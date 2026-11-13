import json
import re
from dataclasses import dataclass
from datetime import date, datetime, time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime


class ProviderUnavailable(Exception):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def provider_datetime(value):
    if not isinstance(value, str):
        raise ProviderUnavailable("Data financeira ausente.")
    try:
        if len(value) == 10:
            return datetime.combine(date.fromisoformat(value), time.min, tzinfo=ZoneInfo("America/Sao_Paulo"))
        parsed = parse_datetime(value)
    except ValueError:
        raise ProviderUnavailable("Data financeira inválida.") from None
    if not parsed or timezone.is_naive(parsed):
        raise ProviderUnavailable("Data financeira inválida.")
    return parsed


@dataclass(frozen=True)
class Snapshot:
    provider_id: str
    plan_id: str
    email: str
    status: str
    updated_at: datetime
    created_at: datetime
    paid_until: datetime | None
    amount: int
    currency: str


def ready():
    return bool(settings.BILLING_ENABLED and settings.PAGBANK_CHECKOUT_TOKEN and settings.PAGBANK_RECURRING_TOKEN and settings.PUBLIC_FRONTEND_URL.startswith("https://") and settings.PUBLIC_API_URL.startswith("https://") and settings.MERCHANT_LEGAL_NAME and settings.MERCHANT_DOCUMENT and settings.MERCHANT_CONTACT_EMAIL and settings.MERCHANT_ADDRESS and (settings.PAGBANK_ENVIRONMENT == "sandbox" or (settings.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend" and settings.EMAIL_HOST and not settings.DEFAULT_FROM_EMAIL.endswith(".invalid"))))


class PagBank:
    def __init__(self):
        sandbox = settings.PAGBANK_ENVIRONMENT == "sandbox"
        self.checkout_api = "https://sandbox.api.pagseguro.com" if sandbox else "https://api.pagseguro.com"
        self.recurring_api = "https://sandbox.api.assinaturas.pagseguro.com" if sandbox else "https://api.assinaturas.pagseguro.com"

    def request(self, base, path, token, method="GET", body=None, key=None):
        if not token:
            raise ProviderUnavailable("PagBank não configurado.")
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json", "Content-Type": "application/json"}
        if key:
            headers["x-idempotency-key"] = str(key)
        request = Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers, method=method)
        try:
            with build_opener(NoRedirect).open(request, timeout=15) as response:
                raw = response.read(1024 * 1024 + 1)
                if len(raw) > 1024 * 1024:
                    raise ProviderUnavailable("Resposta financeira inválida.")
                return json.loads(raw) if raw else {}
        except (HTTPError, URLError, TimeoutError, ValueError, OSError):
            # Nunca incluir tokens, dados bancários ou corpo do provedor nas respostas/logs.
            raise ProviderUnavailable("O PagBank está indisponível. Tente novamente.") from None

    def create_checkout(self, checkout):
        result = self.request(self.checkout_api, "/checkouts", settings.PAGBANK_CHECKOUT_TOKEN, "POST", {
            "reference_id": str(checkout.pk),
            "items": [{"reference_id": "comunidade-online-mensal", "name": "Comunidade Online Unidos em Cristo", "quantity": 1, "unit_amount": checkout.amount}],
            "payment_methods": [{"type": "CREDIT_CARD"}],
            "payment_methods_configs": [{"type": "CREDIT_CARD", "config_options": [{"option": "INSTALLMENTS_LIMIT", "value": "1"}]}],
            "recurrence_plan": {"name": "Comunidade Online — mensal", "interval": {"unit": "MONTH", "length": 1}},
            "redirect_url": settings.PUBLIC_FRONTEND_URL + "/pagamento-pendente.html",
            "return_url": settings.PUBLIC_FRONTEND_URL + "/assinatura.html",
        }, key=checkout.pk)
        if not isinstance(result, dict) or not isinstance(result.get("links"), list) or not isinstance(result.get("recurrence_plan"), dict) or not isinstance(result.get("id"), str):
            raise ProviderUnavailable("Resposta de checkout incompleta.")
        url = next((link.get("href") for link in result["links"] if isinstance(link, dict) and link.get("rel") == "PAY"), "")
        if not isinstance(url, str):
            raise ProviderUnavailable("Endereço de checkout ausente.")
        parsed = urlparse(url)
        allowed = {"pagamento.pagbank.com.br"} if settings.PAGBANK_ENVIRONMENT == "production" else {"pagamento.pagbank.com.br", "pagamento.sandbox.pagbank.com.br", "sandbox.pagseguro.uol.com.br", "sandbox.pagamento.pagseguro.uol.com.br", "qa.pagamento.pagseguro.uol.com.br"}
        if parsed.scheme != "https" or parsed.hostname not in allowed or parsed.username or parsed.password:
            raise ProviderUnavailable("Endereço de checkout não reconhecido.")
        plan_id = result.get("recurrence_plan", {}).get("id", "")
        if not isinstance(plan_id, str) or not re.fullmatch(r"PLAN_[A-Fa-f0-9-]{36}", plan_id):
            raise ProviderUnavailable("Plano recorrente não confirmado pelo PagBank.")
        return {"id": result["id"], "plan_id": plan_id, "url": url}

    def subscription(self, identifier):
        if not re.fullmatch(r"SUBS_[A-Fa-f0-9-]{36}", identifier):
            raise ProviderUnavailable("Identificador inválido.")
        data = self.request(self.recurring_api, f"/subscriptions/{identifier}", settings.PAGBANK_RECURRING_TOKEN)
        if not isinstance(data, dict) or not all(isinstance(data.get(key), dict) for key in ["plan", "customer", "amount"]):
            raise ProviderUnavailable("Resposta financeira incompleta.")
        if data.get("id") != identifier:
            raise ProviderUnavailable("Assinatura não confirmada pelo PagBank.")
        if not isinstance(data["customer"].get("email"), str):
            raise ProviderUnavailable("E-mail financeiro ausente.")
        status = data.get("status", "")
        if not isinstance(status, str) or status not in {"ACTIVE", "PENDING", "OVERDUE", "PENDING_ACTION", "CANCELED", "EXPIRED", "SUSPENDED", "TRIAL"}:
            raise ProviderUnavailable("Estado de assinatura não reconhecido.")
        if not isinstance(data["plan"].get("id"), str):
            raise ProviderUnavailable("Plano financeiro ausente.")
        # ACTIVE é documentado pelo PagBank como fatura paga no ciclo vigente.
        # Só nesse estado next_invoice_at pode confirmar um novo período pago.
        return Snapshot(identifier, data.get("plan", {}).get("id", ""), data.get("customer", {}).get("email", "").strip().lower(), status, provider_datetime(data.get("updated_at")), provider_datetime(data.get("created_at")), provider_datetime(data.get("next_invoice_at")) if status == "ACTIVE" else None, data.get("amount", {}).get("value"), data.get("amount", {}).get("currency"))

    def cancel(self, identifier):
        if not re.fullmatch(r"SUBS_[A-Fa-f0-9-]{36}", identifier):
            raise ProviderUnavailable("Identificador inválido.")
        return self.request(self.recurring_api, f"/subscriptions/{identifier}/cancel", settings.PAGBANK_RECURRING_TOKEN, "PUT", key="cancel" + identifier.replace("-", "").replace("_", ""))
