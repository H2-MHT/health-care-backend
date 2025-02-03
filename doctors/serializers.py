from rest_framework import serializers
from .models import DoctorNotes
from .models import (
    Referral, Invitation,
    AppointmentManagement,
    ConsultationSettings,
    UserPreference,
    ReschedulePolicy,
    CancellationPolicy,
    NoShowPolicy,
    CommunicationPreferences,
    TwoFactorAuthMethod,
)
from datetime import datetime

class DoctorNotesSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorNotes
        fields = ['id', 'title', 'note', 'created_at']
        read_only_fields = ['id', 'created_at', 'doctor']

    def create(self, validated_data):
        # Automatically set the doctor to the logged-in user
        request = self.context.get('request')
        validated_data['doctor'] = request.user
        return super().create(validated_data)
    
    
class ReferralSerializer(serializers.ModelSerializer):
    registration_link = serializers.SerializerMethodField()

    class Meta:
        model = Referral
        fields = ['personal_code', 'referral_points', 'invited_users_count', 'registration_link']

    def get_registration_link(self, obj):
        return obj.get_registration_link()
    
    
class InvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invitation
        fields = ['invited_by', 'invitation_code', 'invited_user_email', 'redeemed']

    def create(self, validated_data):
        """Create an invitation and associate the inviter."""
        invitation = Invitation.objects.create(**validated_data)
        return invitation

class AppointmentManagementSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentManagement
        fields = ['id', 'user', 'appointment_type', 'days', 'start_time', 'end_time']
        read_only_fields = ['user']
        
        
class ConsultationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultationSettings
        fields = '__all__'
        extra_kwargs = {
            'doctor': {'required': False},
            'planned_session': {'required': False},
            'urgent_session': {'required': False},
            'planned_session_length': {'required': False},
            'urgent_session_length': {'required': False},
            'buffer_time': {'required': False},
            'planned_fee': {'required': False},
            'urgent_fee': {'required': False}
        }
        
        
class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = ['timezone', 'language', 'use_system_timezone', 'use_system_language']
        
        
class ReschedulePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = ReschedulePolicy
        fields = '__all__'
        


class CancellationPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = CancellationPolicy
        fields = ['no_fee_cancellation_period', 'fee_percentage', 'chargeable_cancellation_period']
        # Exclude doctor from input fields, it will be set automatically in the view
        read_only_fields = ['doctor']

    def create(self, validated_data):
        # Set the authenticated user as the doctor
        validated_data['doctor'] = self.context['request'].user
        return super().create(validated_data)


class NoShowPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = NoShowPolicy
        fields = ['user', 'planned', 'urgent', 'waiting_time_planned', 'waiting_time_urgent']
        extra_kwargs = {
            'planned': {'required': False},
            'urgent': {'required': False},
            'waiting_time_planned': {'required': False},
            'waiting_time_urgent': {'required': False},
        }
        
        
class CommunicationPreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommunicationPreferences
        fields = '__all__'
        extra_kwargs = {'user': {'read_only': True}}
        
        

class TwoFactorAuthMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = TwoFactorAuthMethod
        fields = ['user', 'method']
        read_only_fields = ['user']