from django.contrib import admin
from .models import (
    User,
    Education,
    Skill,
    Media,
    TwoFactorMethod,
    DeviceAccess,
    AppLanguage,
    Ticket,
)

# Register your models here.


class UserAdmin(admin.ModelAdmin):
    list_display = ('uid', 'id', 'username', 'email','role', 'is_staff', 'is_superuser', 'is_active', 'is_doctor_switched')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.set_password(form.cleaned_data['password'])
            obj.save()
        super().save_model(request, obj, form, change)

    
class EducationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'degree', 'start_month_year', 'end_month_year', 'grade')

class TwoFactorMethodAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_active')
    verbose_name = "Two-Factor Method"
    verbose_name_plural = "Two-Factor Methods"

class AppLanguageAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'language_name', 'code', 'created_at', 'updated_at')
    verbose_name = "Application Language"
    verbose_name_plural = "Application Languages"
    
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'ticket_id', 'title', 'description', 'attachment', 'status', 'created_at', 'updated_at')
    
admin.site.register(Ticket, TicketAdmin)
admin.site.register(Media)
admin.site.register(Skill)
admin.site.register(Education, EducationAdmin)
admin.site.register(User, UserAdmin)

admin.site.register(TwoFactorMethod, TwoFactorMethodAdmin)

admin.site.register(DeviceAccess)
admin.site.register(AppLanguage, AppLanguageAdmin)