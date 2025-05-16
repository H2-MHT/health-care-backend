from rest_framework import serializers
from .models import AccountDetail, Transaction
from collections import OrderedDict
from doctors.models import DoctorWallet
from decimal import Decimal

class AccountDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountDetail
        fields = ['account_number','confirm_account_number','full_name', 'ifsc_code']
          
class TransactionSerializer(serializers.ModelSerializer):
    # status = serializers.SerializerMethodField()
    currency = serializers.CharField(source='account.user.currency')
    transaction_type = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    bank_name = serializers.CharField(source='account.bank_name')
    class Meta:
        model = Transaction
        fields = ['id', 'account', 'amount', 'bank_name', 'transaction_type', 'currency', 'balance', 'reference', 'stripe_payment_link', 'stripe_payment_link_id', 'status', 'rejection_reason', 'timestamp']

    # def get_status(self, obj):
    #     return obj.account.get_status_display()

    def get_transaction_type(self, obj):
        return obj.get_transaction_type_display()
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        doctor_name = instance.account.full_name
        transaction_type = instance.get_transaction_type_display()

        ordered_data = OrderedDict([
            ('account', data['account']),
            ('id', data['id']),
            ('Doctor_name', doctor_name),
            ('transaction_type', transaction_type),
        ])

        for key, value in data.items():
            if key not in ordered_data:
                ordered_data[key] = value

        return ordered_data
    
    
    def get_balance(self, obj):
        try:
            wallet = obj.account.user.doctorwallet_set.first()
            if wallet:
                return wallet.balance
            return Decimal('0.0')
        except Exception as e:
            return Decimal('0.0')