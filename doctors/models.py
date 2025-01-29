from django.db import models
from  users.models import User
import random
import string

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
    """Generate a unique 7-digit referral code."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))

class Referral(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="referral")
    personal_code = models.CharField(max_length=7, unique=True, default=generate_referral_code)
    invited_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="invited_users")
    referral_points = models.PositiveIntegerField(default=0)
    invited_users_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user.first_name} - {self.personal_code}"

    def get_registration_link(self):
        """Generate a registration link that includes the personal referral code."""
        return f"http://localhost:8000/register?referral_code={self.personal_code}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def increase_invite_count(self):
        """Increase the invited users count for the inviter."""
        if self.invited_by:
            inviter_referral = self.invited_by.referral
            print(f"Inviter Referral Found: {inviter_referral.user.first_name}, Current Count: {inviter_referral.invited_users_count}")
            inviter_referral.invited_users_count += 1

            # Debugging: Before saving, print the inviter's referral count
            print(f"Before Saving - Inviter Referral Count: {inviter_referral.invited_users_count}")
            inviter_referral.save()
            # Debugging: After saving, print the updated count
            print(f"After Saving - Inviter Referral Count: {inviter_referral.invited_users_count}")
        else:
            print("No inviter found for this referral.")  # Debugging: Check if there's an inviter



class Invitation(models.Model):
    invited_by = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name='invitations')
    invitation_code = models.CharField(max_length=7)  # Personal code of the inviter
    invited_user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='invited_as')
    is_used = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Invitation by {self.invited_by.user.first_name}"

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