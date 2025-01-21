from django.contrib import admin
from .models import User, Education

# Register your models here.


class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email','role', 'is_staff', 'is_superuser')
    
class EducationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'degree', 'start_date', 'end_date', 'grade')

admin.site.register(Education, EducationAdmin)
admin.site.register(User, UserAdmin)