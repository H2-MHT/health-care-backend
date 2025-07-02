from rest_framework import serializers
from clinics.models import *
from users.models import User
import json
from appointments.serializers import AppointmentSerializer

class ClinicRegisterSerializer(serializers.ModelSerializer):
    working_time = serializers.CharField(max_length=255,required=False)
    services_provided = serializers.CharField(max_length=255, write_only=True)
    languages = serializers.CharField(max_length=255, write_only=True)

    class Meta:
        model = Clinic
        fields = [
            'address', 'website', 'contact_email', 'contact_phone',
            'services_provided', 'languages', 'licenses_certificate',
            'administrator_name', 'administrator_email', 'working_time'
        ]

    def create(self, validated_data):
        working_time = validated_data.pop('working_time', None)
        services_provided = validated_data.pop('services_provided', [])
        languages = validated_data.pop('languages', [])
        user = self.context['request'].user

        # Handle services_provided
        if isinstance(services_provided, str):
            try:
                services_provided = json.loads(services_provided)
            except json.JSONDecodeError:
                services_provided = []

        if isinstance(languages, str):
            try:
                languages = json.loads(languages)
            except json.JSONDecodeError:
                languages = []        

        # Save working_time & languages to User model
        if working_time:
            user.working_time = working_time
        if languages:
            user.languages.set(languages)  # Ensures Many-to-Many assignment
        user.is_verified = True
        user.save()

        # Create the Clinic instance
        clinic = Clinic.objects.create(user=user, **validated_data)
        clinic.services_provided.set(services_provided)  # Assign Many-to-Many
        return clinic


class ClinicSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.first_name', read_only=True)
    profile_picture = serializers.ImageField(source='user.profile_picture', read_only=True)
    class Meta:
        model = Clinic
        fields = '__all__'
        extra_fields = ('name', 'profile_picture')

class ClinicListSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    profile_picture = serializers.ImageField(source='user.profile_picture', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Clinic
        fields = ['id', 'name', 'profile_picture', 'email']

    def get_name(self, obj):
        if obj.user:
            return f"{obj.user.first_name} {obj.user.last_name}".strip()
        return ""

class ClinicDetailSerializer(serializers.ModelSerializer):
    clinic_id = serializers.IntegerField(source='user.id', read_only=True)
    name = serializers.CharField(source='user.first_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    country = serializers.CharField(source='user.country', read_only=True)
    city = serializers.CharField(source='user.city', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    bio = serializers.CharField(source='user.bio', read_only=True)
    profile_picture = serializers.ImageField(source='user.profile_picture', read_only=True)
    currency = serializers.CharField(source='user.currency', read_only=True)

    class Meta:
        model = Clinic
        fields = [
            # user fields
            'clinic_id', 'name', 'email', 'country', 'city', 'phone_number', 'bio', 'profile_picture', 'currency',
            # clinic fields
            'address', 'organisation_name', 'license_number', 'clinic_type', 'public_name',
        ]
class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = '__all__'


class ServicesProvidedSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServicesProvided
        fields = '__all__'


class ClinicInfoSerializer(serializers.ModelSerializer):
    # User fields
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    bio = serializers.CharField(source='user.bio', required=False)
    country = serializers.CharField(source='user.country', required=False)
    city = serializers.CharField(source='user.city', required=False)
    phone_number = serializers.CharField(source='user.phone_number', required=False)
    email =  serializers.SerializerMethodField()
    working_time = serializers.CharField(source='user.working_time', required=False)
    expertise = serializers.CharField(source='user.expertise', required=False)
    languages = serializers.SerializerMethodField()
    profile_picture = serializers.ImageField(source='user.profile_picture', required=False)
    class Meta:
        model = Clinic
        fields = [
            # User fields
            'first_name', 'last_name','bio', 'country', 'city', 'phone_number', 'email', 'working_time', 'expertise', 'languages', 'profile_picture',

            # Clinic fields
            'address', 'organisation_name', 'license_number', 'clinic_type', 'public_name', 
            'clinic_logo', 'website'
        ]

    def get_email(self, obj):
        return obj.user.email if obj.user else None
    
    def get_languages(self, obj):
        try:
            return list(obj.user.languages.values_list("id", flat=True)) if obj.user else []
        except Exception as e:
            return []

    # def to_representation(self, instance):
    #     data = super().to_representation(instance)
    #     try:
    #         data['languages'] = list(instance.user.languages.values_list("id", flat=True)) if instance.user else []
    #     except Exception as e:
    #         data['languages'] = []
    #     return data

    def update(self, instance, validated_data):
        # Extract user data if present
        user_data = validated_data.pop('user', {})  
        user = instance.user  # Get associated User instance

        # Extract languages from request directly
        request = self.context.get('request')
        raw_languages = request.data.get('languages')

        languages = []
        if raw_languages:
            if isinstance(raw_languages, list):
                languages = [int(l) for l in raw_languages if l.isdigit()]
            elif isinstance(raw_languages, str):
                try:
                    parsed = json.loads(raw_languages)
                    if isinstance(parsed, list):
                        languages = [int(l) for l in parsed if isinstance(l, (int, str)) and str(l).isdigit()]
                except json.JSONDecodeError:
                    pass

        # Update user fields
        for attr, value in user_data.items():
            if value is not None:
                setattr(user, attr, value)

        if languages:
            user.languages.set(languages)

        user.save()

        # Update Clinic fields
        for attr, value in validated_data.items():
            if value is not None:
                setattr(instance, attr, value)

        instance.save()
        return instance


class ClinicReviewSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source="doctor.user.get_full_name", read_only=True)
    doctor_profile_picture = serializers.ImageField(source="doctor.user.profile_picture", read_only=True)
    
    clinic_name = serializers.CharField(source="clinic.user.first_name", read_only=True)
    clinic_profile_picture = serializers.ImageField(source="clinic.user.profile_picture", read_only=True)

    class Meta:
        model = ClinicReview
        fields = [
            'id', 'clinic', 'clinic_name', 'clinic_profile_picture', 'doctor_name', 'doctor_profile_picture',
            'rating', 'title', 'content', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ClinicReviewReplySerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)
    user_profile_picture = serializers.ImageField(source="user.profile_picture", read_only=True)

    class Meta:
        model = ClinicReviewReply
        fields = ['id', 'user_name', 'user_profile_picture', 'content', 'created_at']
        read_only_fields = ['id', 'created_at']


class ActiveDoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "profile_picture", "last_activity"]


class ClinicDoctorSerializer(serializers.ModelSerializer):
    years = serializers.IntegerField(source="doctor.experience_years", read_only=True)
    doctor_id = serializers.IntegerField(source="doctor.id", read_only=True)
    specialty = serializers.CharField(source="doctor.specialty", read_only=True)
    languages = LanguageSerializer(many=True, read_only=True)
    qualifications = serializers.CharField(source="doctor.qualifications", read_only=True)
    clinic_name = serializers.CharField(source="work_place.user.first_name", read_only=True)
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "profile_picture",
            "bio",
            "expertise",
            "languages",
            "country",
            "years",
            "specialty",
            "doctor_id",
            "rating",
            "reviews",
            "qualifications",
            "clinic_name"
        ]


class CalendarAppointmentSerializer(AppointmentSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)

        # Safely retrieve patient details
        patient_user = getattr(instance.patient, "user", None)
        patient_profile_picture = (
            patient_user.profile_picture.url if patient_user and patient_user.profile_picture else None
        )
        data["patient"] = {
            "id": instance.patient.id,
            "name": patient_user.get_full_name() if patient_user else "Unknown",
            "profile_picture": patient_profile_picture
        }

        # Safely retrieve doctor details
        doctor_user = getattr(instance.doctor, "user", None)
        doctor_profile_picture = (
            doctor_user.profile_picture.url if doctor_user and doctor_user.profile_picture else None
        )
        data["doctor"] = {
            "id": instance.doctor.id,
            "name": doctor_user.get_full_name() if doctor_user else "Unknown",
            "profile_picture": doctor_profile_picture
        }

        return data


class OtherClinicSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)

    class Meta:
        model = OtherClinic
        fields = ["id", "clinic_name", "address", "website"]

    def create(self, validated_data):
        doctor = self.context.get("doctor")
        if not doctor:
            raise serializers.ValidationError("Doctor context is required.")
        return OtherClinic.objects.create(doctor=doctor, **validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
    
class ClinicAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clinic
        fields = ["id","address"]