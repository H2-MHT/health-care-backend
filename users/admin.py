from django.contrib import admin
from .models import User, Education, Skill, Media

# Register your models here.


class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email','role', 'is_staff', 'is_superuser', 'is_active')
    
class EducationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'degree', 'start_month', 'start_year', 'end_month', 'end_year', 'grade')

admin.site.register(Media)
admin.site.register(Skill)
admin.site.register(Education, EducationAdmin)
admin.site.register(User, UserAdmin)