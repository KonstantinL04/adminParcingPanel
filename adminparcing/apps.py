from django.apps import AppConfig


class AdminparcingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'adminparcing'

    def ready(self):
        import adminparcing.signals  # noqa: F401
