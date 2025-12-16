# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import ParsedMessage

@receiver(post_save, sender=ParsedMessage)
def message_created(sender, instance, created, **kwargs):
    if not created:
        return

    from .serializers import MessageSerializer

    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        "events",
        {
            "type": "event_created",
            "data": {
                "type": "message",
                "payload": MessageSerializer(instance).data,
            }
        }
    )
