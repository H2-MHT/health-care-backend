from django.contrib import admin
from .models import User

# Register your models here.


class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email','role', 'is_staff', 'is_superuser')
admin.site.register(User, UserAdmin)