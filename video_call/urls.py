from django.urls import path
from .views import (
    SendNotificationView, 
    CreateAgoraChatUserAPIView, 
    GenerateAgoraToken,
    AgoraUserReceiverIDAPIView,
    StartRecordingAPIView, 
    StopRecordingAPIView,
    AgoraTokenView,
    RecordingListAPIView,
    CreateMeetingLink,
    GenerateMeetingToken,
    UserInfoAPIView,
    VideoCallTimeTrackerAPIView
    
)

urlpatterns = [
    path('send-notification/', SendNotificationView.as_view(), name='send-notification'),
     # agora video call (common token for both)
    path('video-chat/', CreateAgoraChatUserAPIView.as_view(), name='agora-video-chat'),
    # create agora token(for sender and receiver)
    path('generate-token/', GenerateAgoraToken.as_view(), name='generate-token'),
    # agora receiver user id
    path('agora-user-receiverid/', AgoraUserReceiverIDAPIView.as_view(), name='agora-receiver-id'),
    # start recording
    path('start-recording/', StartRecordingAPIView.as_view(), name='start-recording'),
    # stop recording
    path('stop-recording/', StopRecordingAPIView.as_view(), name='stop-recording'),
    # agora token get
    path('get-agora-token/', AgoraTokenView.as_view(), name='agora-token'),
    # recording list
    path('recording-list/', RecordingListAPIView.as_view(), name="recording-list"),
    # Meeting link
    path('meeting-link/', CreateMeetingLink.as_view(), name='meeting-link'),
    # generate meeting token
    path('generate-meeting-token/', GenerateMeetingToken.as_view(), name="generate-meeting-token"),
    # user-info
    path('user-info/', UserInfoAPIView.as_view(), name='user-info'),
    path("time_tracker/", VideoCallTimeTrackerAPIView.as_view(), name="time_tracker")
        
]
