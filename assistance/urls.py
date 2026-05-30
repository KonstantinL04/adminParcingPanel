from rest_framework.routers import DefaultRouter

from .api import HelperPresenceViewSet, HelpRequestViewSet


router = DefaultRouter()
router.register("help-requests", HelpRequestViewSet, basename="help-requests")
router.register("helper-presence", HelperPresenceViewSet, basename="helper-presence")

urlpatterns = router.urls
