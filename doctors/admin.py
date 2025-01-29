from django.contrib import admin
from .models import Doctor, DoctorNotes, Referral, Invitation, AppointmentManagement
# Register your models here.
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['id','user',]

class ReferralAdmin(admin.ModelAdmin):
    list_display = ['id','personal_code','invited_by','referral_points', 'invited_users_count']
    
admin.site.register(Doctor, DoctorAdmin)
admin.site.register(DoctorNotes)
admin.site.register(Referral, ReferralAdmin)
admin.site.register(Invitation)
admin.site.register(AppointmentManagement)