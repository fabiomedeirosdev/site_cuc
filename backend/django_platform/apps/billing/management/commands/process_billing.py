from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

from apps.billing.models import EmailJob, Subscription
from apps.billing.provider import PagBank, ProviderUnavailable
from apps.billing.services import deliver_email, synchronize


class Command(BaseCommand):
    help = "Reconcilia assinaturas conhecidas, retenta cancelamentos e entrega e-mails pendentes."

    def handle(self, *args, **options):
        if not settings.BILLING_ENABLED:
            self.stdout.write("Integração de assinaturas desativada; nenhuma operação financeira executada.")
            return
        failures = 0
        for subscription in Subscription.objects.iterator():
            try:
                # Consultar antes de retentar: uma resposta perdida pode já ter
                # cancelado a renovação no banco na execução anterior.
                subscription = synchronize(subscription.provider_id)
                if subscription is None:
                    continue
                if subscription.cancel_requested_at and subscription.status not in {"CANCELED", "EXPIRED"}:
                    PagBank().cancel(subscription.provider_id)
                    synchronize(subscription.provider_id)
            except ProviderUnavailable:
                failures += 1
        for identifier in EmailJob.objects.filter(sent_at__isnull=True).values_list("pk", flat=True):
            deliver_email(identifier)
        self.stdout.write(f"Reconciliação concluída; pendências de comunicação com o banco: {failures}.")
