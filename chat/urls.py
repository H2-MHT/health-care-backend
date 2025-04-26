from django.urls import path
from chat.views import *

urlpatterns = [
    path("chat-room/", ChatRoomAPIView.as_view()),
    path("chat-message/<int:room_id>/", ChatMessageAPIView.as_view()),
]
