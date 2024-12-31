from django.contrib import admin
from .models import Appointment


# Register your models here.

class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient', 'doctor', 'clinic', 'date_time', 'status')
    
admin.site.register(Appointment, AppointmentAdmin)