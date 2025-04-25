from django.db import models
from users.models import User
from doctors.models import(
    Doctor, 
    BookedAppointment
)
from patients.models import Patient
# Create your models here.

class Agoratoken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    userID = models.IntegerField()
    token = models.TextField()
    record_token = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"user id:-{self.user_id}"

class Recording(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sender_recording")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="receiver_recording")
    title = models.CharField(max_length=255)
    video_file = models.FileField(upload_to='recordings/')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Recording: {self.title} from {self.sender.get_full_name()} to {self.receiver.get_full_name()}"

STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Expired", "Expired")
        ]
class MeetingRoom(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    appointment = models.ForeignKey(BookedAppointment, on_delete=models.CASCADE)
    link = models.URLField(blank=True)
    channel_name = models.TextField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)