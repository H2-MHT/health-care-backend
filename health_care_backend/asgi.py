"""
ASGI config for DjanoChannelsPOC project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path
from chat.consumers import ChatConsumer
from video_call.consumers import DeepgramConsumer
from channels.auth import AuthMiddlewareStack
from video_call.chat import VideoCallConsumer

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "health_care_backend.settings")
django.setup()
django_asgi_app= get_asgi_application()

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(
                [
                    path("ws/chat/<str:room_name>", ChatConsumer.as_asgi()),
                    path("ws/transcribe/", DeepgramConsumer.as_asgi()), 
                    path("ws/video/<str:room_name>/", VideoCallConsumer.as_asgi())
                ]
            )
        ),
    }
)
