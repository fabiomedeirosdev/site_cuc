from django.db import migrations


def create_institutional_groups(apps, schema_editor):
    Group = apps.get_model("editorial", "EditorialGroup")
    # Somente os quatro trabalhos descritos no site institucional existente.
    entries = [
        ("rhematerapia", "Rhematerapia", "heart", "Dez oficinas voltadas à busca do autoconhecimento e à compreensão mais ampla de si."),
        ("restaura-me", "Restaura-me", "prayer", "Uma vivência do carisma da restauração, associando a Palavra de Deus à formação humana."),
        ("promocao-a-vida", "Promoção à Vida", "family", "Acolhimento por meio do Projeto Raquel e do trabalho Gravidez em Crise."),
        ("grupo-cura", "Grupo C.U.R.A.", "headquarters", "Apoio a dependentes e codependentes em situações relacionadas a drogas, álcool e jogos."),
    ]
    for position, (slug, name, cover, description) in enumerate(entries):
        Group.objects.get_or_create(slug=slug, defaults={"name": name, "cover": cover, "description": description, "position": position})


class Migration(migrations.Migration):
    dependencies = [("editorial", "0001_initial")]
    operations = [migrations.RunPython(create_institutional_groups, migrations.RunPython.noop)]
