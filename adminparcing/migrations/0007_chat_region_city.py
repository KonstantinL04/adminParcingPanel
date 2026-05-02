from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("adminparcing", "0006_alertcategory_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="chat",
            name="city",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="chats",
                to="adminparcing.city",
            ),
        ),
        migrations.AddField(
            model_name="chat",
            name="region",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="chats",
                to="adminparcing.region",
            ),
        ),
    ]
