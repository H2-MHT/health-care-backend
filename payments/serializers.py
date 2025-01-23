from rest_framework import serializers
from .models import AccountDetail, Transaction

class AccountDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountDetail
        fields = ['amount', 'account_number', 'confirm_account_number', 'full_name', 'ifsc_code', 'status']

class TransactionSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    transaction_type = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = ['account', 'amount', 'transaction_type', 'status']

    def get_status(self, obj):
        return obj.account.get_status_display()

    def get_transaction_type(self, obj):
        return obj.get_transaction_type_display()