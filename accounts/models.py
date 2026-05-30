from django.db import models
from django.contrib.auth.hashers import check_password, make_password
from django.utils.crypto import salted_hmac
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class IdentityUser(models.Model):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True, null=True, blank=True)
    password_hash = models.CharField(max_length=255)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    last_login = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_username(self):
        return self.username or self.email

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password_hash)

    def get_session_auth_hash(self):
        return salted_hmac(
            "accounts.IdentityUser.get_session_auth_hash",
            self.password_hash,
        ).hexdigest()

    def get_session_auth_fallback_hash(self):
        return []

    def has_perm(self, perm, obj=None):
        return bool(self.is_active and (self.is_superuser or self.is_staff))

    def has_perms(self, perm_list, obj=None):
        return all(self.has_perm(perm, obj=obj) for perm in perm_list)

    def has_module_perms(self, app_label):
        return bool(self.is_active and (self.is_superuser or self.is_staff))


class UserProfile(models.Model):
    user = models.OneToOneField(IdentityUser, on_delete=models.CASCADE, related_name="profile")

    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    nickname = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)

    reputation = models.IntegerField(default=0)
    status = models.CharField(max_length=32, default="active")

    def __str__(self):
        return f"{self.user.email} profile"

class UserReputationLog(models.Model):
    ACTION_EVENT_CREATED = "event_created"
    ACTION_EVENT_CONFIRMED = "event_confirmed"
    ACTION_EVENT_DENIED = "event_denied"

    ACTION_EDIT_APPROVED = "edit_approved"
    ACTION_EDIT_REJECTED = "edit_rejected"

    ACTION_HELP_COMPLETED = "help_completed"
    ACTION_HELP_FAILED = "help_failed"
    ACTION_HELP_CANCELED = "help_canceled"

    ACTION_CHOICES = [
        (ACTION_EVENT_CREATED, "event_created"),
        (ACTION_EVENT_CONFIRMED, "event_confirmed"),
        (ACTION_EVENT_DENIED, "event_denied"),

        (ACTION_EDIT_APPROVED, "edit_approved"),
        (ACTION_EDIT_REJECTED, "edit_rejected"),

        (ACTION_HELP_COMPLETED, "help_completed"),
        (ACTION_HELP_FAILED, "help_failed"),
        (ACTION_HELP_CANCELED, "help_canceled"),
    ]

    user = models.ForeignKey(
        IdentityUser,
        on_delete=models.CASCADE,
        related_name="reputation_logs"
    )

    action = models.CharField(
        max_length=64,
        choices=ACTION_CHOICES,
        db_index=True
    )

    reputation_delta = models.IntegerField()
    total_reputation = models.IntegerField()
    comment = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    # Универсальная связь с сущностью-источником
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey(
        "content_type",
        "object_id"
    )

    class Meta:
        ordering = ["-created_at"]


class ReputationRule(models.Model):
    action = models.CharField(
        max_length=64,
        choices=UserReputationLog.ACTION_CHOICES,
        unique=True,
        db_index=True
    )
    title = models.CharField(max_length=128)
    reputation_delta = models.IntegerField(default=0)
    description = models.CharField(max_length=255, blank=True, default="")
    enabled = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["action"]

    def __str__(self):
        return f"{self.action}: {self.reputation_delta}"


class Role(models.Model):
    name = models.CharField(max_length=64, unique=True)
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name


class UserRole(models.Model):
    user = models.ForeignKey(IdentityUser, on_delete=models.CASCADE, related_name="roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="users")

    class Meta:
        unique_together = ("user", "role")

    def __str__(self):
        return f"{self.user.email} -> {self.role.name}"


class AuthIdentity(models.Model):
    PROVIDER_CHOICES = [
        ("apple", "apple"),
        ("google", "google"),
        ("telegram", "telegram"),
        ("email", "email"),
    ]

    user = models.ForeignKey(IdentityUser, on_delete=models.CASCADE, related_name="identities")
    provider = models.CharField(max_length=32, choices=PROVIDER_CHOICES)
    provider_user_id = models.CharField(max_length=255)
    email = models.EmailField(null=True, blank=True)
    linked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("provider", "provider_user_id")

    def __str__(self):
        return f"{self.provider}:{self.provider_user_id}"


class AppPurchase(models.Model):
    PLATFORM_APPSTORE = "appstore"
    PLATFORM_CHOICES = [
        (PLATFORM_APPSTORE, "appstore"),
    ]

    STATUS_PENDING = "pending"
    STATUS_VERIFIED = "verified"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "pending"),
        (STATUS_VERIFIED, "verified"),
        (STATUS_REJECTED, "rejected"),
    ]

    user = models.ForeignKey(IdentityUser, on_delete=models.CASCADE, related_name="app_purchases")
    platform = models.CharField(max_length=32, choices=PLATFORM_CHOICES, default=PLATFORM_APPSTORE)
    transaction_id = models.CharField(max_length=255, unique=True)
    product_id = models.CharField(max_length=255)
    verification_status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    grants_full_access = models.BooleanField(default=False, db_index=True)
    purchased_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verification_error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "grants_full_access"]),
        ]

    def __str__(self):
        return f"{self.user.email} -> {self.product_id}"
