from django.contrib import admin
from .models import Chat, ExcludedUser, AlertCategory, Location, Setting, SettingAPI, Region, City

admin.site.register(Chat)
admin.site.register(ExcludedUser)
admin.site.register(AlertCategory)
admin.site.register(Location)
admin.site.register(Setting)
admin.site.register(Region)
admin.site.register(City)

@admin.register(SettingAPI)
class SettingAPIAdmin(admin.ModelAdmin):
    list_display = ("key", "decrypted_value")

    def decrypted_value(self, obj):
        return obj.value
    decrypted_value.short_description = "Value"
