from django.contrib import admin

from .models import (
    AlertCategory,
    Chat,
    City,
    ExcludedUser,
    Location,
    ParsedMessage,
    Region,
    Setting,
    SettingAPI,
)

admin.site.register(Chat)
admin.site.register(ExcludedUser)
admin.site.register(AlertCategory)
admin.site.register(Location)
admin.site.register(Setting)
admin.site.register(Region)
admin.site.register(City)


@admin.register(ParsedMessage)
class ParsedMessageAdmin(admin.ModelAdmin):
    list_display = ["id", "chat", "parsing_category", "author_name", "created_at", "parsed_at"]
    list_filter = ["created_at", "parsing_category"]
    search_fields = ["text", "author_name", "chat__title"]

@admin.register(SettingAPI)
class SettingAPIAdmin(admin.ModelAdmin):
    list_display = ("key", "decrypted_value")

    def decrypted_value(self, obj):
        return obj.value
    decrypted_value.short_description = "Value"
