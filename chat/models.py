from django.db import models
from users.models import User

# Create your models here.


class ChatRoom(models.Model):
    room_name = models.CharField(max_length=100, unique=True)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sender")
    receiver = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="receiver"
    )
    doc = models.DateTimeField(auto_now_add=True)
    last_update = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("sender", "receiver")

    def __str__(self):
        return self.room_name+'-'+str(self.sender.email)+'-'+str(self.receiver.email)




class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE)
    message = models.TextField(blank=True)
    file = models.FileField(upload_to='chat_files/', null=True)
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="sender_message"
    )
    receiver = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="receiver_message"
    )
    doc = models.DateTimeField(auto_now_add=True)
    seen = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.room.last_update = self.doc
        self.room.save()

    def __str__(self):
        return str(self.sender.email) + "-" + str(self.receiver.email)
