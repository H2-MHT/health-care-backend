from django.contrib import admin
from .models import Payment
# Register your models here.


class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'appointment', 'amount', 'total_amount', 'method', 'status', 'timestamp')
    
admin.site.register(Payment, PaymentAdmin)
