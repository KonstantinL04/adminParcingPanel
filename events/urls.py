from rest_framework.routers import DefaultRouter
from .api import ParsedMessageViewSet, MessageLocationViewSet, MessageRouteViewSet

router = DefaultRouter()
router.register("messages", ParsedMessageViewSet, basename="events-messages")
router.register("locations", MessageLocationViewSet, basename="events-locations")
router.register("routes", MessageRouteViewSet, basename="events-routes")

urlpatterns = router.urls