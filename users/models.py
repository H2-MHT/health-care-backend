import pycountry
import uuid as uuid_lib
from django.db import transaction
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from clinics.models import Language
import random
from django.utils.timezone import now
from datetime import datetime
from django.utils import timezone 

class CustomUserManager(BaseUserManager):
    """
    Custom user manager where email is the unique identifier.
    """

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")

        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and return a superuser with elevated permissions.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "SuperAdmin")  # Default role for superusers

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


def validate_terms(value):
    if not value:
        raise ValidationError("You must agree to the terms and conditions.")


class TwoFactorMethod(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
    
    
class User(AbstractUser):
    ROLE_CHOICES = [
        ("Patient", "Patient"),
        ("Doctor", "Doctor"),
        ("Clinic", "Clinic"),
        ("Admin", "Admin"),
        ("SuperAdmin", "Super Admin"),
    ]
    GENDER_CHOICES = [
        ("Male", "Male"),
        ("Female", "Female"),
        ("Other", "Other"),
    ]

    # Authentication fields
    username = None
    uid = models.CharField(max_length=30, editable=False, blank=True, null=True, unique=True)
    uuid = models.UUIDField(default=uuid_lib.uuid4, editable=False, unique=True)
    email = models.EmailField(unique=True, null=False)
    password = models.CharField(max_length=128, null=False)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    # Personal Information
    first_name = models.CharField(max_length=150, null=False, blank=False)
    last_name = models.CharField(max_length=150, blank=True, default="")
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10, choices=GENDER_CHOICES, blank=True, default="Other"
    )
    phone_number = models.CharField(max_length=20, blank=True, default="")
    profile_picture = models.ImageField(
        upload_to="profile_pictures/", null=True, blank=True
    )
    bio = models.TextField(blank=True, default="")
    otp = models.CharField(max_length=6, blank=True, default="")
    temp_password = models.CharField(max_length=128, blank=True, default="")

    # Address Information
    country = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=255, blank=True, default="")
    currency=models.CharField(max_length=10, default="USD", help_text="Currency code")
    residence = models.CharField(max_length=255, blank=True, default="")

    # Professional Information
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default="Patient", null=False
    )
    is_doctor_switched = models.BooleanField(default=False)
    languages = models.ManyToManyField(Language, blank=True)
    work_place = models.ForeignKey("clinics.Clinic", on_delete=models.SET_NULL, null=True, blank=True, related_name="clinic_work")
    expertise = models.TextField(blank=True, default="")
    professional_stat = models.TextField(blank=True, default="")
    working_time = models.CharField(max_length=255, blank=True, default="")
    
    # Agreement
    terms_and_condition = models.BooleanField(
        validators=[validate_terms], default=False
    )
    code_of_conduct = models.BooleanField(default=False, null=True, blank=True)
    acknowledge = models.BooleanField(default=False, null=True, blank=True)
    medical_disclaimer = models.BooleanField(default=False, null=True, blank=True)
    
    # Two-Factor Authentication (Multiple Methods)
    two_factor_methods = models.ManyToManyField("TwoFactorMethod", blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)
    last_activity = models.DateTimeField(blank=True, null=True)
    is_online = models.BooleanField(default=False)
    rating = models.PositiveSmallIntegerField(null=True, default=0)
    reviews = models.PositiveBigIntegerField(null=True, default=0)
    
    # firebase device token
    device_token = models.TextField(unique=True, blank=True, null=True)
    # agora channel name
    agora_channel_name = models.CharField(max_length=250, null=True, blank=True)
    # Agora receiver user id
    agoraReceiverUserUid = models.IntegerField(null=True, blank=True)
    
    # Set email as the unique identifier
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    def generate_otp(self):
        """Generate and save a 6-digit OTP for the user."""
        self.otp = str(random.randint(100000, 999999))
        self.save()
        return self.otp
    
    def update_activity(self):
        self.last_activity = now()
        self.save(update_fields=['last_activity'])

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()    
    
    @staticmethod
    def get_country_code(country_name: str) -> str:
        try:
            country = pycountry.countries.search_fuzzy(country_name)[0]
            return country.alpha_2
        except (LookupError, AttributeError, IndexError):
            return 'XX'  # Default fallback if country not found

    @staticmethod
    @transaction.atomic
    def generate_uid(prefix: str, country_code: str) -> str:
        today = datetime.today().strftime('%d%m%Y')

        # Lock the sequence row to prevent race condition
        sequence, _ = UIDSequence.objects.select_for_update().get_or_create(
            prefix=prefix,
            date=today,
            defaults={'counter': 0}
        )

        sequence.counter += 1
        sequence.save()

        return f"{prefix}{today}{country_code}{sequence.counter:06d}"

    def save(self, *args, **kwargs):
        if not self.uid:
            prefix = 'U' if self.role == 'Patient' else 'D' if self.role == 'Doctor' else 'X'
            country_code = self.get_country_code(self.country or "")
            self.uid = self.generate_uid(prefix, country_code)
        super().save(*args, **kwargs)


