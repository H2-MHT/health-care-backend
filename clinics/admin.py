from django.contrib import admin
from .models import *
# Register your models here.
admin.site.register(Clinic)
admin.site.register(ServicesProvided)
admin.site.register(Language)
admin.site.register(ClinicReview)
admin.site.register(ClinicReviewReply)