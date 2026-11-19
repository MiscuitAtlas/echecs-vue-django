from django.urls import path

from .consumers import GameConsumer

websocket_urlpatterns = [path("ws/parties/<str:code>/", GameConsumer.as_asgi())]
