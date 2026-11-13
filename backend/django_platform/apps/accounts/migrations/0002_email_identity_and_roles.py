from django.db import migrations


def prepare_roles_and_profiles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    User = apps.get_model("auth", "User")
    Profile = apps.get_model("accounts", "Profile")
    content_type, _ = ContentType.objects.get_or_create(app_label="accounts", model="profile")
    subscriber, _ = Group.objects.get_or_create(name="Assinantes")
    for code, label in [
        ("read_articles", "Pode ler artigos publicados"),
        ("watch_videos", "Pode assistir a vídeos publicados"),
        ("listen_audio", "Pode ouvir áudios publicados"),
    ]:
        permission, _ = Permission.objects.get_or_create(content_type=content_type, codename=code, defaults={"name": label})
        subscriber.permissions.add(permission)
    for group in ["Colunistas", "Coordenadores"]:
        Group.objects.get_or_create(name=group)
    for user in User.objects.iterator():
        Profile.objects.get_or_create(user_id=user.pk, defaults={"display_name": f"{user.first_name} {user.last_name}".strip()})


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial"), ("auth", "0012_alter_user_first_name_max_length")]
    operations = [
        # Protege o login por e-mail sem substituir auth.User nem apagar suas tabelas.
        # Se houver duplicatas preexistentes, o PostgreSQL interrompe a migração.
        migrations.RunSQL(
            "CREATE UNIQUE INDEX accounts_user_email_ci ON auth_user (LOWER(BTRIM(email))) WHERE BTRIM(email) <> '';",
            "DROP INDEX accounts_user_email_ci;",
        ),
        migrations.RunPython(prepare_roles_and_profiles, migrations.RunPython.noop),
    ]
