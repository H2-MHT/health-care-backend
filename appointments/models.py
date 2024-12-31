from django.db import models

# Create your models here.


class Appointment(models.Model):
    patient = models.ForeignKey("patients.Patient", on_delete=models.CASCADE)
    doctor = models.ForeignKey("doctors.Doctor", on_delete=models.CASCADE)
    clinic = models.ForeignKey("clinics.Clinic", on_delete=models.CASCADE)
    date_time = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=[
            ("Pending", "Pending"),
            ("Confirmed", "Confirmed"),
            ("Completed", "Completed"),
            ("Cancelled", "Cancelled"),
            ("Archived", "Archived"),
        ],
    )
    records = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"Appointment with {self.doctor} on {self.date_time}"
    
    
    def get_status(self):
        return self.status
    
