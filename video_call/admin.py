from django.contrib import admin
from .models import (
        Agoratoken,
        Recording,
        MeetingRoom,
        VideoCallTimeTracker
)
# Register your models here.

admin.site.register(Agoratoken)
admin.site.register(Recording)
admin.site.register(MeetingRoom)
admin.site.register(VideoCallTimeTracker)