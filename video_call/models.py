from django.db import models
from users.models import User
# Create your models here.

class Agoratoken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    userID = models.IntegerField()
    token = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"user id:-{self.user_id}"