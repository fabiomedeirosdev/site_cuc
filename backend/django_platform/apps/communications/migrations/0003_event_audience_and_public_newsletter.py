import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def populate_email(apps, schema_editor):
    Preference = apps.get_model("communications", "NewsletterPreference")
    used = set()
    for preference in Preference.objects.select_related("user").all():
        email = preference.user.email.strip().lower()
        if not email or email in used:
            raise RuntimeError("Revise os e-mails duplicados ou vazios da newsletter antes de migrar.")
        used.add(email)
        preference.email = email
        preference.save(update_fields=["email"])


class Migration(migrations.Migration):
    dependencies = [("communications", "0002_alter_campaign_status")]
    operations = [
        migrations.AddField(model_name="event", name="is_members_only", field=models.BooleanField(default=False, verbose_name="apenas para assinantes")),
        migrations.AddField(model_name="newsletterpreference", name="email", field=models.EmailField(max_length=254, null=True)),
        migrations.RunPython(populate_email, migrations.RunPython.noop),
        migrations.AlterField(model_name="newsletterpreference", name="email", field=models.EmailField(max_length=254, unique=True)),
        migrations.AlterField(model_name="newsletterpreference", name="user", field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="newsletter_preference", to=settings.AUTH_USER_MODEL)),
    ]
