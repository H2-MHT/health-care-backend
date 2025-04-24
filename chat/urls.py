from django.urls import path
from chat.views import *
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("chat-room/", ChatRoomAPIView.as_view()),
    path("chat-message/<int:room_id>/", ChatMessageAPIView.as_view()),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
