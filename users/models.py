from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models
from clinics.models import Language
import random
from django.utils.timezone import now


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


class User(AbstractUser):
    ROLE_CHOICES = [
        ("Patient", "Patient"),
        ("Doctor", "Doctor"),
        ("Clinic", "Clinic"),
        ("SuperAdmin", "Super Admin"),
    ]
    GENDER_CHOICES = [
        ("Male", "Male"),
        ("Female", "Female"),
        ("Other", "Other"),
    ]

    # Authentication fields
    username = None
    email = models.EmailField(unique=True, null=False)
    password = models.CharField(max_length=128, null=False)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    # Personal Information
    first_name = models.CharField(max_length=150, null=False, blank=False)
    last_name = models.CharField(max_length=150, null=True, blank=True)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10, choices=GENDER_CHOICES, null=True, blank=True
    )
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    profile_picture = models.ImageField(
        upload_to="profile_pictures/", null=True, blank=True
    )
    bio = models.TextField(null=True, blank=True)
    otp = models.CharField(max_length=6, null=True, blank=True)
    temp_password = models.CharField(max_length=128, null=True, blank=True)

    # Address Information
    country = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    residence = models.CharField(max_length=255, null=True, blank=True)

    # Professional Information
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default="Patient", null=False
    )
    languages = models.ManyToManyField(Language)
    work_place = models.ForeignKey("clinics.Clinic", on_delete=models.SET_NULL, null=True, blank=True, related_name="clinic_work")
    expertise = models.TextField(null=True, blank=True)
    professional_stat = models.TextField(null=True, blank=True)
    working_time = models.CharField(max_length=255, null=True, blank=True)
    # Agreement
    terms_and_condition = models.BooleanField(
        validators=[validate_terms], default=False
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)
    last_activity = models.DateTimeField(blank=True, null=True)

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


class Education(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="educations")
    school = models.CharField(max_length=255, blank=True, null=True)
    degree = models.CharField(max_length=100, blank=True, null=True)
    field_of_study = models.CharField(max_length=100, blank=True, null=True)
    start_month = models.IntegerField(null=True, blank=True)
    start_year = models.IntegerField(null=True, blank=True)
    end_month = models.IntegerField(null=True, blank=True)
    end_year = models.IntegerField(null=True, blank=True)
    grade = models.CharField(max_length=50, blank=True, null=True)
    activities_and_societies = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    # Assuming skills are a ManyToMany relationship
    skills = models.JSONField(default=list, blank=True)


    # For media, you can either store files or URLs
    media = models.ImageField(upload_to='education_media/', blank=True, null=True)

    def __str__(self):
        return f"{self.school} - {self.degree or 'Education'}"


class Skill(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Media(models.Model):
    file = models.FileField(upload_to="education_media/", blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.file.name if self.file else "Media"
