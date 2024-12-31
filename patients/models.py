from django.db import models

# Create your models here.


class Patient(models.Model):
    user = models.OneToOneField("users.User", on_delete=models.CASCADE)
    chronic_conditions = models.TextField(null=True, blank=True)
    fav_doc = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="favorite_patients",
    )
    fav_clinic = models.ForeignKey(
        "clinics.Clinic", on_delete=models.SET_NULL, null=True, blank=True
    )
    current_medication = models.TextField(null=True, blank=True)
    allergies = models.TextField(null=True, blank=True)
    show_email = models.BooleanField(default=False)
    show_phone = models.BooleanField(default=False)
    health_documents = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.user.get_full_name()

class MedicalHistory(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    condition = models.CharField(max_length=255)
    diagnosis_date = models.DateField(null=True, blank=True)
    treatment_details = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=[("Active", "Active"), ("Resolved", "Resolved")]
    )
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
