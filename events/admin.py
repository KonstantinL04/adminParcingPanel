from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import (
    EventClass,
    EventClassItem,
    MapEvent,
    EventMedia,
    EntityVote,
    PocketGisSource,
    PocketGisImport,
)


@admin.register(EventClass)
class EventClassAdmin(admin.ModelAdmin):
    list_display = ["name", "sort_order", "enabled", "created_at"]
    list_filter = ["enabled"]
    search_fields = ["name"]
    ordering = ["sort_order", "name"]


@admin.register(EventClassItem)
class EventClassItemAdmin(admin.ModelAdmin):
    list_display = ["name", "event_class", "source_kind", "sort_order", "enabled"]
    list_filter = ["enabled", "source_kind", "event_class"]
    search_fields = ["name", "event_class__name"]
    ordering = ["event_class__sort_order", "sort_order", "name"]


@admin.register(MapEvent)
class MapEventAdmin(GISModelAdmin):
    list_display = ["id", "get_class_item_name", "source_kind", "source", "status", "is_active", "created_at"]
    list_filter = ["source_kind", "source", "status", "is_active"]
    search_fields = ["details", "source_name", "source_object_id"]
    readonly_fields = ["first_seen_at", "last_seen_at", "created_at"]
    ordering = ["-created_at"]

    def get_class_item_name(self, obj):
        return getattr(obj.class_item, 'name', '-')
    get_class_item_name.short_description = "Category"
    get_class_item_name.admin_order_field = "class_item__name"


@admin.register(EventMedia)
class EventMediaAdmin(admin.ModelAdmin):
    list_display = ["id", "event", "user_id", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["user_id", "event__id"]


@admin.register(EntityVote)
class EntityVoteAdmin(admin.ModelAdmin):
    list_display = ["id", "event", "user_id", "vote", "created_at"]
    list_filter = ["vote", "created_at"]
    search_fields = ["user_id", "event__id"]


@admin.register(PocketGisSource)
class PocketGisSourceAdmin(admin.ModelAdmin):
    list_display = ["name", "enabled", "last_sync_at", "last_status"]
    list_filter = ["enabled"]
    search_fields = ["name"]


@admin.register(PocketGisImport)
class PocketGisImportAdmin(admin.ModelAdmin):
    list_display = ["id", "source", "file_name", "status", "rows_total", "rows_inserted", "created_at"]
    list_filter = ["status", "created_at"]
    readonly_fields = ["created_at", "finished_at"]
