from django.core.management.base import BaseCommand, CommandError
from apps.core.inbox import synchronize_inbox


class Command(BaseCommand):
    help = "Importa novos e-mails da caixa de atendimento, sem enviar respostas nem marcar mensagens como lidas no provedor."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50)

    def handle(self, *args, **options):
        if not 1 <= options["limit"] <= 200:
            raise CommandError("Use um limite entre 1 e 200 mensagens.")
        try:
            count = synchronize_inbox(options["limit"])
        except Exception:
            raise CommandError("Não foi possível sincronizar a caixa de atendimento. Confira a configuração IMAP e a disponibilidade do provedor.") from None
        self.stdout.write(self.style.SUCCESS(f"Novas mensagens importadas: {count}"))
