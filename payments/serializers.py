from rest_framework import serializers
from .models import AccountDetail, Transaction
from collections import OrderedDict


class AccountDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountDetail
        fields = ['amount', 'account_number', 'full_name', 'ifsc_code', 'status']
          
class TransactionSerializer(serializers.ModelSerializer):
    # status = serializers.SerializerMethodField()
    transaction_type = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = ['account', 'amount', 'transaction_type', 'status', 'rejection_reason']

    # def get_status(self, obj):
    #     return obj.account.get_status_display()

    def get_transaction_type(self, obj):
        return obj.get_transaction_type_display()
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        doctor_name = instance.account.full_name
        ordered_data = OrderedDict()
        ordered_data['account'] = data['account']
        ordered_data['Doctor_name'] = doctor_name  
        ordered_data.update(data)
        
        return ordered_data