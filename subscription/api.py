from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import AllowAny
from .models import SubscriptionPlan, UserSubscription
from .serializers import SubscriptionPlanSerializer, UserSubscriptionSerializer

class SubscriptionPlanViewSet(ModelViewSet):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [AllowAny]

class UserSubscriptionViewSet(ModelViewSet):
    queryset = UserSubscription.objects.select_related("user", "plan").all()
    serializer_class = UserSubscriptionSerializer
    permission_classes = [AllowAny]
