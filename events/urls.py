from rest_framework.routers import DefaultRouter
from .api import (
    ParsedMessageViewSet,
    RoadEventViewSet,
    EventVoteViewSet,
    PocketGisSourceViewSet,
    PocketGisImportViewSet,
    PocketGisPointViewSet,
    PocketGisCategoryViewSet,
)

router = DefaultRouter()
router.register("messages", ParsedMessageViewSet, basename="events-messages")
router.register("road-events", RoadEventViewSet, basename="events-road-events")
router.register("votes", EventVoteViewSet, basename="events-votes")
router.register("pocketgis/sources", PocketGisSourceViewSet, basename="events-pocketgis-sources")
router.register("pocketgis/imports", PocketGisImportViewSet, basename="events-pocketgis-imports")
router.register("pocketgis/points", PocketGisPointViewSet, basename="events-pocketgis-points")
router.register("pocketgis/categories", PocketGisCategoryViewSet, basename="events-pocketgis-categories")

urlpatterns = router.urls
