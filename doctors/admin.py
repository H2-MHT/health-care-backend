from django.contrib import admin
from .models import Doctor, DoctorNotes
# Register your models here.
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['id','user',]
admin.site.register(Doctor, DoctorAdmin)
admin.site.register(DoctorNotes)