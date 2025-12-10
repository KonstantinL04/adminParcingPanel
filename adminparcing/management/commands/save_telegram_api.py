from django.core.management.base import BaseCommand
from adminparcing.models import SettingAPI
from adminparcing.utils.crypto import fernet

class Command(BaseCommand):

    def handle(self, *args, **options):
        keys = {
            "API_ID": "",
            "API_HASH": "",
            "SESSION_NAME": ""
        }

        for k, v in keys.items():
            obj, created = SettingAPI.objects.get_or_create(key=k)
            obj.value = v  # setter + общий fernet
            obj.save()