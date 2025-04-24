from django.db import models
from doctors.models import (
    BookedAppointment,
    Doctor,
)
from patients.models import Patient
from users.models import User
# Create your models here.
class ConsultationSummary(models.Model):
    appointment = models.OneToOneField(
        "appointments.Appointment", on_delete=models.CASCADE
    )
    ai_generated_summary = models.TextField(null=True, blank=True)
    human_verified_summary = models.TextField(null=True, blank=True)
    translated_languages = models.JSONField(null=True, blank=True)

class Prescription(models.Model):
    appointment = models.OneToOneField(BookedAppointment, on_delete=models.CASCADE)
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'Doctor'})
    medicines = models.JSONField(null=True, blank=True)
    diagnosis = models.TextField(null=True, blank=True)
    additional_instruction = models.TextField(null=True, blank=True)
    pdf_file = models.FileField(upload_to='prescription/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ConsultationReport(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    appointment = models.ForeignKey(BookedAppointment, on_delete=models.CASCADE)
    short_description = models.TextField(null=True, blank=True)
    translated_text= models.TextField(null=True, blank=True)
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, null=True, blank=True)
    recommendation = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Consultation for {self.doctor} by {self.patient} on {self.created_at}'
    
