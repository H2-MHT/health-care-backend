from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.


class User(AbstractUser):
    ROLE_CHOICES = [
        ('Patient', 'Patient'),
        ('Doctor', 'Doctor'),
        ('SuperAdmin', 'Super Admin'),
    ]
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ]

    # Custom fields based on the uploaded document
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, null=True, blank=True)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    country = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    otp = models.CharField(max_length=6, null=True, blank=True)
    languages = models.TextField(null=True, blank=True)
    work_place = models.TextField(null=True, blank=True)
    expertise = models.TextField(null=True, blank=True)
    professional_stat = models.TextField(null=True, blank=True)
    residence = models.TextField(null=True, blank=True)
    working_time = models.TextField(null=True, blank=True)
    licenses_certificate = models.TextField(null=True, blank=True)
    media_digest = models.TextField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return self.username
