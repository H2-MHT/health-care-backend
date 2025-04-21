from rest_framework import serializers
from .models import Review, Reply, Report
from patients.models import Patient
from doctors.models import BookedAppointment

from appointments.models import Appointment

class ReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.SerializerMethodField()
    reviewer_profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['id', 'reviewer_name', 'doctor', 'patient', 'reviewer_profile_picture', 'rating', 'title', 'content', 'recommend', 'created_at']
        extra_kwargs = {
            'doctor': {'required': False},
            'patient': {'required': False},
        }
    def get_reviewer_name(self, obj):
        return obj.patient.user.first_name if obj.patient and obj.patient.user else "Unknown"

    def get_reviewer_profile_picture(self, obj):
        if obj.patient and obj.patient.user and hasattr(obj.patient.user, 'profile_picture'):
            return obj.patient.user.profile_picture.url if obj.patient.user.profile_picture else None
        return None


class ReviewUpdateSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.SerializerMethodField()
    reviewer_profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['id', 'reviewer_name', 'reviewer_profile_picture', 'doctor', 'rating','title', 'content', 'recommend', 'created_at']

    def get_reviewer_name(self, obj):
        return obj.patient.user.first_name if obj.patient and obj.patient.user else "Unknown"

    def get_reviewer_profile_picture(self, obj):
        if obj.patient and obj.patient.user and hasattr(obj.patient.user, 'profile_picture'):
            return obj.patient.user.profile_picture.url if obj.patient.user.profile_picture else None
        return None

class ReplySerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()  # Add user name field
    user_type = serializers.SerializerMethodField()  # Add user type field
    user = serializers.StringRelatedField()  # Show user (patient/doctor)
    parent_reply = serializers.PrimaryKeyRelatedField(queryset=Reply.objects.all(), required=False)
    created_at = serializers.DateTimeField(read_only=True)
    patient_name = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()  # To get the profile picture from the User model

    class Meta:
        model = Reply
        fields = ['id', 'user', 'user_name', 'profile_picture', 'user_type', 'patient_name', 'content', 'created_at', 'parent_reply']

    def get_user_name(self, obj):
        # Get the user's name based on whether they are a doctor or patient
        if hasattr(obj.user, 'patient'):
            return obj.user.patient.user.first_name  # Patient's first name
        elif hasattr(obj.user, 'doctor'):
            return obj.user.doctor.user.first_name  # Doctor's first name
        return None

    def get_user_type(self, obj):
        # Get the user's type (patient or doctor)
        if hasattr(obj.user, 'patient'):
            return 'patient'
        elif hasattr(obj.user, 'doctor'):
            return 'doctor'
        return None

    def get_profile_picture(self, obj):
        user = obj.user  # Access the associated User object
        return user.profile_picture.url if user.profile_picture else None  # Return the URL of the profile picture, or None if no picture exists


    def get_patient_name(self, obj):
        if hasattr(obj.user, 'patient') and obj.user.patient.user:
            return obj.user.patient.user.first_name
        return None

class ReportSerializer(serializers.ModelSerializer):
    review_id = serializers.ReadOnlyField(source="review.id")
    reported_by = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = ["id", "review_id", "content", "reported_by", "reason", "status", "created_at"]

    def get_reported_by(self, obj):
        return obj.reported_by.get_full_name()
    
    def get_content(self, obj):
        return obj.review.content