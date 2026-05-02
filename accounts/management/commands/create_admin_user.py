from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import IdentityUser, Role, UserProfile, UserRole


class Command(BaseCommand):
    help = "Create or update main admin user for session-based auth"

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Admin email")
        parser.add_argument("--password", required=True, help="Admin password")
        parser.add_argument("--username", default="admin", help="Admin username")
        parser.add_argument("--first-name", default="", help="Profile first name")
        parser.add_argument("--last-name", default="", help="Profile last name")

    @transaction.atomic
    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        password = options["password"]
        username = options["username"].strip()
        first_name = options["first_name"].strip()
        last_name = options["last_name"].strip()

        if not email:
            raise CommandError("Email cannot be empty")
        if len(password) < 8:
            raise CommandError("Password must contain at least 8 characters")

        user, created = IdentityUser.objects.get_or_create(
            email=email,
            defaults={"username": username},
        )

        # Keep username unique if admin already exists with another value.
        if username and user.username != username:
            clash = IdentityUser.objects.filter(username=username).exclude(pk=user.pk).exists()
            if clash:
                raise CommandError(f"Username '{username}' is already used by another user")
            user.username = username

        user.set_password(password)
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        if first_name:
            profile.first_name = first_name
        if last_name:
            profile.last_name = last_name
        profile.save()

        admin_role, _ = Role.objects.get_or_create(
            name="admin",
            defaults={"description": "System administrator"},
        )
        UserRole.objects.get_or_create(user=user, role=admin_role)

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} admin user: {email}"))
