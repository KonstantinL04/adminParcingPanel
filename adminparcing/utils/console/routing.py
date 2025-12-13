from django.urls import path
from .consumers import ParserConsoleConsumer

websocket_urlpatterns = [
    path("ws/parser-console/", ParserConsoleConsumer.as_asgi()),
]