from django.db import models
from  users.models import User
import random

# Create your models here.


class Doctor(models.Model):
    user = models.OneToOneField("users.User", on_delete=models.CASCADE)
    specialty = models.CharField(max_length=255)
    qualifications = models.TextField(null=True, blank=True)
    experience_years = models.PositiveIntegerField(null=True, blank=True)
    available_dates = models.JSONField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return self.user.get_full_name()

class DoctorNotes(models.Model):
    doctor = models.ForeignKey(
        "users.User", 
        on_delete=models.CASCADE, 
        limit_choices_to={'role': 'Doctor'}, 
        related_name='notes_as_doctor'
    )
    title = models.CharField(max_length=255, help_text="Title of the doctor's note")
    note = models.TextField(help_text="Detailed note provided by the doctor")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Date and time when the note was created")
    updated_at = models.DateTimeField(auto_now=True, help_text="Date and time when the note was last updated")

    def __str__(self):
        return f"Note by Dr. {self.doctor.first_name}"


def generate_referral_code():
    """
    Generates a unique 7-digit personal referral code.
    """
    while True:
        code = ''.join(random.choices('0123456789', k=7))
        if not Referral.objects.filter(personal_code=code).exists():
            return code


class Referral(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='referral')
    personal_code = models.CharField(max_length=7, unique=True, default=generate_referral_code)
    registry_link = models.URLField(blank=True, null=True)
    points = models.IntegerField(default=0)
    users_invited = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.user.first_name}'s Referral"


class Invitation(models.Model):
    invited_by = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name='invitations')
    invitation_code = models.CharField(max_length=7)  # Personal code of the inviter
    invited_user_email = models.EmailField(unique=True)  # Email of the invitee
    invited_user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='invited_as')
    created_at = models.DateTimeField(auto_now_add=True)
    redeemed = models.BooleanField(default=False)  # To track if the invitation was used

    def __str__(self):
        return f"Invitation by {self.invited_by.user.username} to {self.invited_user_email}"


class AppointmentManagement(models.Model):
    
    DAYS_CHOICES = [
        ('Mon', 'Monday'),
        ('Tue', 'Tuesday'),
        ('Wed', 'Wednesday'),
        ('Thu', 'Thursday'),
        ('Fri', 'Friday'),
        ('Sat', 'Saturday'),
        ('Sun', 'Sunday'),
    ]
    
    APPOINTMENT_TYPE_CHOICES = [
        ('Planned', 'Planned consultation'),
        ('Urgent', 'Urgent call'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="appointment_preferences")
    appointment_type = models.CharField(max_length=50, choices=APPOINTMENT_TYPE_CHOICES)
    days = models.CharField(max_length=100, help_text="Comma-separated days, e.g., Mon,Fri,Sat")
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    def __str__(self):
        return f"{self.appointment_type} ({self.days} {self.start_time}-{self.end_time})"


class ConsultationSettings(models.Model):
    CONSULTATION_TYPE_CHOICES = [
        ('planned', 'Planned Consultation'),
        ('urgent', 'Urgent Call'),
    ]
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    session_type = models.CharField(max_length=50, choices=CONSULTATION_TYPE_CHOICES)
    session_length = models.IntegerField(choices=[(15, '15 minutes'), (30, '30 minutes')])
    buffer_time = models.DurationField(blank=True, null=True)
    planned_fee_per_15_min = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    urgent_fee_per_15_min = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"{self.session_type} ({self.session_length} minutes)"