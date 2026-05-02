from django.db import models
from django.contrib.auth.hashers import check_password, make_password
from django.utils.crypto import salted_hmac


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


class SubscriptionPlan(models.Model):
    code = models.CharField(max_length=64, unique=True)
    title = models.CharField(max_length=128)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    period = models.CharField(max_length=32)
    features = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code


class UserSubscription(models.Model):
    STATUS_CHOICES = [
        ("active", "active"),
        ("trial", "trial"),
        ("canceled", "canceled"),
        ("expired", "expired"),
    ]

    PROVIDER_CHOICES = [
        ("appstore", "appstore"),
        ("googleplay", "googleplay"),
        ("stripe", "stripe"),
        ("manual", "manual"),
    ]

    user = models.ForeignKey(
        IdentityUser,
        on_delete=models.CASCADE,
        related_name="subscriptions"
    )
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="subscriptions")

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="active")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=True)

    provider = models.CharField(max_length=16, choices=PROVIDER_CHOICES, default="manual")
    provider_subscription_id = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} -> {self.plan.code}"
