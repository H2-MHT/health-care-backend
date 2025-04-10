from django.db import models
from django.db.models import Avg
from doctors.models import Doctor
# Create your models here.


class ServicesProvided(models.Model):
    title = models.CharField(max_length=200)

    def __str__(self):
        return self.title


class Language(models.Model):
    title = models.CharField(max_length=200)

    def __str__(self):
        return self.title


CLINIC_TYPE_CHOICES = ((0, "Public"), (1, "Private"), (2, "Specialty"))


class Clinic(models.Model):
    user = models.OneToOneField("users.User", on_delete=models.SET_NULL, related_name="clinic_user", null=True, blank=True)
    address = models.TextField(blank=True, default="")
    contact_phone = models.CharField(max_length=20, blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    website = models.URLField(blank=True, default="")
    services_provided = models.ManyToManyField(ServicesProvided, blank=True)
    licenses_certificate = models.FileField(upload_to="certificate", null=True, blank=True)
    administrator_name = models.CharField(max_length=255, blank=True, default="")
    administrator_email = models.EmailField(blank=True, default="")
    clinic_type = models.PositiveSmallIntegerField(choices=CLINIC_TYPE_CHOICES, default=0, null=True)
    license_number = models.CharField(max_length=500, blank=True, default="")
    public_name = models.CharField(max_length=255, blank=True, default="")
    clinic_logo = models.ImageField(upload_to="clinic_logo", null=True, blank=True)
    organisation_name = models.CharField(max_length=255, blank=True, default="")
    optional_information = models.CharField(max_length=500, blank=True, default="")

    def __str__(self):
        return self.user.first_name if self.user else str(self.id)


class ClinicReview(models.Model):
    clinic = models.ForeignKey("clinics.Clinic", on_delete=models.CASCADE, related_name="reviews")
    doctor = models.ForeignKey("doctors.Doctor", on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(default=0)
    title = models.CharField(max_length=255, blank=True, default="")
    content = models.TextField(blank=True, default="")
    recommend = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.doctor} for Clinic {self.clinic}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.update_clinic_user_rating()

    def update_clinic_user_rating(self):
        """ Update the doctor's User model rating and review count """
        if self.clinic and self.clinic.user:
            clinic_user = self.clinic.user
            clinic_reviews = ClinicReview.objects.filter(clinic=self.clinic, rating__isnull=False)

            avg_rating = clinic_reviews.aggregate(Avg("rating"))["rating__avg"] or 0
            review_count = clinic_reviews.count()

            clinic_user.rating = avg_rating
            clinic_user.reviews = review_count
            clinic_user.save()


class ClinicReviewReply(models.Model):
    review = models.ForeignKey(ClinicReview, on_delete=models.CASCADE, related_name="clinic_replies")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Reply by {self.user} to review {self.review.id}"

class OtherClinic(models.Model):
    choices=[('Others','Others')]
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    clinic_name=models.CharField(max_length=255,null=False)
    address=models.CharField(max_length=255,null=False)
    website=models.CharField(max_length=255,null=True, blank=True)