from django.db import models
from  users.models import User
import random
import string
from django.contrib.auth import get_user_model

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
        "Doctor", 
        on_delete=models.CASCADE, 
    )
    title = models.CharField(max_length=255, help_text="Title of the doctor's note")
    note = models.TextField(help_text="Detailed note provided by the doctor")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Date and time when the note was created")
    updated_at = models.DateTimeField(auto_now=True, help_text="Date and time when the note was last updated")



def generate_referral_code():
    """Generate a unique 7-digit referral code."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))

class Referral(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="referral")
    personal_code = models.CharField(max_length=7, unique=True, default=generate_referral_code)
    invited_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="invited_users")
    referral_points = models.PositiveIntegerField(default=0)
    invited_users_count = models.PositiveIntegerField(default=0)
    referral_use = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.first_name} - {self.personal_code}"

    def get_registration_link(self):
        """Generate a registration link that includes the personal referral code."""
        return f"http://localhost:8000/register?referral_code={self.personal_code}"



class Invitation(models.Model):
    invited_by = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name='invitations')
    invited_user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='invited_as')
    first_appointment = models.BooleanField(default=False)
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
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    planned_session = models.CharField(max_length=50, null=True, blank=True)
    urgent_session = models.CharField(max_length=50, null=True, blank=True)
    planned_session_length = models.IntegerField(choices=[(15, '15 minutes'), (30, '30 minutes')], null=True, blank=True)
    urgent_session_length = models.IntegerField(choices=[(15, '15 minutes'), (30, '30 minutes')], null=True, blank=True)
    buffer_time = models.DurationField(blank=True, null=True)
    planned_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    urgent_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def __str__(self):
        return f"Consultation settings for {self.doctor}"
    
    
    
class UserPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    timezone = models.CharField(max_length=50, default='UTC')
    language = models.CharField(max_length=10, default='en')
    use_system_timezone = models.BooleanField(default=True)
    use_system_language = models.BooleanField(default=True)
    
    
class ReschedulePolicy(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    allow_reschedule = models.BooleanField(default=False)
    max_reschedules = models.PositiveIntegerField(null=True, blank=True)
    reschedule_days = models.PositiveIntegerField(null=True, blank=True)
    reschedule_time_range = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"Reschedule Policy - Allowed: {self.allow_reschedule}"
    
    
class CancellationPolicy(models.Model):
    doctor = models.OneToOneField(User, on_delete=models.CASCADE)
    no_fee_cancellation_period = models.TimeField()
    fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    chargeable_cancellation_period = models.TimeField()

    def __str__(self):
        return f"{self.doctor.email} - No Fee: {self.no_fee_cancellation_period}, {self.fee_percentage}% Fee"
    
    
class NoShowPolicy(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="no_show_policies")
    planned = models.CharField(max_length=50, blank=True, null=True)
    urgent = models.CharField(max_length=50, blank=True, null=True)
    waiting_time_planned = models.CharField(max_length=20, blank=True, null=True, help_text="Waiting time for planned cases (e.g., 15 minutes)")
    waiting_time_urgent = models.CharField(max_length=20, blank=True, null=True, help_text="Waiting time for urgent cases (e.g., 30 minutes)")

    def __str__(self):
        return f"User: {self.user.username}, Planned: {self.waiting_time_planned or 'N/A'}, Urgent: {self.waiting_time_urgent or 'N/A'}"
    
        

class CommunicationPreferences(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="communication_preferences")

    # Notification Preferences
    appointment_reminders = models.BooleanField(default=True)
    patient_messages = models.BooleanField(default=True)
    other_important_updates = models.BooleanField(default=True)

    # Channel Preferences
    email = models.BooleanField(default=True)
    whatsapp = models.BooleanField(default=True)
    platform_messenger = models.BooleanField(default=True)

    def __str__(self):
        return f"Communication Preferences for {self.user.username}"
    
    

class TwoFactorAuthMethod(models.Model):
    METHOD_CHOICES = [
        ('email', 'E-mail verification'),
        ('security_question', 'Security question'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    method = models.CharField(max_length=50, choices=METHOD_CHOICES)

    def __str__(self):
        return f"{self.user.username} - {self.get_method_display()}"