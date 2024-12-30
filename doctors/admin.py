from django.contrib import admin
from .models import Doctor, DoctorNotes
# Register your models here.
admin.site.register(Doctor)
admin.site.register(DoctorNotes)