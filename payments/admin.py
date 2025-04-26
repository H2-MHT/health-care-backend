from django.contrib import admin
from .models import Payment, AccountDetail, Transaction
# Register your models here.


class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_appointment', 'amount', 'total_amount', 'method', 'status', 'timestamp')
    search_fields = ('appointment__id', 'status', 'amount')
    list_filter = ('status', 'method')

    def get_appointment(self, obj):
        return obj.appointment.id if obj.appointment else "No Appointment"
    get_appointment.admin_order_field = 'appointment'
    get_appointment.short_description = 'Appointment ID'
    
        
class AccountDetailAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'account_number', 'ifsc_code')

admin.site.register(Transaction)
admin.site.register(AccountDetail, AccountDetailAdmin)    
admin.site.register(Payment, PaymentAdmin)
