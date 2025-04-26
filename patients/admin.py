from django.contrib import admin
from .models import *
# Register your models here.

admin.site.register(Patient)
admin.site.register(MedicalHistory)
admin.site.register(AllergyDocument)
admin.site.register(Favourite)
admin.site.register(FamilyMember)
admin.site.register(Reminder)