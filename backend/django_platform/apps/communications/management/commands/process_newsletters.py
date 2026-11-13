from django.core.management.base import BaseCommand
from apps.communications.services import run_newsletters


class Command(BaseCommand):
    help = "Prepara o boletim semanal e entrega edições agendadas, respeitando consentimento e assinatura."

    def handle(self, *args, **options):
        result = run_newsletters()
        if not result["enabled"]:
            self.stdout.write("Newsletter desativada. Nenhum e-mail enviado.")
        else:
            self.stdout.write(f"Enviados: {result['sent']}. Falhas pendentes para retentativa: {result['failed']}.")
