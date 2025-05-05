import random
import string
from django.db import models
from users.models import User
from django.core.exceptions import ValidationError
from django.utils.timezone import now

# Create your models here.

def validate_past_date(value):
    if value >= now().date():
        raise ValidationError("not the feasible date")

class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="patient_profile")
    chronic_conditions = models.TextField(null=True, blank=True)
    show_email = models.BooleanField(default=True)
    show_phone = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Patient"
        verbose_name_plural = "Patients"

    def __str__(self):
        return self.user.get_full_name()


class DashboardMedicalHistory(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="medical_documents")
    file = models.FileField(upload_to="medical_documents/", null=True, blank=True )
    title = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    condition = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    diagnosis_date = models.TextField(null=True, blank=True)
    
    
class MedicalHistory(models.Model):
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="medical_documents")
    name = models.CharField(max_length=255, null=True, blank=True)
    document_link= models.TextField(default="")
    date = models.DateField(validators=[validate_past_date],null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class AllergyDocument(models.Model):
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="allergy_documents")
    name = models.CharField(max_length=255, null=True, blank=True)
    document_link= models.TextField(default="")
    date = models.DateField(validators=[validate_past_date],null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name = "Allergy Document"
        verbose_name_plural = "Allergy Documents"


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


class FamilyMember(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="family_members")
    member_name = models.CharField(max_length=100)
    member_email = models.EmailField(max_length=100, null=True,blank=True)
    family_status = models.CharField(max_length=100)
    member_profile = models.FileField(upload_to="family_profiles/", null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    def __str__(self):
        return f"Family Member - {self.patient.user.get_full_name()}"

class OTPVerification(models.Model):
    family_member = models.OneToOneField(FamilyMember, on_delete=models.CASCADE, related_name="otp_verification")
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def generate_otp():
        """Generate a 6-digit random OTP."""
        return ''.join(random.choices(string.digits, k=6))



class Reminder(models.Model):
    NOTIFICATION_METHODS = [
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('whatsapp', 'WhatsApp'),
    ]
    
    TIME_TYPES = [
        ('days', 'Days'),
        ('hours', 'Hours'),
        ('minutes', 'Minutes'),
    ]

    appointment = models.ForeignKey('doctors.BookedAppointment', on_delete=models.CASCADE)

    notification_method = models.CharField(max_length=20, choices=NOTIFICATION_METHODS)
    notification_time = models.PositiveIntegerField()
    notification_time_type = models.CharField(max_length=10, choices=TIME_TYPES)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Prevents duplicate reminders for the same appointment and method
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[ 'appointment', 'notification_method'],
                name='unique_reminder_per_method'
            )
        ]
        
        verbose_name = "Reminder"
        verbose_name_plural = "Reminders"
    
    def __str__(self):
        return f"Reminder for Appointment {self.appointment.id}"