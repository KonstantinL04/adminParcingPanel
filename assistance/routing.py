from django.urls import re_path

from .consumers import HelpPresenceConsumer, HelpRequestConsumer


websocket_urlpatterns = [
    re_path(r"ws/help-requests/(?P<help_request_id>\d+)/$", HelpRequestConsumer.as_asgi()),
    re_path(r"ws/help-presence/$", HelpPresenceConsumer.as_asgi()),
]
