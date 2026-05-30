from django.db import migrations, models
import django.db.models.deletion


def copy_votes_to_event_fk(apps, schema_editor):
    EntityVote = apps.get_model("events", "EntityVote")
    MapEvent = apps.get_model("events", "MapEvent")
    ContentType = apps.get_model("contenttypes", "ContentType")

    map_event_type = ContentType.objects.filter(app_label="events", model="mapevent").first()
    if not map_event_type:
        EntityVote.objects.all().delete()
        return

    event_ids = set(MapEvent.objects.values_list("id", flat=True))
    votes = EntityVote.objects.filter(content_type_id=map_event_type.id)

    for vote in votes.iterator():
        if vote.object_id in event_ids:
            vote.event_id = vote.object_id
            vote.save(update_fields=["event"])

    EntityVote.objects.filter(event__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0006_drop_legacy_help_tables"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name="entityvote",
            unique_together=set(),
        ),
        migrations.RemoveIndex(
            model_name="entityvote",
            name="events_enti_content_54aa61_idx",
        ),
        migrations.RemoveIndex(
            model_name="entityvote",
            name="events_enti_user_id_f0c182_idx",
        ),
        migrations.AddField(
            model_name="entityvote",
            name="event",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="votes",
                to="events.mapevent",
            ),
        ),
        migrations.RunPython(copy_votes_to_event_fk, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="entityvote",
            name="event",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="votes",
                to="events.mapevent",
            ),
        ),
        migrations.RemoveField(
            model_name="entityvote",
            name="content_type",
        ),
        migrations.RemoveField(
            model_name="entityvote",
            name="object_id",
        ),
        migrations.AddIndex(
            model_name="entityvote",
            index=models.Index(fields=["event"], name="events_vote_event_idx"),
        ),
        migrations.AddIndex(
            model_name="entityvote",
            index=models.Index(fields=["user_id"], name="events_vote_user_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="entityvote",
            unique_together={("event", "user_id")},
        ),
    ]
