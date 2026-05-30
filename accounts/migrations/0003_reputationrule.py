from django.db import migrations, models


DEFAULT_RULES = {
    "event_created": ("Создание дорожного события", 1, "Начисляется за создание события пользователем."),
    "event_confirmed": ("Подтверждение события", 2, "Начисляется за полезное подтверждение дорожного события."),
    "event_denied": ("Опровержение события", -2, "Списывается за ошибочное или вредное действие по событию."),
    "edit_approved": ("Правка одобрена", 1, "Начисляется за принятую модератором правку."),
    "edit_rejected": ("Правка отклонена", -1, "Списывается за отклоненную правку."),
    "help_completed": ("Помощь оказана", 2, "Начисляется помощнику после успешного завершения запроса помощи."),
    "help_failed": ("Помощь не оказана", -2, "Списывается, если отклик не привел к помощи."),
    "help_canceled": ("Помощь отменена", -1, "Списывается или фиксируется при отмене помощи."),
}


def seed_reputation_rules(apps, schema_editor):
    ReputationRule = apps.get_model("accounts", "ReputationRule")
    for action, (title, delta, description) in DEFAULT_RULES.items():
        ReputationRule.objects.get_or_create(
            action=action,
            defaults={
                "title": title,
                "reputation_delta": delta,
                "description": description,
                "enabled": True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_userreputationlog"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReputationRule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(choices=[("event_created", "event_created"), ("event_confirmed", "event_confirmed"), ("event_denied", "event_denied"), ("edit_approved", "edit_approved"), ("edit_rejected", "edit_rejected"), ("help_completed", "help_completed"), ("help_failed", "help_failed"), ("help_canceled", "help_canceled")], db_index=True, max_length=64, unique=True)),
                ("title", models.CharField(max_length=128)),
                ("reputation_delta", models.IntegerField(default=0)),
                ("description", models.CharField(blank=True, default="", max_length=255)),
                ("enabled", models.BooleanField(default=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["action"],
            },
        ),
        migrations.RunPython(seed_reputation_rules, migrations.RunPython.noop),
    ]
