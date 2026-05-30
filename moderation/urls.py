from rest_framework.routers import DefaultRouter
from .api import (
    ModerationCaseViewSet,
    ModerationDecisionViewSet,
    ModerationReportViewSet,
    UserSanctionViewSet,
)

router = DefaultRouter()
router.register("cases", ModerationCaseViewSet, basename="moderation-cases")
router.register("decisions", ModerationDecisionViewSet, basename="moderation-decisions")
router.register("reports", ModerationReportViewSet, basename="moderation-reports")
router.register("sanctions", UserSanctionViewSet, basename="moderation-sanctions")

urlpatterns = router.urls
