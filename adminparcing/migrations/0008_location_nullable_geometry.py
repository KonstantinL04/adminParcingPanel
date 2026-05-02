from django.db import migrations
import django.contrib.gis.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ("adminparcing", "0007_chat_region_city"),
    ]

    operations = [
        migrations.AlterField(
            model_name="location",
            name="location",
            field=django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326),
        ),
    ]
