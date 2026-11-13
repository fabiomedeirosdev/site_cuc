from django.db import migrations, models
import apps.communications.images


class Migration(migrations.Migration):
    dependencies = [("communications", "0003_event_audience_and_public_newsletter")]
    operations = [
        migrations.AddField(model_name=name, name="is_members_only", field=models.BooleanField(default=False, verbose_name="apenas para assinantes"))
        for name in ["notice", "campaign", "newslettersettings"]
    ] + [
        operation
        for name, folder, label in [("notice", "notices", "imagem de divulgação"), ("campaign", "newsletters", "imagem da newsletter"), ("newslettersettings", "newsletters", "imagem da newsletter")]
        for operation in [
            migrations.AddField(model_name=name, name="image", field=models.ImageField(blank=True, storage=apps.communications.images.communication_image_storage, upload_to=f"{folder}/%Y/%m/", verbose_name=label)),
            migrations.AddField(model_name=name, name="image_alt", field=models.CharField(blank=True, max_length=200, verbose_name="descrição da imagem")),
        ]
    ]
