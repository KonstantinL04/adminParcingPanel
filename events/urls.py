from rest_framework.routers import DefaultRouter
from .api import ParsedMessageViewSet, RoadEventViewSet, EventVoteViewSet

router = DefaultRouter()
router.register("messages", ParsedMessageViewSet, basename="events-messages")
router.register("road-events", RoadEventViewSet, basename="events-road-events")
router.register("votes", EventVoteViewSet, basename="events-votes")

urlpatterns = router.urls
