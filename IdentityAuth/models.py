from django.db import models

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
