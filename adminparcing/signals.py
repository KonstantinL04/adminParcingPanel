from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import ParsedMessage


@receiver(post_save, sender=ParsedMessage)
def parsed_message_created(sender, instance, created, **kwargs):
    if not created:
        return

    parsing_category = instance.parsing_category
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "events",
        {
            "type": "event_created",
            "data": {
                "type": "message",
                "payload": {
                    "id": instance.id,
                    "telegram_message_id": instance.telegram_message_id,
                    "chat": instance.chat_id,
                    "author_name": instance.author_name,
                    "text": instance.text,
                    "category": parsing_category.category_id if parsing_category else None,
                    "created_at": instance.created_at.isoformat() if instance.created_at else None,
                    "parsed_at": instance.parsed_at.isoformat() if instance.parsed_at else None,
                },
            },
        },
    )
