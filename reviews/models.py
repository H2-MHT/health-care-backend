from django.db import models
from users.models import User
from django.db.models import Avg, Count

# Create your models here.


class Review(models.Model):
    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE)
    doctor = models.ForeignKey("doctors.Doctor", on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=255, null=True, blank=True)
    content = models.TextField(null=True, blank=True)
    recommend = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.update_doctor_user_rating()

    def update_doctor_user_rating(self):
        """ Update the doctor's User model rating and review count """
        if self.doctor and self.doctor.user:
            doctor_user = self.doctor.user
            doctor_reviews = Review.objects.filter(doctor=self.doctor, rating__isnull=False)

            avg_rating = doctor_reviews.aggregate(Avg("rating"))["rating__avg"] or 0
            review_count = doctor_reviews.count()

            doctor_user.rating = avg_rating
            doctor_user.reviews = review_count
            doctor_user.save()

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
