from rest_framework import serializers
from django.contrib.auth import get_user_model
import json
from doctors.models import Doctor
from users.models import User
import re
from clinics.models import Clinic
from patients.models import Patient
class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    languages = serializers.CharField(max_length=255, write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "password",
            "currency",
            "confirm_password",
            "role",
            "dob",
            "gender",
            "country",
            "city",
            "bio",
            "languages",
            "work_place",
            "expertise",
            "professional_stat",
            "residence",
            "working_time",
            "profile_picture",
            "phone_number",
            "rating",
            "reviews"
        ]
        extra_kwargs = {
            "email": {"required": True}
        }

    def validate_email(self, value):
        """
        Override default unique email validation:
        Allow if user exists but is unverified.
        """
        user = User.objects.filter(email=value).first()
        if user and user.is_verified:
            raise serializers.ValidationError("User with this email is already verified.")
        return value

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError("Passwords must match.")
        return data

    def create(self, validated_data):
        validated_data.pop("confirm_password", None)
        languages_data = validated_data.pop("languages", [])

        if isinstance(languages_data, str):
            try:
                languages_data = json.loads(languages_data)
            except json.JSONDecodeError:
                languages_data = []

        email = validated_data.get("email")
        existing_user = User.objects.filter(email=email).first()

        if existing_user:
            if existing_user.is_verified:
                raise serializers.ValidationError({"email": "User with this email is already verified."})
            else:
                # Update the existing unverified user instead of deleting
                existing_user.first_name = validated_data.get("first_name", existing_user.first_name)
                existing_user.last_name = validated_data.get("last_name", existing_user.last_name)
                existing_user.password = validated_data.get("password", existing_user.password)
                existing_user.set_password(existing_user.password)  # hashed password
                existing_user.is_verified = False  # unverified for re-registration
                existing_user.otp = ""  # Reset OTP
                existing_user.otp_created_at = None  # Clear OTP timestamp
                existing_user.save(update_fields=['first_name', 'last_name', 'password', 'is_verified', 'otp', 'otp_created_at'])

                # Proceed with any necessary updates, like languages
                if languages_data:
                    existing_user.languages.set(languages_data)

                return existing_user


        user = User(**validated_data)
        user.set_password(validated_data["password"])
        user.save()

        if languages_data:
            user.languages.set(languages_data)

        return user


    def update(self, instance, validated_data):
        validated_data.pop("confirm_password", None)
        languages = validated_data.pop("languages", [])

        for attr, value in validated_data.items():
            if attr == "password":
                instance.set_password(value)
            else:
                setattr(instance, attr, value)

        if isinstance(languages, str):
            try:
                languages = json.loads(languages)
            except json.JSONDecodeError:
                languages = []

        instance.save()

        if languages:
            instance.languages.set(languages)

        return instance

class OTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)


class SignInSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES)
    def validate(self, data):
        email = data.get("email")
        password = data.get("password")
        role = data.get("role")
        # Get the user model
        User = get_user_model()

        # Retrieve the user by email
        user = User.objects.filter(email=email).first()

        if not user:
            raise serializers.ValidationError("Invalid email or password.")

        # Check the user's password
        if not user.check_password(password):
            raise serializers.ValidationError("Invalid email or password.")
        
        # Check the user's role
        if role!= user.role:
            raise serializers.ValidationError(f"Invalid role. User's role is {user.role}")
        
        if user.role in ["Patient", "Doctor"] and not user.is_verified:
            raise serializers.ValidationError("You are not verified. Request new OTP to verify your account.")

        # Reactivate the account if it's inactive
        if not user.is_active:
            user.is_active = True
            user.save()

        # Add the user object to the validated data
        data["user"] = user
        return data


class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True)

    def validate(self, data):
        request = self.context["request"]
        user = request.user

        if not user or not user.is_authenticated:
            raise serializers.ValidationError({"access": "Invalid or expired token."})

        new_password = data.get("new_password")

        error_list = []
        if len(new_password) < 8:
            error_list.append("Password must be at least 8 characters long.")
        if not re.search(r"[A-Za-z]", new_password):
            error_list.append("Password must contain at least one letter.")
        if not re.search(r"[0-9]", new_password):
            error_list.append("Password must contain at least one number.")
        if not re.search(r"[@$!%*?&]", new_password):
            error_list.append("Password must contain at least one special character.")
        
        if error_list:
            raise serializers.ValidationError({'errors':error_list})
        
        return data

    def save(self):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        
        
