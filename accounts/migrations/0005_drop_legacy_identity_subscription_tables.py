from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_apppurchase_remove_usersubscription_plan_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DROP TABLE IF EXISTS "IdentityAuth_authidentity" CASCADE;
            DROP TABLE IF EXISTS "IdentityAuth_identityuser" CASCADE;
            DROP TABLE IF EXISTS "IdentityAuth_role" CASCADE;
            DROP TABLE IF EXISTS "IdentityAuth_userprofile" CASCADE;
            DROP TABLE IF EXISTS "IdentityAuth_userrole" CASCADE;
            DROP TABLE IF EXISTS subscription_usersubscription CASCADE;
            DROP TABLE IF EXISTS subscription_subscriptionplan CASCADE;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
