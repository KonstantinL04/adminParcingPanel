from django.db import models

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
        "IdentityAuth.IdentityUser",
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
