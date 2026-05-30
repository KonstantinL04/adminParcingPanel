from django.db import models


class ModerationCase(models.Model):
    TARGET_EVENT = "event"
    TARGET_EVENT_EDIT = "event_edit"
    TARGET_USER = "user"
    TARGET_CHOICES = [
        (TARGET_EVENT, "event"),
        (TARGET_EVENT_EDIT, "event_edit"),
        (TARGET_USER, "user"),
    ]

    STATUS_OPEN = "open"
    STATUS_IN_REVIEW = "in_review"
    STATUS_RESOLVED = "resolved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_OPEN, "open"),
        (STATUS_IN_REVIEW, "in_review"),
        (STATUS_RESOLVED, "resolved"),
        (STATUS_REJECTED, "rejected"),
    ]

    PRIORITY_LOW = "low"
    PRIORITY_MEDIUM = "medium"
    PRIORITY_HIGH = "high"
    PRIORITY_CRITICAL = "critical"
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, "low"),
        (PRIORITY_MEDIUM, "medium"),
        (PRIORITY_HIGH, "high"),
        (PRIORITY_CRITICAL, "critical"),
    ]

    target_type = models.CharField(max_length=16, choices=TARGET_CHOICES, db_index=True)
    target_id = models.PositiveIntegerField(db_index=True)
    title = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_OPEN, db_index=True)
    priority = models.CharField(max_length=16, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM, db_index=True)
    assigned_moderator_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
    reason = models.TextField(blank=True, default="")
    opened_by_user_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["target_type", "target_id", "status"]),
            models.Index(fields=["status", "priority", "created_at"]),
        ]


class ModerationReport(models.Model):
    case = models.ForeignKey(ModerationCase, on_delete=models.CASCADE, related_name="reports")
    reporter_user_id = models.CharField(max_length=64, db_index=True)
    text = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class EventEditProposal(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPLIED = "applied"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "pending"),
        (STATUS_APPLIED, "applied"),
        (STATUS_REJECTED, "rejected"),
    ]

    case = models.OneToOneField(ModerationCase, on_delete=models.CASCADE, related_name="event_edit_proposal")
    event_id = models.PositiveIntegerField(db_index=True)
    proposer_user_id = models.CharField(max_length=64, db_index=True)
    proposed_changes = models.JSONField(default=dict, blank=True)
    comment = models.TextField(blank=True, default="")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ModerationDecision(models.Model):
    DECISION_CONFIRM = "confirm"
    DECISION_REJECT = "reject"
    DECISION_HIDE = "hide"
    DECISION_RESTORE = "restore"
    DECISION_WARN = "warn"
    DECISION_RESTRICT = "restrict"
    DECISION_BAN = "ban"
    DECISION_CHOICES = [
        (DECISION_CONFIRM, "confirm"),
        (DECISION_REJECT, "reject"),
        (DECISION_HIDE, "hide"),
        (DECISION_RESTORE, "restore"),
        (DECISION_WARN, "warn"),
        (DECISION_RESTRICT, "restrict"),
        (DECISION_BAN, "ban"),
    ]

    case = models.ForeignKey(ModerationCase, on_delete=models.CASCADE, related_name="decisions")
    decision = models.CharField(max_length=16, choices=DECISION_CHOICES, db_index=True)
    moderator_user_id = models.CharField(max_length=64, db_index=True)
    reason = models.TextField(blank=True, default="")
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class UserSanction(models.Model):
    TYPE_WARN = "warn"
    TYPE_RESTRICT = "restrict"
    TYPE_BAN = "ban"
    TYPE_CHOICES = [
        (TYPE_WARN, "warn"),
        (TYPE_RESTRICT, "restrict"),
        (TYPE_BAN, "ban"),
    ]

    STATUS_ACTIVE = "active"
    STATUS_REVOKED = "revoked"
    STATUS_EXPIRED = "expired"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "active"),
        (STATUS_REVOKED, "revoked"),
        (STATUS_EXPIRED, "expired"),
    ]

    user_id = models.PositiveIntegerField(db_index=True)
    case = models.ForeignKey(ModerationCase, null=True, blank=True, on_delete=models.SET_NULL, related_name="sanctions")
    sanction_type = models.CharField(max_length=16, choices=TYPE_CHOICES, db_index=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True)
    reason = models.TextField(blank=True, default="")
    starts_at = models.DateTimeField(auto_now_add=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_by_user_id = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
