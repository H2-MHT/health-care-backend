from rest_framework import serializers
from .models import DoctorNotes
from .models import Referral, Invitation, AppointmentManagement, ConsultationSettings
from users.models import User
from django.contrib.auth import get_user_model


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
        fields = ['id', 'session_type', 'session_length', 'buffer_time', 'planned_fee_per_15_min', 'urgent_fee_per_15_min', 'doctor'
        ]
    
    def validate_session_length(self, value):
        if value not in [15, 30]:
            raise serializers.ValidationError("Session length must be either 15 or 30 minutes.")
        return value