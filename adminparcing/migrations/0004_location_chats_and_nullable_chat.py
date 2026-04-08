from django.db import migrations, models
import django.db.models.deletion


def forwards_fill_chats(apps, schema_editor):
    Location = apps.get_model("adminparcing", "Location")
    for loc in Location.objects.exclude(chat_id__isnull=True).iterator():
        loc.chats.add(loc.chat_id)


def backwards_fill_chat(apps, schema_editor):
    Location = apps.get_model("adminparcing", "Location")
    for loc in Location.objects.filter(chat_id__isnull=True).iterator():
        first_chat_id = loc.chats.values_list("id", flat=True).first()
        if first_chat_id:
            loc.chat_id = first_chat_id
            loc.save(update_fields=["chat"])


class Migration(migrations.Migration):

    dependencies = [
        ("adminparcing", "0003_alter_region_unique_together_location_chat_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="location",
            name="chat",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="locations",
                to="adminparcing.chat",
            ),
        ),
        migrations.AddField(
            model_name="location",
            name="chats",
            field=models.ManyToManyField(blank=True, related_name="locations_multi", to="adminparcing.chat"),
        ),
        migrations.RunPython(forwards_fill_chats, backwards_fill_chat),
    ]
