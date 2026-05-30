from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("adminparcing", "0016_remove_location_chat"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="parsedmessage",
            name="category_id",
        ),
        migrations.RemoveField(
            model_name="parsedmessage",
            name="category_name",
        ),
    ]
