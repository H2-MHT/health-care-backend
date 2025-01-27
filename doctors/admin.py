from django.contrib import admin
from .models import Doctor, DoctorNotes, Referral, Invitation, AppointmentManagement, ConsultationSettings
# Register your models here.
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['id','user',]
    
admin.site.register(Doctor, DoctorAdmin)
admin.site.register(DoctorNotes)
admin.site.register(Referral)
admin.site.register(Invitation)
admin.site.register(AppointmentManagement)
admin.site.register(ConsultationSettings)