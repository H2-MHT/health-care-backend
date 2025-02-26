"""
ASGI config for DjanoChannelsPOC project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path
from chat.consumers import ChatConsumer
from channels.auth import AuthMiddlewareStack

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "health_care_backend.settings")
application = get_asgi_application()

application = ProtocolTypeRouter(
    {
        "http": application,
        "websocket": AuthMiddlewareStack(
            URLRouter(
                [
                    path("ws/chat/<str:room_name>", ChatConsumer.as_asgi()),
                ]
            )
        ),
    }
)
