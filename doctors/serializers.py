from rest_framework import serializers
from .models import (
    Referral, Invitation,
    AppointmentManagement,
    ConsultationSettings,
    UserPreference,
    ReschedulePolicy,
    CancellationPolicy,
    NoShowPolicy,
    CommunicationPreferences,
)
from datetime import datetime, timedelta
from django.contrib.auth.hashers import check_password
from users.models import User
from django.utils.timezone import now

# class DoctorNotesSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = DoctorNotes
#         fields = ['id', 'title', 'note', 'created_at']
#         read_only_fields = ['id', 'created_at', 'doctor']

#     def create(self, validated_data):
#         request = self.context.get("request")
#         if not hasattr(request.user, "doctor"):  # Ensure the user is a doctor
#             raise serializers.ValidationError({"error": "Only doctors can create notes."})
#         validated_data["doctor"] = request.user.doctor  # Assign the related Doctor instance
#         return super().create(validated_data)
    
    
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
        fields = ['id', 'user', 'allow_reschedule', 'max_reschedules', 'reschedule_days', 'reschedule_time_range']

    def validate_reschedule_days(self, value):
        """Ensure the reschedule_days field contains a valid weekday abbreviation (Mon, Tue, etc.)."""
        valid_days = dict(ReschedulePolicy.DAYS_CHOICES).keys()
        if value not in valid_days:
            raise serializers.ValidationError("Invalid day. Choose from Mon, Tue, Wed, Thu, Fri, Sat, Sun.")
        return value


class CancellationPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = CancellationPolicy
        fields = ['id','no_fee_cancellation_period', 'fee_percentage', 'chargeable_cancellation_period']
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
        
        

# Serializer for Selecting 2FA Methods
class PasswordChangeRequestSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not check_password(value, user.password):
            raise serializers.ValidationError("Incorrect old password.")
        return value

class PasswordChangeConfirmSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True)
    otp = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        return value

    
    