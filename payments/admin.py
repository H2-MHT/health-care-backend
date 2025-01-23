from django.contrib import admin
from .models import Payment, AccountDetail, Transaction
# Register your models here.


class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'appointment', 'amount', 'total_amount', 'method', 'status', 'timestamp')
    
class AccountDetailAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'account_number', 'ifsc_code')

admin.site.register(Transaction)
admin.site.register(AccountDetail, AccountDetailAdmin)    
admin.site.register(Payment, PaymentAdmin)
