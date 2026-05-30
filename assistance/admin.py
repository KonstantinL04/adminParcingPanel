from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import (
    HelpRequest,
    HelpRequestCandidate,
    HelpRequestChatMessage,
    HelpRequestChatRoom,
    HelpRequestResolution,
    HelpRequestResponse,
    HelperPresence,
)


@admin.register(HelpRequest)
class HelpRequestAdmin(GISModelAdmin):
    list_display = ["id", "event_id", "creator_user_id", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["creator_user_id", "description"]


@admin.register(HelpRequestResponse)
class HelpRequestResponseAdmin(admin.ModelAdmin):
    list_display = ["id", "help_request", "responder_user_id", "accepted", "created_at"]
    list_filter = ["accepted", "help_request__status"]
    search_fields = ["responder_user_id"]


@admin.register(HelperPresence)
class HelperPresenceAdmin(GISModelAdmin):
    list_display = ["user_id", "is_available", "reliability_score", "last_seen_at"]
    list_filter = ["is_available"]
    search_fields = ["user_id"]


admin.site.register(HelpRequestCandidate)
admin.site.register(HelpRequestChatRoom)
admin.site.register(HelpRequestChatMessage)
admin.site.register(HelpRequestResolution)
