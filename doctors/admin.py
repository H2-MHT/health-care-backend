from django.contrib import admin
from .models import(
    Doctor,
    # DoctorNotes,
    Referral,
    UserPreference,
    Invitation,
    ReschedulePolicy,
    AppointmentManagement,
    ConsultationSessionAndFee,
    NoShowPolicy,
    CommunicationPreferences,
    Membership,
    BookedAppointment,
    Slot,
    DoctorSchedule,
)
# Register your models here.
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['id','user',]

class ReferralAdmin(admin.ModelAdmin):
    list_display = ['id','personal_code','referral_points', 'invited_users_count']


class TwoFactorMethodAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'is_active']
    
admin.site.register(Doctor, DoctorAdmin)
# admin.site.register(DoctorNotes)
admin.site.register(Referral, ReferralAdmin)
admin.site.register(Invitation)
admin.site.register(AppointmentManagement)
admin.site.register(ConsultationSessionAndFee)
admin.site.register(ReschedulePolicy)
admin.site.register(UserPreference)
admin.site.register(NoShowPolicy)
admin.site.register(CommunicationPreferences)
admin.site.register(Membership)
admin.site.register(BookedAppointment)
admin.site.register(Slot)
admin.site.register(DoctorSchedule)
