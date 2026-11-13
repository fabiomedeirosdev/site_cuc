from django.db import migrations


def rename(apps, old, new):
    Group = apps.get_model("auth", "Group")
    group = Group.objects.filter(name=old).first()
    if group:
        if Group.objects.filter(name=new).exists():
            raise RuntimeError("Existem dois grupos de facilitadores. Revise os vínculos antes de renomear.")
        group.name = new
        group.save(update_fields=["name"])


def forwards(apps, schema_editor):
    rename(apps, "Colunistas", "Facilitadores")


def backwards(apps, schema_editor):
    rename(apps, "Facilitadores", "Colunistas")


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_email_identity_and_roles")]
    operations = [migrations.RunPython(forwards, backwards)]
