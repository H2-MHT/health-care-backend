from django.urls import path
from .views import SendNotificationView, CreateAgoraChatUserAPIView, AgoraUserReceiverIDAPIView

urlpatterns = [
    path('send-notification/', SendNotificationView.as_view(), name='send-notification'),
     # agora video call
    path('video-chat/', CreateAgoraChatUserAPIView.as_view(), name='agora-video-chat'),
    # agora receiver user id
    path('agora-user-receiverid/', AgoraUserReceiverIDAPIView.as_view(), name='agora-receiver-id')
]
