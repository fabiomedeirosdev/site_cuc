import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def seed_founders(apps, schema_editor):
    apps.get_model("core", "FoundersPage").objects.get_or_create(pk=1)


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="FoundersPage", fields=[
            ("id", models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
            ("title", models.CharField(default="Nossos fundadores", max_length=200, verbose_name="título da página")),
            ("body", models.TextField(default="Eneida Carmona e Luiz Carmona são psicólogos e fundadores da Comunidade Unidos em Cristo. A missão nasceu de encontros de oração entre casais amigos, com o desejo de partilhar a Palavra de Deus e viver a fé de forma concreta. Com o tempo, passou a oferecer formações, palestras e projetos de restauração do ser.", max_length=50000, verbose_name="história dos fundadores")),
            ("photo", models.ImageField(blank=True, upload_to="institutional/founders/%Y/%m/", verbose_name="foto dos fundadores")),
            ("photo_alt", models.CharField(default="Fundadores da Comunidade Unidos em Cristo", max_length=200, verbose_name="descrição da foto")),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
        ], options={"verbose_name": "página dos fundadores", "verbose_name_plural": "página dos fundadores", "constraints": [models.CheckConstraint(condition=models.Q(id=1), name="core_single_founders_page")]}),
        migrations.RunPython(seed_founders, migrations.RunPython.noop),
    ]
