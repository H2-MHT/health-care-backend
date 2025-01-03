from django.db import models
from users.models import User
# Create your models here.


class Review(models.Model):
    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE)
    doctor = models.ForeignKey("doctors.Doctor", on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()
    content = models.TextField(null=True, blank=True)
    recommend = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # def __str__(self):
    #     return f"{self.patient.user.first_name} - {self.doctor.user.first_name} - {self.rating}"
    def __str__(self):
        return f"Review by {self.patient} for Doctor {self.doctor}"
    
class Reply(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="replies")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)  # Could be patient or doctor
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Reply by {self.user} to review {self.review.id}"
