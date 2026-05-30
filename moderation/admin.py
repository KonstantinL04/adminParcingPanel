from django.contrib import admin
from .models import ModerationCase, ModerationReport, ModerationDecision, UserSanction, EventEditProposal


@admin.register(ModerationCase)
class ModerationCaseAdmin(admin.ModelAdmin):
    list_display = ["id", "target_type", "target_id", "status", "priority", "assigned_moderator_id", "created_at"]
    list_filter = ["target_type", "status", "priority"]
    search_fields = ["title", "reason", "opened_by_user_id", "assigned_moderator_id"]


@admin.register(ModerationReport)
class ModerationReportAdmin(admin.ModelAdmin):
    list_display = ["id", "case", "reporter_user_id", "created_at"]
    search_fields = ["reporter_user_id", "text"]


@admin.register(ModerationDecision)
class ModerationDecisionAdmin(admin.ModelAdmin):
    list_display = ["id", "case", "decision", "moderator_user_id", "created_at"]
    list_filter = ["decision"]
    search_fields = ["moderator_user_id", "reason"]


@admin.register(UserSanction)
class UserSanctionAdmin(admin.ModelAdmin):
    list_display = ["id", "user_id", "sanction_type", "status", "created_at"]
    list_filter = ["sanction_type", "status"]
    search_fields = ["user_id", "reason", "created_by_user_id"]


@admin.register(EventEditProposal)
class EventEditProposalAdmin(admin.ModelAdmin):
    list_display = ["id", "case", "event_id", "proposer_user_id", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["event_id", "proposer_user_id", "comment"]
