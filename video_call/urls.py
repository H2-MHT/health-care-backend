from django.urls import path
from .views import SendNotificationView, CreateAgoraChatUserAPIView

urlpatterns = [
    path('send-notification/', SendNotificationView.as_view(), name='send-notification'),
    
     # agora video call
    path('video-chat/', CreateAgoraChatUserAPIView.as_view(), name='agora-video-chat'),
]
