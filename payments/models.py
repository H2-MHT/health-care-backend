from django.db import models
from users.models import User
# Create your models here.


class Payment(models.Model):
    appointment = models.OneToOneField(
        "appointments.Appointment", on_delete=models.CASCADE
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    method = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20,
        choices=[("Pending", "Pending"), ("Success", "Success"), ("Failed", "Failed")],
        default="Pending"
    )
    payment_notes = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    

class AccountDetail(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    account_number = models.CharField(max_length=30)
    confirm_account_number = models.CharField(max_length=30)
    full_name = models.CharField(max_length=100)
    ifsc_code = models.CharField(max_length=20)


    def __str__(self):
        return self.account_number + self.full_name
    
    class Meta:
        verbose_name = 'Account Detail'
        verbose_name_plural = 'Account Details'
        
        
class Transaction(models.Model):
    account = models.ForeignKey(AccountDetail, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=50, choices=[("Deposit", "Deposit"), ("Withdrawal", "Withdrawal")])
    status = models.CharField(max_length=20, choices=[("pending", "Pending"), ("success", "Success"), ("failed", "Failed")], default="Pending", null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    rejection_reason = models.TextField(null=True, blank=True)
    
    
    class Meta:
        verbose_name = 'Transection'
        verbose_name_plural = 'Transections'