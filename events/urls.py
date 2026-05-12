# urls.py

from rest_framework.routers import DefaultRouter
from .api import (
    EventClassViewSet,
    EventClassItemViewSet,
    MapEventViewSet,
    EntityVoteViewSet,
    PocketGisSourceViewSet,
    PocketGisImportViewSet,
)

router = DefaultRouter()

# Каталог событий
router.register("event-classes", EventClassViewSet, basename="event-classes")
router.register("event-class-items", EventClassItemViewSet, basename="event-class-items")

# Точки на карте (единый endpoint)
router.register("events", MapEventViewSet, basename="events")

# Голосование
router.register("votes", EntityVoteViewSet, basename="votes")

# Импорт PocketGIS
router.register("pocketgis/sources", PocketGisSourceViewSet, basename="pocketgis-sources")
router.register("pocketgis/imports", PocketGisImportViewSet, basename="pocketgis-imports")

urlpatterns = router.urls