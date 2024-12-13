from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.


class User(AbstractUser):
    ROLE_CHOICES = [
        ("Patient", "Patient"),
        ("Doctor", "Doctor"),
        ("SuperAdmin", "Super Admin"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    dob = models.DateField()
    gender = models.CharField(
        max_length=10,
        choices=[("Male", "Male"), ("Female", "Female"), ("Other", "Other")],
    )
    country = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    bio = models.TextField(null=True, blank=True)
    otp = models.CharField(max_length=6, null=True, blank=True)
    languages = models.TextField(null=True, blank=True)
    profile_picture = models.ImageField(
        upload_to="profile_pictures/", null=True, blank=True
    )
    phone_number = models.CharField(max_length=20)

    def __str__(self):
        return self.username
