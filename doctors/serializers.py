from rest_framework import serializers
from .models import (
    Referral, Invitation,
    AppointmentManagement,
    ConsultationSessionAndFee,
    UserPreference,
    ReschedulePolicy,
    CancellationPolicy,
    NoShowPolicy,
    CommunicationPreferences,
    BookedAppointment,
    DoctorSchedule,
    # Slot,
)
from payments.models import Payment
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
        fields = ['id', 'doctor', 'appointment_type', 'days', 'start_time', 'end_time']
        read_only_fields = ['doctor']
        
class DoctorScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorSchedule
        fields = ['doctor', 'schedule']
        

class ConsultationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultationSessionAndFee
        fields = '__all__'
        extra_kwargs = {
            'doctor': {'required': True},
            'doctor_id': {'required': True},
            'planned_session': {'required': False},
            'urgent_session': {'required': False},
            'planned_session_length': {'required': False},
            'urgent_session_length': {'required': False},
            'buffer_time': {'required': False},
            'planned_fees': {'required': False},
            'urgent_fees': {'required': False}
        }
        

# class AvailableSlotSerializer(serializers.ModelSerializer):
#     day_id = serializers.SerializerMethodField()

#     class Meta:
#         model = Slot
#         fields = ["day_id", "day", "time_slot", "status"]

#     def get_day_id(self, obj):
#         return hash(obj.day)  # Generate a unique ID for each day


class BookedAppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookedAppointment
        fields = '__all__'


class PaymentSummarySerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    hour = serializers.SerializerMethodField()
    subtotal = serializers.SerializerMethodField()
    discount = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = ["category", "date", "hour", "subtotal", "discount", "total"]

    def get_category(self, obj):
        """Fetch specialty from the Doctor model"""
        try:
            return obj.appointment.doctor.specialty 
        except AttributeError:
            return "Unknown"

    def get_date(self, obj):
        """Return the current date"""
        return now().strftime("%d %b, %Y")

    def get_hour(self, obj):
        """Return the current time"""
        return now().strftime("%I:%M %p")

    def get_subtotal(self, obj):
        """Fetch planned_fee or urgent_fee from ConsultationSettings"""
        try:
            consultation = ConsultationSessionAndFee.objects.get(doctor=obj.appointment.doctor)
            return f"${consultation.planned_fee or consultation.urgent_fee:.2f}"
        except ConsultationSessionAndFee.DoesNotExist:
            return "$0.00"

    def get_discount(self, obj):
        """Set discount (modify logic if needed)"""
        return "$0.00"

    def get_total(self, obj):
        """Total amount calculation (considering discount if applicable)"""
        subtotal = float(self.get_subtotal(obj).replace("$", ""))
        return f"${subtotal:.2f}"


        
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

    
    