from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("content", "0001_initial")]
    operations = [
        migrations.AddField(model_name="article", name="is_featured", field=models.BooleanField(default=False, verbose_name="destaque na página inicial")),
        migrations.AddField(model_name="article", name="featured_position", field=models.PositiveSmallIntegerField(default=0, verbose_name="ordem do destaque")),
    ]
