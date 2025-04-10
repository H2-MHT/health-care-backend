import os
from django.db import models
from django.forms import ValidationError
from  users.models import User
import random
import string
from payments.models import Payment
from patients.models import Patient
from appointments.models import Appointment
from decimal import Decimal
# Create your models here.


class Doctor(models.Model):
    user = models.OneToOneField("users.User", on_delete=models.CASCADE)
    specialty = models.CharField(max_length=255)
    qualifications = models.TextField(null=True, blank=True)
    experience_years = models.PositiveIntegerField(null=True, blank=True)
    available_dates = models.JSONField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    planned_hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    urgent_hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def update_hourly_rates(self):
        """hourly rates based on consultation settings"""
        consultation = ConsultationSessionAndFee.objects.filter(doctor=self).first()
        if consultation:
            planned_hourly = 0
            urgent_hourly = 0

            if consultation.planned_fees and consultation.planned_session_length:
                planned_hourly = (consultation.planned_fees / consultation.planned_session_length) * 60

            if consultation.urgent_fees and consultation.urgent_session_length:
                urgent_hourly = (consultation.urgent_fees / consultation.urgent_session_length) * 60

            self.planned_hourly_rate = round(planned_hourly, 2)
            self.urgent_hourly_rate = round(urgent_hourly, 2)
            self.save()

    def __str__(self):
        return self.user.get_full_name()

# class DoctorNotes(models.Model):
#     doctor = models.ForeignKey(
#         "Doctor", 
#         on_delete=models.CASCADE, 
#     )
#     title = models.CharField(max_length=255, help_text="Title of the doctor's note")
#     note = models.TextField(help_text="Detailed note provided by the doctor")
#     created_at = models.DateTimeField(auto_now_add=True, help_text="Date and time when the note was created")
#     updated_at = models.DateTimeField(auto_now=True, help_text="Date and time when the note was last updated")



def generate_referral_code():
    """Generate a unique 7-digit referral code."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))

class Referral(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="referral")
    personal_code = models.CharField(max_length=7, unique=True, default=generate_referral_code)
    referral_points = models.PositiveIntegerField(default=0)
    invited_users_count = models.PositiveIntegerField(default=0)
    
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
    
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="appointment_preferences", null=True)
    appointment_type = models.CharField(max_length=50, choices=APPOINTMENT_TYPE_CHOICES)
    days = models.CharField(max_length=100, help_text="Comma-separated days, e.g., Mon,Fri,Sat")
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    def __str__(self):
        return f"{self.appointment_type} ({self.days} {self.start_time}-{self.end_time})"

# class Slot(models.Model):
#     doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, null=True)
#     day = models.CharField(max_length=10)
#     start_time = models.TimeField()
#     end_time = models.TimeField()
#     slot_type = models.CharField(max_length=10, choices=[("Planned", "Planned"), ("Urgent", "Urgent")], blank=True)
#     is_booked = models.BooleanField(default=False)

    # def __str__(self):
    #     return f"{self.doctor} - {self.day} {self.start_time}-{self.end_time} ({self.slot_type})"
    
class DoctorSchedule(models.Model):
    # doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)  # Ensures only 1 record per doctor
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # Ensures only 1 record per doctor
    schedule = models.JSONField(default=dict)  # Stores full schedule as JSON

class PatientBookAppointment(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)  # Ensures only 1 record per doctor
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, null=True, blank=True)  # Add patient field
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, null=True, blank=True)
    schedule = models.JSONField(default=dict)  # Stores appointments as JSON { "YYYY-MM-DD": { "slots": [...] } }
    date = models.DateField(auto_now_add=True)  # Date when the appointment was recorded
    status = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True)
    APPOINTMENT_TYPES = [
        ("Planned", "Planned"),
        ("Urgent", "Urgent"),
    ]
    appointment_type = models.CharField(max_length=20, choices=APPOINTMENT_TYPES)
    
    
class BookedAppointment(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Confirmed", "Confirmed"),
        ("Rescheduled", "Rescheduled"),
        ("Cancelled", "Cancelled"),
        ("Completed", "Completed"),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Completed", "Completed"),
        ("Refunded", "Refunded"),
        ("Failed", "Failed"),
        ("Cancelled", "Cancelled"),
        ]

    # doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="doctor_appointments")
    # patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="patient_appointments")
    doctor = models.IntegerField(help_text="Consider patient as User id")
    patient = models.IntegerField(help_text="Consider patient as User id")
    appointment_type = models.CharField(max_length=50, choices=[('Planned', 'Planned consultation'), ('Urgent', 'Urgent call')])
    slot = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2,null=True, default=Decimal('0.00'))
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default="Pending")
    stripe_session_id = models.CharField(max_length=255, blank=True, null=True)
    rescheduled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="rescheduled_appointments")
    created_at = models.DateTimeField(auto_now_add=True)

    # appointment_status = models.ForeignKey(Slot, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"Appointment with Dr. {self.doctor} at {self.slot}"

    
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
    
    
class ConsultationSessionAndFee(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    planned_session = models.CharField(max_length=50, null=True, blank=True)
    urgent_session = models.CharField(max_length=50, null=True, blank=True)
    planned_session_length = models.IntegerField(choices=[(15, '15 minutes'), (30, '30 minutes')], null=True, blank=True)
    urgent_session_length = models.IntegerField(choices=[(15, '15 minutes'), (30, '30 minutes')], null=True, blank=True)
    buffer_time = models.DurationField(blank=True, null=True)
    planned_fees = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    urgent_fees = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    def save(self, *args, **kwargs):
        """Automatically update doctor's hourly rates when saving consultation fees"""
        super().save(*args, **kwargs)
        if self.doctor:
            planned_hourly = 0
            urgent_hourly = 0

            if self.planned_fees and self.planned_session_length:
                planned_hourly = (self.planned_fees / self.planned_session_length) * 60

            if self.urgent_fees and self.urgent_session_length:
                urgent_hourly = (self.urgent_fees / self.urgent_session_length) * 60

            self.doctor.planned_hourly_rate = round(planned_hourly, 2)
            self.doctor.urgent_hourly_rate = round(urgent_hourly, 2)
            self.doctor.save()

    def __str__(self):
        return f"Consultation settings for {self.doctor}"

    
class UserPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    timezone = models.CharField(max_length=50, default='UTC')
    language = models.CharField(max_length=10, default='en')
    use_system_timezone = models.BooleanField(default=True)
    use_system_language = models.BooleanField(default=True)
    
    
    
class ReschedulePolicy(models.Model):
        
    DAYS_CHOICES = [
        ('Mon', 'Monday'),
        ('Tue', 'Tuesday'),
        ('Wed', 'Wednesday'),
        ('Thu', 'Thursday'),
        ('Fri', 'Friday'),
        ('Sat', 'Saturday'),
        ('Sun', 'Sunday'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    allow_reschedule = models.BooleanField(default=False)
    max_reschedules = models.PositiveIntegerField(null=True, blank=True)
    reschedule_days = models.CharField(max_length=50, choices=DAYS_CHOICES)
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
    
    
    
class Membership(models.Model):
    MEMBERSHIP_CHOICES = [
        ('basic', 'Basic'),
        ('premium', 'Premium'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    membership_type = models.CharField(max_length=10, choices=MEMBERSHIP_CHOICES)

    def __str__(self):
        return f"{self.user.username} - {self.membership_type}"
    

class LicenceCertificate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="attachment")
    name = models.CharField(max_length=250, default="Untitled")
    description = models.TextField(null=True, blank=True)
    attachment = models.FileField(upload_to="Licence_Certificate/attachment/", blank=True, null=True)
    date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=[("Pending", "Pending"), ("Approved", "Approved"), ("Rejected", "Rejected")], default="Pending", null=True)
    rejection_reason = models.TextField(null=True, blank=True)
    is_delete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.date}"
    
    
def validate_video_extension(value):
    """Validate that uploaded file has a video extension."""
    ext = os.path.splitext(value.name)[1].lower()
    allowed_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv','.jpg', '.jpeg', '.png', '.webp']
    if ext not in allowed_extensions:
        raise ValidationError("Only accepting this types of files .mp4, .avi, .mov, .mkv, .flv, .wmv, .jpg, .jpeg, .png, .webp")

def validate_video_size(value):
    """Validate that uploaded video size is less than 30MB."""
    max_size = 30 * 1024 * 1024
    if value.size > max_size:
        raise ValidationError("Size too large. Maximum allowed size is 30MB.")

class MediaDigest(models.Model):
    user_doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="media_digest_documents")
    title = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(default="")
    attachment_file = models.FileField(
        upload_to="media_digest_documents/",
        validators=[validate_video_extension, validate_video_size]
    )

    def __str__(self):
        return self.title if self.title else "Untitled Media"


class DoctorWallet(models.Model):
    doctor = models.ForeignKey(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.0'))
    
