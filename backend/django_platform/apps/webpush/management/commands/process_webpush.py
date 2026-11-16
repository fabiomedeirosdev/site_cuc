import json

from django.core.management.base import BaseCommand, CommandError
from apps.webpush.services import run_push


class Command(BaseCommand):
    help = "Processa um lote limitado de Web Push e encerra. Não inicia serviço residente."

    def add_arguments(self, parser):
        parser.add_argument("--batch-size", type=int, default=20)
        parser.add_argument("--max-seconds", type=int, default=25)

    def handle(self, *args, **options):
        if not 1 <= options["batch_size"] <= 100 or not 1 <= options["max_seconds"] <= 50:
            raise CommandError("Use lote de 1 a 100 e duração de 1 a 50 segundos.")
        self.stdout.write(json.dumps(run_push(options["batch_size"], options["max_seconds"])))
