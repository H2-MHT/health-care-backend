from rest_framework import serializers
from users.models import User
from .models import(
    AllergyDocument,
    MedicalHistory,
    Favourite,
    FamilyMember,
    OTPVerification,
    Reminder,
)
from clinics.serializers import ClinicSerializer
from doctors.models import Doctor
from users.serializers import UserSerializer
import os

class PatientUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "phone_number", "profile_picture", "role", "city", "country", "residence"]
class PatientSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "name", "profile_picture"]
        read_only_fields = ["id"]

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()
    
# Validator for file type
def validate_document_file(value):
    ext = os.path.splitext(value.name)[1].lower()
    allowed_extensions = [".pdf", ".jpg", ".jpeg", ".png"]

    if ext not in allowed_extensions:
        raise serializers.ValidationError("Only PDF, JPG, and PNG files are allowed.")

class MedicalDocumentSerializer(serializers.ModelSerializer):
    patient = serializers.SerializerMethodField()
    class Meta:
        model = MedicalHistory
        fields = ["id", "name", "document_link", "date", "patient"]

    def get_patient(self, obj):
        return obj.patient.id if obj.patient else None

class AllergyDocumentSerializer(serializers.ModelSerializer):
    patient=serializers.SerializerMethodField()
    class Meta:
        model = AllergyDocument
        fields = ["id","name","document_link","date","patient"]

    def get_patient(self, obj):
        return obj.patient.id if obj.patient else None
        

class FavouriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favourite
        fields = ["id", "patient", "fav_doc", "doc_status", "fav_clinic", "clinic_status"]
        read_only_fields = ["patient"]

class DoctorSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Doctor
        fields = ["id", "user", "specialty", "qualifications", "experience_years"]
class FavouriteDoctorSerializer(serializers.ModelSerializer):
    fav_doc = DoctorSerializer()
    class Meta:
        model = Favourite
        fields = ["id", "patient", "doc_status", "fav_doc"]
        read_only_fields = ["patient"]

class FavouriteClinicSerializer(serializers.ModelSerializer):
    fav_clinic = ClinicSerializer()
    profile_picture = serializers.ImageField(source='user.profile_picture', read_only=True)
    class Meta:
        model = Favourite
        fields = ["id", "patient", "clinic_status", "fav_clinic", "profile_picture"]
        read_only_fields = ["patient"]

class FamilyMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = FamilyMember
        fields = ["id", "member_name", "member_email", "family_status", "member_profile", "is_verified"]

class OTPVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OTPVerification
        fields = ["family_member", "otp"]
        
        
class ReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reminder
        fields = ["notification_method", "notification_time", "notification_time_type"]
        read_only_fields = ['user_patient_name', 'appointment']  
        
