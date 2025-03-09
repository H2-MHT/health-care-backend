from django.db import models
from users.models import User
# Create your models here.


class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="patient_profile")
    chronic_conditions = models.TextField(null=True, blank=True)
    show_email = models.BooleanField(default=False)
    show_phone = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Patient"
        verbose_name_plural = "Patients"

    def __str__(self):
        return self.user.get_full_name()


class MedicalHistory(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="medical_documents")
    file = models.FileField(upload_to="medical_documents/", null=True, blank=True )
    title = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Medical Document - {self.patient.user.get_full_name()}"


class AllergyDocument(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="allergy_documents")
    file = models.FileField(upload_to="allergy_documents/", null=True, blank=True )
    description = models.TextField(null=True, blank=True)
    medicine_name = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name = "Allergy Document"
        verbose_name_plural = "Allergy Documents"

    def __str__(self):
        return f"Allergy Document - {self.patient.user.get_full_name()}"


class Favourite(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    fav_doc = models.ForeignKey(
        "doctors.Doctor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="favorite_patients",
    )
    doc_status = models.BooleanField(default=False)
    fav_clinic = models.ForeignKey(
        "clinics.Clinic",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="favorite_clinics",
    )
    clinic_status = models.BooleanField(default=False)

