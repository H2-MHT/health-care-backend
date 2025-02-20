from django.contrib import admin
from .models import User, Education, Skill, Media, TwoFactorMethod

# Register your models here.


class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email','role', 'is_staff', 'is_superuser', 'is_active')

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
    
admin.site.register(Media)
admin.site.register(Skill)
admin.site.register(Education, EducationAdmin)
admin.site.register(User, UserAdmin)

admin.site.register(TwoFactorMethod, TwoFactorMethodAdmin)