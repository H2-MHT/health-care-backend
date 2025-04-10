from django.urls import path
from .views import SendNotificationView, CreateAgoraChatUserAPIView, AgoraUserReceiverIDAPIView,StartRecordingAPIView, StopRecordingAPIView

urlpatterns = [
    path('send-notification/', SendNotificationView.as_view(), name='send-notification'),
     # agora video call
    path('video-chat/', CreateAgoraChatUserAPIView.as_view(), name='agora-video-chat'),
    # agora receiver user id
    path('agora-user-receiverid/', AgoraUserReceiverIDAPIView.as_view(), name='agora-receiver-id'),
    # start recording
    path('start-recording/', StartRecordingAPIView.as_view(), name='start-recording'),
    # stop recording
    path('stop-recording/', StopRecordingAPIView.as_view(), name='stop-recording'),
        
]
