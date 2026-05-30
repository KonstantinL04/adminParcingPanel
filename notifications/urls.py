from rest_framework.routers import DefaultRouter
from .api import (
    NotificationTemplateViewSet,
    DeviceTokenViewSet,
    NotificationJobViewSet,
    NotificationDeliveryViewSet,
    DrivingAlertViewSet,
)

router = DefaultRouter()
router.register("templates", NotificationTemplateViewSet, basename="notification-templates")
router.register("devices", DeviceTokenViewSet, basename="notification-devices")
router.register("jobs", NotificationJobViewSet, basename="notification-jobs")
router.register("deliveries", NotificationDeliveryViewSet, basename="notification-deliveries")
router.register("driving", DrivingAlertViewSet, basename="notification-driving")

urlpatterns = router.urls
