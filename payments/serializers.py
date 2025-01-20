from rest_framework import serializers
from .models import AccountDetail

class AccountDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountDetail
        fields = ['account_number', 'confirm_account_number', 'full_name', 'ifsc_code']
