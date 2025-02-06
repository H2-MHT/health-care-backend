from django.contrib import admin
from .models import Appointment


# Register your models here.

class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_patient_name', 'get_doctor_name', 'get_clinic_name', 'date_time', 'status')

    def get_patient_name(self, obj):
        return obj.patient.user.get_full_name() if obj.patient else "No Patient"
    get_patient_name.short_description = "Patient"

    def get_doctor_name(self, obj):
        return obj.doctor.user.get_full_name() if obj.doctor else "No Doctor"
    get_doctor_name.short_description = "Doctor"

    def get_clinic_name(self, obj):
        return obj.clinic.name if obj.clinic else "No Clinic"
    get_clinic_name.short_description = "Clinic"

admin.site.register(Appointment, AppointmentAdmin)