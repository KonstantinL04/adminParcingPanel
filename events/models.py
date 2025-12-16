from django.db import models
from django.contrib.gis.db import models as gis_models

# Create your models here.
class ParsedMessage(models.Model):
    telegram_message_id = models.BigIntegerField()
    chat_id = models.CharField(max_length=255)
    chat_title = models.CharField(max_length=255)

    author_id = models.BigIntegerField(null=True, blank=True)
    author_name = models.CharField(max_length=255, blank=True)

    text = models.TextField()

    category_id = models.IntegerField(null=True, blank=True)
    category_name = models.CharField(max_length=50, null=True, blank=True)

    created_at = models.DateTimeField()
    parsed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["category_id"]),
            models.Index(fields=["chat_id"]),
        ]
        

class MessageLocation(models.Model):
    message = models.ForeignKey(
        ParsedMessage,
        related_name="locations",
        on_delete=models.CASCADE
    )

    location = gis_models.PointField()
    place_name = models.CharField(max_length=255)
    place_id = models.IntegerField(null=True, blank=True)

    source = models.CharField(
        max_length=20,
        choices=[
            ("telegram", "Telegram"),
            ("nlp", "NLP"),
            ("route", "Route"),
        ]
    )

    confidence = models.FloatField(null=True, blank=True)
    
class MessageRouteMatch(models.Model):
    message = models.ForeignKey(
        ParsedMessage,
        related_name="routes",
        on_delete=models.CASCADE
    )

    route_id = models.IntegerField()
    route_name = models.CharField(max_length=255)

    start_place_id = models.IntegerField()
    start_place_name = models.CharField(max_length=255)

    end_place_id = models.IntegerField()
    end_place_name = models.CharField(max_length=255)

    reversed = models.BooleanField(default=False)

    confidence = models.FloatField(null=True, blank=True)