from rest_framework import serializers
from users.models import User
from .models import AllergyDocument, MedicalHistory, Favourite, FamilyMember, OTPVerification
from clinics.serializers import ClinicSerializer
from doctors.models import Doctor
import os

class PatientUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "phone_number", "profile_picture", "role", "city", "country", "residence"]

# Validator for file type
def validate_document_file(value):
    ext = os.path.splitext(value.name)[1].lower()
    allowed_extensions = [".pdf", ".jpg", ".jpeg", ".png"]

    if ext not in allowed_extensions:
        raise serializers.ValidationError("Only PDF, JPG, and PNG files are allowed.")

class MedicalDocumentSerializer(serializers.ModelSerializer):
    patient = serializers.PrimaryKeyRelatedField(read_only=True)  # Make patient read-only

    class Meta:
        model = MedicalHistory
        fields = '__all__'  # Keep all fields, but patient is not required in input

class AllergyDocumentSerializer(serializers.ModelSerializer):
    patient = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = AllergyDocument
        fields = '__all__'
        

class FavouriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Favourite
        fields = ["id", "patient", "fav_doc", "doc_status", "fav_clinic", "clinic_status"]
        read_only_fields = ["patient"]

class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = '__all__'
class FavouriteDoctorSerializer(serializers.ModelSerializer):
    fav_doc = DoctorSerializer()
    class Meta:
        model = Favourite
        fields = ["id", "patient", "doc_status", "fav_doc"]
        read_only_fields = ["patient"]

class FavouriteClinicSerializer(serializers.ModelSerializer):
    fav_clinic = ClinicSerializer()
    class Meta:
        model = Favourite
        fields = ["id", "patient", "clinic_status", "fav_clinic"]
        read_only_fields = ["patient"]


class FamilyMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = FamilyMember
        fields = ["id", "member_name", "member_email", "family_status", "is_verified"]

class OTPVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OTPVerification
        fields = ["family_member", "otp"]