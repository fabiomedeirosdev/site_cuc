from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("editorial", "0003_alter_membership_role")]
    operations = [
        migrations.AddField(model_name="editorialgroup", name="custom_cover", field=models.ImageField(blank=True, upload_to="group-covers/%Y/%m/", verbose_name="foto própria")),
        migrations.AddField(model_name="editorialgroup", name="cover_alt", field=models.CharField(blank=True, max_length=200, verbose_name="descrição da foto")),
    ]
