from django.db import models
from users.models import User
# Create your models here.


class Review(models.Model):
    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE)
    doctor = models.ForeignKey("doctors.Doctor", on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()
    content = models.TextField(null=True, blank=True)
    recommend = models.BooleanField(default=False)
    reply = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.patient.user.first_name} - {self.doctor.user.first_name} - {self.rating}"
