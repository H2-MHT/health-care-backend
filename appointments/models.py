from django.db import models

from users.models import User


# Create your models here.


class Appointment(models.Model):
    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE)
    doctor = models.ForeignKey("doctors.Doctor", on_delete=models.CASCADE)
    clinic = models.ForeignKey("clinics.Clinic", on_delete=models.CASCADE)
    date_time = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=[
            ("Pending", "Pending"),
            ("Confirmed", "Confirmed"),
            ("Completed", "Completed"),
            ("Cancelled", "Cancelled"),
            ("Archived", "Archived"),
        ],
    )
    records = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Appointment with {self.doctor} on {self.date_time}"

    def get_status(self):
        return self.status


class Chat(models.Model):
    appointment = models.ForeignKey(Appointment, related_name='chats', on_delete=models.CASCADE)
    participants = models.ManyToManyField(User, related_name='appointment_chats')
    created_at = models.DateTimeField(auto_now_add=True)


class Message(models.Model):
    chat = models.ForeignKey(Chat, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    content = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='chat_files/', blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)


class Call(models.Model):
    chat = models.ForeignKey(Chat, related_name='calls', on_delete=models.CASCADE)
    caller = models.ForeignKey(User, related_name='outgoing_calls', on_delete=models.CASCADE)
    callee = models.ForeignKey(User, related_name='incoming_calls', on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(blank=True, null=True)
    call_duration = models.DurationField(blank=True, null=True)
    recording = models.FileField(upload_to='call_recordings/', blank=True, null=True)
