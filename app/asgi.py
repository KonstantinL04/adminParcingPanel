"""
ASGI config for app project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from assistance.routing import websocket_urlpatterns as assistance_websocket_urlpatterns
from events.routing import websocket_urlpatterns as events_websocket_urlpatterns
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.settings")
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(events_websocket_urlpatterns + assistance_websocket_urlpatterns)
    ),
})
