from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0005_delete_parsedmessage"),
        ("assistance", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DROP TABLE IF EXISTS events_helpchatmessage CASCADE;
            DROP TABLE IF EXISTS events_helpchatroom CASCADE;
            DROP TABLE IF EXISTS events_helprequestparticipant CASCADE;
            DROP TABLE IF EXISTS events_helprequestcandidate CASCADE;
            DROP TABLE IF EXISTS events_helprequestchatmessage CASCADE;
            DROP TABLE IF EXISTS events_helprequestchatroom CASCADE;
            DROP TABLE IF EXISTS events_helprequestresolution CASCADE;
            DROP TABLE IF EXISTS events_helprequestresponse CASCADE;
            DROP TABLE IF EXISTS events_helperpresence CASCADE;
            DROP TABLE IF EXISTS events_helprequest CASCADE;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
