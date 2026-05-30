from rest_framework import serializers
from .models import ModerationCase, ModerationReport, ModerationDecision, UserSanction, EventEditProposal


class ModerationReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModerationReport
        fields = ["id", "case", "reporter_user_id", "text", "created_at"]
        read_only_fields = ["created_at"]


class ModerationDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModerationDecision
        fields = ["id", "case", "decision", "moderator_user_id", "reason", "meta", "created_at"]
        read_only_fields = ["created_at"]


class EventEditProposalSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventEditProposal
        fields = [
            "id",
            "case",
            "event_id",
            "proposer_user_id",
            "proposed_changes",
            "comment",
            "status",
            "applied_at",
            "created_at",
        ]
        read_only_fields = ["status", "applied_at", "created_at"]


class UserSanctionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSanction
        fields = [
            "id",
            "user_id",
            "case",
            "sanction_type",
            "status",
            "reason",
            "starts_at",
            "ends_at",
            "created_by_user_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["starts_at", "created_at", "updated_at"]


class ModerationCaseSerializer(serializers.ModelSerializer):
    reports = ModerationReportSerializer(many=True, read_only=True)
    decisions = ModerationDecisionSerializer(many=True, read_only=True)
    event_edit_proposal = EventEditProposalSerializer(read_only=True)

    class Meta:
        model = ModerationCase
        fields = [
            "id",
            "target_type",
            "target_id",
            "title",
            "status",
            "priority",
            "assigned_moderator_id",
            "reason",
            "opened_by_user_id",
            "resolved_at",
            "created_at",
            "updated_at",
            "reports",
            "decisions",
            "event_edit_proposal",
        ]
        read_only_fields = ["resolved_at", "created_at", "updated_at"]


class ModerationReportCreateSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=ModerationCase.TARGET_CHOICES)
    target_id = serializers.IntegerField(min_value=1)
    reporter_user_id = serializers.CharField()
    text = serializers.CharField(required=False, allow_blank=True, default="")
    priority = serializers.ChoiceField(choices=ModerationCase.PRIORITY_CHOICES, required=False)
    title = serializers.CharField(required=False, allow_blank=True, default="")


class EventEditProposalCreateSerializer(serializers.Serializer):
    event_id = serializers.IntegerField(min_value=1)
    proposer_user_id = serializers.CharField()
    proposed_changes = serializers.JSONField()
    comment = serializers.CharField(required=False, allow_blank=True, default="")
    priority = serializers.ChoiceField(choices=ModerationCase.PRIORITY_CHOICES, required=False)


class ModerationAssignSerializer(serializers.Serializer):
    moderator_user_id = serializers.CharField()


class ModerationResolveSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=ModerationDecision.DECISION_CHOICES)
    moderator_user_id = serializers.CharField()
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    meta = serializers.JSONField(required=False)
