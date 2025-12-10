from django.contrib import admin
from .models import Chat, ExcludedUser, EmojiGroup, TextPattern, Location, Setting, SettingAPI

admin.site.register(Chat)
admin.site.register(ExcludedUser)
admin.site.register(EmojiGroup)
admin.site.register(TextPattern)
admin.site.register(Location)
admin.site.register(Setting)

@admin.register(SettingAPI)
class SettingAPIAdmin(admin.ModelAdmin):
    list_display = ("key", "decrypted_value")

    def decrypted_value(self, obj):
        return obj.value
    decrypted_value.short_description = "Value"