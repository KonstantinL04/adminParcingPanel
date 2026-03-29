from rest_framework.routers import DefaultRouter
from .api import SubscriptionPlanViewSet, UserSubscriptionViewSet

router = DefaultRouter()
router.register("plans", SubscriptionPlanViewSet, basename="subscription_plans")
router.register("user_subscriptions", UserSubscriptionViewSet, basename="user_subscriptions")

urlpatterns = router.urls
