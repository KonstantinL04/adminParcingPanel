from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from .models import IdentityUser, UserProfile, UserReputationLog, ReputationRule


DEFAULT_REPUTATION_DELTAS = {
    UserReputationLog.ACTION_EVENT_CREATED: 1,
    UserReputationLog.ACTION_EVENT_CONFIRMED: 2,
    UserReputationLog.ACTION_EVENT_DENIED: -2,
    UserReputationLog.ACTION_EDIT_APPROVED: 1,
    UserReputationLog.ACTION_EDIT_REJECTED: -1,
    UserReputationLog.ACTION_HELP_COMPLETED: 2,
    UserReputationLog.ACTION_HELP_FAILED: -2,
    UserReputationLog.ACTION_HELP_CANCELED: -1,
}


def apply_reputation_change(user, action, delta=None, comment="", source_object=None):
    if not isinstance(user, IdentityUser):
        user = IdentityUser.objects.filter(id=user).first()
    if not user:
        return None

    if delta is None:
        rule = ReputationRule.objects.filter(action=action, enabled=True).first()
        delta = rule.reputation_delta if rule else DEFAULT_REPUTATION_DELTAS.get(action, 0)

    with transaction.atomic():
        profile, _ = UserProfile.objects.select_for_update().get_or_create(user=user)
        profile.reputation = int(profile.reputation or 0) + int(delta)
        profile.save(update_fields=["reputation"])

        content_type = None
        object_id = None
        if source_object is not None:
            content_type = ContentType.objects.get_for_model(source_object.__class__)
            object_id = source_object.pk

        return UserReputationLog.objects.create(
            user=user,
            action=action,
            reputation_delta=int(delta),
            total_reputation=profile.reputation,
            comment=comment or "",
            content_type=content_type,
            object_id=object_id,
        )
