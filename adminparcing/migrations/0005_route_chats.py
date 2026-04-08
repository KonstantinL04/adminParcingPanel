from django.db import migrations, models


def forwards_fill_route_chats(apps, schema_editor):
    Route = apps.get_model("adminparcing", "Route")

    for route in Route.objects.all().iterator():
        chat_ids = set()

        for loc in [route.start_point, route.end_point]:
            if not loc:
                continue
            if getattr(loc, "chat_id", None):
                chat_ids.add(loc.chat_id)
            for cid in loc.chats.values_list("id", flat=True):
                chat_ids.add(cid)

        for point in route.points.select_related("location").all():
            loc = point.location
            if not loc:
                continue
            if getattr(loc, "chat_id", None):
                chat_ids.add(loc.chat_id)
            for cid in loc.chats.values_list("id", flat=True):
                chat_ids.add(cid)

        if chat_ids:
            route.chats.set(chat_ids)


def backwards_clear_route_chats(apps, schema_editor):
    Route = apps.get_model("adminparcing", "Route")
    for route in Route.objects.all().iterator():
        route.chats.clear()


class Migration(migrations.Migration):

    dependencies = [
        ("adminparcing", "0004_location_chats_and_nullable_chat"),
    ]

    operations = [
        migrations.AddField(
            model_name="route",
            name="chats",
            field=models.ManyToManyField(blank=True, related_name="routes", to="adminparcing.chat"),
        ),
        migrations.RunPython(forwards_fill_route_chats, backwards_clear_route_chats),
    ]
