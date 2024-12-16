from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError

def validate_terms(value):
    if not value:
        raise ValidationError("You must agree to the terms and conditions.")

class User(AbstractUser):
    ROLE_CHOICES = [
        ("Patient", "Patient"),
        ("Doctor", "Doctor"),
        ("SuperAdmin", "Super Admin"),
    ]
    GENDER_CHOICES = [
        ("Male", "Male"),
        ("Female", "Female"),
        ("Other", "Other"),
    ]

    # Remove 'username' and use 'email' as the unique identifier
    username = None
    first_name = models.CharField(max_length=150, null=False)
    last_name = models.CharField(max_length=150, null=False)
    email = models.EmailField(unique=True, null=False)
    password = models.CharField(max_length=128, null=False)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10, choices=GENDER_CHOICES, null=True, blank=True
    )
    country = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    otp = models.CharField(max_length=6, null=True, blank=True)
    languages = models.TextField(null=True, blank=True)
    work_place = models.CharField(max_length=255, null=True, blank=True)
    expertise = models.TextField(null=True, blank=True)
    professional_stat = models.TextField(null=True, blank=True)
    residence = models.CharField(max_length=255, null=True, blank=True)
    working_time = models.CharField(max_length=255, null=True, blank=True)
    licenses_certificate = models.TextField(null=True, blank=True)
    media_digest = models.TextField(null=True, blank=True)
    profile_picture = models.ImageField(
        upload_to="profile_pictures/", null=True, blank=True
    )
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    terms_and_condition = models.BooleanField(
        validators=[validate_terms], default=False
    )
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, blank=True, null=True)

    # Set email as the unique identifier
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    def save(self, *args, **kwargs):
        """Custom save method with validations."""
        if not self.email:
            raise ValidationError("Email is a required field.")
        if not self.role:
            raise ValidationError("Role is a required field.")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.email
