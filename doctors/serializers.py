from rest_framework import serializers
from .models import DoctorNotes
from .models import Referral, Invitation, AppointmentManagement
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
    class Meta:
        model = Referral
        fields = ['personal_code', 'registry_link', 'points', 'users_invited']


User = get_user_model()

class InvitationSerializer(serializers.ModelSerializer):
    invited_user_email = serializers.EmailField(write_only=True)

    class Meta:
        model = Invitation
        fields = ['id', 'invitation_code', 'invited_user_email', 'created_at', 'redeemed']

    def create(self, validated_data):
        invited_by = self.context['invited_by']
        invited_user_email = validated_data['invited_user_email']

        # Ensure the email isn't already registered
        if User.objects.filter(email=invited_user_email).exists():  # Fixed: Now uses the correct User model
            raise serializers.ValidationError({"invited_user_email": "This email is already registered."})

        # Create the invitation
        invitation = Invitation.objects.create(
            invited_by=invited_by,
            invitation_code=invited_by.personal_code,
            invited_user_email=invited_user_email
        )

        # Mock email sending (replace with actual implementation)
        self.send_invitation_email(invited_user_email, invited_by.registry_link)

        return invitation

    def send_invitation_email(self, email, link):
        print(f"Invitation email sent to {email} with link: {link}")  # Replace with actual email logic


class AppointmentManagementSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppointmentManagement
        fields = ['id', 'user', 'appointment_type', 'days', 'start_time', 'end_time']
        read_only_fields = ['user']