class SocialLoginSerializer(serializers.Serializer):
    ROLE_CHOICES = [
        ("Patient", "Patient"),
        ("Doctor", "Doctor"),
    ]
    role = serializers.ChoiceField(choices=ROLE_CHOICES, required=False)
    token = serializers.CharField(required=True)


# Validation for profile picture
def validate_profile_picture(value):
    if value.size > 2 * 1024 * 1024:  # Limit size to 2 MB
        raise serializers.ValidationError("Profile picture must be smaller than 2 MB.")
    if not value.name.lower().endswith((".png", ".jpg", ".jpeg")):
        raise serializers.ValidationError("Profile picture must be a PNG or JPG file.")
    return value


class UserProfileSerializer(serializers.ModelSerializer):
    experience_years = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "role",
            "dob",
            "gender",
            "phone_number",
            "bio",
            "country",
            "city",
            "currency",
            "residence",
            "languages",
            "work_place",
            "expertise",
            "professional_stat",
            "working_time",
            "profile_picture",
            "experience_years"
        ]
        
    def to_representation(self, instance):
        """Customize GET response for languages"""
        data = super().to_representation(instance)
        exp = Doctor.objects.filter(user=instance).first()
        if exp:
            data['experience_years'] = exp.experience_years
        return data
    def get_email(self, obj):
        """Return email only if Patient has show_email=True."""
        if obj.role == "Patient":
            try:
                if not obj.patient_profile.show_email:
                    return None  # Hide email
            except Patient.DoesNotExist:
                return None  # No patient profile found
        return obj.email  # Show email

    def get_phone_number(self, obj):
        """Return phone number only if Patient has show_phone=True."""
        if obj.role == "Patient":
            try:
                if not obj.patient_profile.show_phone:
                    return None  # Hide phone number
            except Patient.DoesNotExist:
                return None  # No patient profile found
        return obj.phone_number  # Show phone number
    
    
class UserProfileUpdateSerializer(UserProfileSerializer):
    profile_picture = serializers.ImageField(
        required=False, validators=[validate_profile_picture]
    )
    languages = serializers.CharField(required=False)
    show_email = serializers.BooleanField(required=False)
    show_phone = serializers.BooleanField(required=False)
    class Meta(UserProfileSerializer.Meta):
            fields = UserProfileSerializer.Meta.fields + ['show_email', 'show_phone']

    def update(self, instance, validated_data):
        languages = validated_data.pop('languages', [])
        if isinstance(languages, str):
            try:
                languages = json.loads(languages)
            except json.JSONDecodeError:
                languages = []

        # Doctor-specific logic
        if instance.role == "Doctor":
            experience_years = validated_data.pop('experience_years', None)
            clinic = validated_data.pop('clinic', None)

            doc = Doctor.objects.filter(user=instance).first()
            if doc:
                if experience_years is not None:
                    doc.experience_years = experience_years

                if clinic and clinic != "other":
                    try:
                        clinic_instance = Clinic.objects.get(id=clinic)
                        doc.work_place = clinic_instance
                    except Clinic.DoesNotExist:
                        raise serializers.ValidationError("Invalid clinic ID.")

                doc.save()

        # Patient-specific logic
        if instance.role == "Patient" and hasattr(instance, 'patient_profile'):
            show_email = validated_data.pop('show_email', None)
            show_phone = validated_data.pop('show_phone', None)

            if show_email is not None:
                instance.patient_profile.show_email = show_email
            if show_phone is not None:
                instance.patient_profile.show_phone = show_phone
            instance.patient_profile.save()

        # Update other fields dynamically
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if languages:
            instance.languages.set(languages)

        # Save the main instance (UserProfile)
        instance.save()
        return instance
    
    def to_representation(self, instance):
        """Customize GET response for languages"""
        data = super().to_representation(instance)
        data['languages'] = list(instance.languages.values_list("id", flat=True))

        # Include patient fields if available
        if instance.role == "Patient" and hasattr(instance, 'patient_profile'):
            data['show_email'] = instance.patient_profile.show_email
            data['show_phone'] = instance.patient_profile.show_phone

        return data
