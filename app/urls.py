"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from adminparcing.api import (
    ChatViewSet,
    ExcludedUserViewSet,
    AlertCategoryViewSet,
    RegionViewSet,
    CityViewSet,
    LocationViewSet, 
    RouteViewSet, 
    SettingViewSet, 
    SettingAPIViewSet, 
    ParserViewSet,
    NlpViewSet
)
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register("chats", ChatViewSet, basename="chats")
router.register("excluded_users", ExcludedUserViewSet, basename="excluded_users")
router.register("alert_categories", AlertCategoryViewSet, basename="alert_categories")
router.register("regions", RegionViewSet, basename="regions")
router.register("cities", CityViewSet, basename="cities")
router.register("locations", LocationViewSet, basename="locations")
router.register("routes", RouteViewSet, basename="routes")
router.register("settings", SettingViewSet, basename="settings")
router.register("settings_api", SettingAPIViewSet, basename="settings_api")
router.register("parser", ParserViewSet, basename="parser")
router.register("nlp", NlpViewSet, basename="nlp")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path("api/events/", include("events.urls")),
    path("api/accounts/", include("accounts.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
