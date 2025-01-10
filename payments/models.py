from django.db import models

# Create your models here.


class Payment(models.Model):
    appointment = models.OneToOneField(
        "appointments.Appointment", on_delete=models.CASCADE
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    method = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20, choices=[("Paid", "Paid"), ("Pending", "Pending")]
    )
    payment_notes = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)