from django.db import models

# Create your models here.
class ConsultationSummary(models.Model):
    appointment = models.OneToOneField(
        "appointments.Appointment", on_delete=models.CASCADE
    )
    ai_generated_summary = models.TextField(null=True, blank=True)
    human_verified_summary = models.TextField(null=True, blank=True)
    translated_languages = models.JSONField(null=True, blank=True)

class Prescription(models.Model):
    appointment = models.OneToOneField(
        "appointments.Appointment", on_delete=models.CASCADE
    )
    doctor = models.ForeignKey("doctors.Doctor", on_delete=models.CASCADE)
    medicines = models.JSONField(null=True, blank=True)
    diagnosis = models.TextField(null=True, blank=True)
    additional_instruction = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

