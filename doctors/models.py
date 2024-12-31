from django.db import models

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
    patient = models.ForeignKey(
        "users.User", 
        on_delete=models.CASCADE, 
        limit_choices_to={'role': 'Patient'}, 
        related_name='notes_as_patient'
    )
    doctor = models.ForeignKey(
        "users.User", 
        on_delete=models.CASCADE, 
        limit_choices_to={'role': 'Doctor'}, 
        related_name='notes_as_doctor'
    )
    title = models.CharField(max_length=255, help_text="Title of the doctor's note")
    note = models.TextField(help_text="Detailed note provided by the doctor")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Date and time when the note was created")
    updated_at = models.DateTimeField(auto_now=True, help_text="Date and time when the note was last updated")

    def __str__(self):
        return f"Note by Dr. {self.doctor.first_name} for {self.patient.first_name}"


    def __str__(self):
        return f"Note by Dr. {self.doctor.first_name} for {self.patient.first_name}"

