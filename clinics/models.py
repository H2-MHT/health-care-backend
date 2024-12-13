from django.db import models

# Create your models here.


class Clinic(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    phone_number = models.CharField(max_length=20)
    password = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    website = models.URLField(null=True, blank=True)
    services_provided = models.TextField(null=True, blank=True)
    licenses_certificate = models.TextField(null=True, blank=True)
    languages = models.TextField(null=True, blank=True)
    working_time = models.TextField(null=True, blank=True)
    administrator_name = models.CharField(max_length=255, null=True, blank=True)
    administrator_email = models.EmailField(null=True, blank=True)