class UIDSequence(models.Model):
    prefix = models.CharField(max_length=10)
    date = models.CharField(max_length=8)
    counter = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('prefix', 'date')
        
        
def user_fileq(instance, filename):
    return "{0}-{1}".format(instance.type, filename)


class UserFile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="files")
    file = models.FileField(upload_to="licenses_certificates/", null=True, blank=True)
    type = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=[("Certificate", "Certificate"), ("Media", "Media")],
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.type}"

class Skill(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
    

class Education(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="educations")
    school = models.CharField(max_length=255, blank=True, null=True)
    degree = models.CharField(max_length=100, blank=True, null=True)
    field_of_study = models.CharField(max_length=100, blank=True, null=True)
    start_month_year = models.CharField(max_length=100, blank=True, default="")
    end_month_year = models.CharField(max_length=100, blank=True, default="")
    grade = models.CharField(max_length=50, blank=True, null=True)
    activities_and_societies = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    skills = models.ManyToManyField(Skill, blank=True, default="")

    def __str__(self):
        return f"{self.school} - {self.degree or 'Education'}"


class Media(models.Model):
    file = models.FileField(upload_to="education_media/", blank=True, null=True)
    education = models.ForeignKey(Education, on_delete=models.CASCADE, default="", blank=True, null=True, related_name="media")
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.file.name if self.file else "Media"

class Notes(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, help_text="Title of the doctor's note")
    note = models.TextField(help_text="Detailed note provided by the doctor")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Date and time when the note was created")
    updated_at = models.DateTimeField(auto_now=True, help_text="Date and time when the note was last updated")
    

class DeviceAccess(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_accesses')
    location_name = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField()
    logged_in_time = models.TimeField()
    platform = models.CharField(max_length=100)
    active_sessions = models.BooleanField(null=True, blank=True, default=None)

class AppLanguage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='app_languages')
    language_name = models.CharField(max_length=100, blank=True, null=True, help_text="Language name", default="English")
    code = models.CharField(max_length=10, blank=True, null=True, help_text="Language code", default="en")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Application Language"
        verbose_name_plural = "Application Languages"

    def __str__(self):
        return f"{self.user.email} - {self.language_name}"
    
# help and support 

class Ticket(models.Model):
    STATUS_CHOICES = (
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ticket_id = models.CharField(max_length=20, unique=True, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    attachment = models.FileField(upload_to='support_attachments/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    admin_comment = models.TextField(blank=True, null=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.ticket_id:
            role = getattr(self.user, 'role', '').lower()
            prefix = {
                'patient': 'PUID',
                'doctor': 'DUID',
                'clinic': 'CUID',
            }.get(role, 'UID')
            random_number = random.randint(100000, 999999)
            self.ticket_id = f"{prefix}{random_number}"
            while Ticket.objects.filter(ticket_id=self.ticket_id).exists():
                random_number = random.randint(100000, 999999)
                self.ticket_id = f"{prefix}{random_number}"
        super().save(*args, **kwargs)

