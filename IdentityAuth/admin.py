from django.contrib import admin
from .models import IdentityUser, UserProfile, Role, UserRole, AuthIdentity

admin.site.register(IdentityUser)
admin.site.register(UserProfile)
admin.site.register(Role)
admin.site.register(UserRole)
admin.site.register(AuthIdentity)
