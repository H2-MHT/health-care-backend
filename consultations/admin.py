from django.contrib import admin
from .models import ConsultationSummary, Prescription, ConsultationReport
# Register your models here.

admin.site.register(ConsultationSummary)
admin.site.register(Prescription)
admin.site.register(ConsultationReport)