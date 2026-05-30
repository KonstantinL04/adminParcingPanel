from django.contrib import admin

from .models import (
    IdentityUser,
    UserProfile,
    UserReputationLog,
    ReputationRule,
    Role,
    UserRole,
    AuthIdentity,
    AppPurchase,
)

admin.site.register(IdentityUser)
admin.site.register(UserProfile)
admin.site.register(UserReputationLog)
admin.site.register(ReputationRule)
admin.site.register(Role)
admin.site.register(UserRole)
admin.site.register(AuthIdentity)
admin.site.register(AppPurchase)
