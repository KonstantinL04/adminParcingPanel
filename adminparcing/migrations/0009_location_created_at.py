from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("adminparcing", "0008_location_nullable_geometry"),
    ]

    operations = [
        migrations.AddField(
            model_name="location",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, db_index=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
