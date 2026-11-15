import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import LiveServerTestCase, override_settings
from django.utils import timezone
from rest_framework.throttling import ScopedRateThrottle

from apps.content.models import Article
from apps.editorial.models import EditorialGroup, Membership
from .models import Checkout, Subscription
from .provider import PagBank, Snapshot
from .services import synchronize


class BillingBrowserTests(LiveServerTestCase):
    host = "127.0.0.1"

    def test_subscription_workflow_in_edge(self):
        workspace = Path(__file__).resolve().parents[4]
        fixtures = {}
        snapshots = {}
        group = EditorialGroup.objects.create(name="Formação de teste", slug="billing-test")
        author = get_user_model().objects.create_user(username="billing-author", email="author@example.invalid", password="BillingTest!81-Password")
        Membership.objects.create(group=group, user=author, role="columnist")
        article = Article.objects.create(author=author, group=group, title="Reflexão exclusiva", body="## Esperança\n\nTexto exclusivo para assinantes.", audience="members", status="published", video_url="https://youtu.be/abcdefghijk")
        rates = {"login": "1000/minute", "account": "1000/minute", "checkout": "1000/minute", "invitation": "1000/minute", "webhook": "1000/minute"}
        with override_settings(BILLING_ENABLED=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", PUBLIC_FRONTEND_URL="https://example.invalid", PUBLIC_API_URL="https://api.example.invalid", PAGBANK_CHECKOUT_TOKEN="test-only", PAGBANK_RECURRING_TOKEN="test-only", MERCHANT_LEGAL_NAME="Entidade fictícia de teste", MERCHANT_DOCUMENT="DOCUMENTO DE TESTE", MERCHANT_CONTACT_EMAIL="support@example.invalid", MERCHANT_ADDRESS="Endereço fictício de teste", CSRF_TRUSTED_ORIGINS=["http://127.0.0.1:5177"], CORS_ALLOWED_ORIGINS=["http://127.0.0.1:5177"]), patch.object(ScopedRateThrottle, "THROTTLE_RATES", rates), patch.object(PagBank, "subscription", side_effect=lambda identifier: snapshots[identifier]), patch.object(PagBank, "cancel", return_value={}), patch.object(PagBank, "create_checkout", side_effect=lambda checkout: {"id": "CHEC_" + str(uuid4()), "plan_id": "PLAN_" + str(uuid4()), "url": "https://pagamento.pagbank.com.br/pagamento?code=TEST-ONLY"}):
            for viewport in ["desktop", "tablet", "mobile", "small-mobile"]:
                fixtures[viewport] = {"article": article.pk}
                for role in ["new", "existing"]:
                    email = f"{viewport}.{role}@example.invalid"
                    if role == "existing":
                        get_user_model().objects.create_user(username=f"{viewport}-existing", email=email, password="BillingTest!81-Password")
                    checkout = Checkout.objects.create(plan_id="PLAN_" + str(uuid4()), legal_version=settings.BILLING_LEGAL_VERSION)
                    identifier = "SUBS_" + str(uuid4())
                    now = timezone.now()
                    snapshots[identifier] = Snapshot(identifier, checkout.plan_id, email, "ACTIVE", now, now - timedelta(days=15), now + timedelta(days=15), 4800, "BRL")
                    synchronize(identifier)
                    token = re.search(r"#convite=([A-Za-z0-9_-]+)", mail.outbox[-1].body).group(1)
                    fixtures[viewport][role] = {"token": token, "email": email}
                expired = get_user_model().objects.create_user(username=f"{viewport}-expired", email=f"{viewport}.expired@example.invalid", password="BillingTest!81-Password")
                Subscription.objects.create(checkout=checkout, provider_id="SUBS_" + str(uuid4()), email=expired.email, user=expired, status="CANCELED", paid_until=timezone.now() - timedelta(days=1))
            env = {**os.environ, "CUC_BILLING_E2E": "1", "CUC_API_TARGET": self.live_server_url, "CUC_BILLING_FIXTURES": json.dumps(fixtures)}
            npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
            command = [npm, "run", "test:billing"]
            if env.get("CUC_BILLING_E2E_GREP"):
                command += ["--", "--grep", env["CUC_BILLING_E2E_GREP"]]
            result = subprocess.run(command, cwd=workspace / "frontend", env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", errors="replace", timeout=360)
        encoding = sys.stdout.encoding or "utf-8"
        print(result.stdout.encode(encoding, errors="replace").decode(encoding))
        self.assertEqual(result.returncode, 0, result.stdout)
