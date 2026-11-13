import uuid
from django.db import migrations, models
import apps.accounts.images


def populate_public_ids(apps, schema_editor):
    Profile = apps.get_model("accounts", "Profile")
    for profile in Profile.objects.filter(public_id__isnull=True).iterator():
        profile.public_id = uuid.uuid4()
        profile.save(update_fields=["public_id"])


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_facilitators_name")]
    operations = [
        migrations.AddField(model_name="profile", name="public_id", field=models.UUIDField(null=True, editable=False)),
        migrations.RunPython(populate_public_ids, migrations.RunPython.noop),
        migrations.AlterField(model_name="profile", name="public_id", field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
        migrations.AddField(model_name="profile", name="avatar", field=models.ImageField(blank=True, storage=apps.accounts.images.profile_image_storage, upload_to="avatars/%Y/%m/", verbose_name="foto de perfil")),
        migrations.AddField(model_name="profile", name="biography", field=models.TextField(blank=True, max_length=3000, verbose_name="biografia")),
        migrations.AddField(model_name="profile", name="website", field=models.URLField(blank=True, max_length=500, verbose_name="site")),
        migrations.AddField(model_name="profile", name="phone", field=models.CharField(blank=True, max_length=30, verbose_name="telefone público")),
        migrations.AddField(model_name="profile", name="video_url", field=models.URLField(blank=True, max_length=1000, verbose_name="vídeo de apresentação no YouTube")),
        migrations.AddField(model_name="profile", name="pending_email", field=models.EmailField(blank=True, max_length=254, verbose_name="novo e-mail pendente")),
        migrations.AddField(model_name="profile", name="email_change_hash", field=models.CharField(blank=True, max_length=64)),
        migrations.AddField(model_name="profile", name="email_change_auth_hash", field=models.CharField(blank=True, max_length=64)),
        migrations.AddField(model_name="profile", name="email_change_expires_at", field=models.DateTimeField(blank=True, null=True)),
    ]
