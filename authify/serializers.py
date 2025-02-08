from rest_framework import serializers
from django.contrib.auth import get_user_model
import json
from users.models import User


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
        ]

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError("Passwords must match.")
        return data

    def create(self, validated_data):
        validated_data.pop(
            "confirm_password"
        )  # Remove confirm_password field before saving

        languages = validated_data.pop('languages', [])
        # Handle services_provided

        if isinstance(languages, str):
            try:
                languages = json.loads(languages)
            except json.JSONDecodeError:
                languages = []  

        user = User(**validated_data)
        user.set_password(validated_data["password"])  # Hash the password
        if languages:
            user.languages.set(languages)
        user.save()
        return user


class OTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)


class SignInSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        # Get the user model
        User = get_user_model()

        # Retrieve the user by email
        user = User.objects.filter(email=email).first()
        if not user:
            raise serializers.ValidationError("Invalid email or password.")

        # Check the user's password
        if not user.check_password(password):
            raise serializers.ValidationError("Invalid email or password.")

        # Reactivate the account if it's inactive
        if not user.is_active:
            user.is_active = True
            user.save()

        # Add the user object to the validated data
        data["user"] = user
        return data


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
    if not value.name.lower().endswith(('.png', '.jpg', '.jpeg')):
        raise serializers.ValidationError("Profile picture must be a PNG or JPG file.")
    return value
class UserProfileUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    dob = serializers.DateField(required=False)
    gender = serializers.ChoiceField(choices=["Male", "Female", "Other"], required=False)
    phone_number = serializers.CharField(required=False)
    bio = serializers.CharField(required=False)
    country = serializers.CharField(required=False)
    city = serializers.CharField(required=False)
    languages = serializers.CharField(required=False)
    work_place = serializers.CharField(required=False)
    expertise = serializers.CharField(required=False)
    professional_stat = serializers.CharField(required=False)
    working_time = serializers.CharField(required=False)
    profile_picture = serializers.ImageField(required=False, validators=[validate_profile_picture])

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        languages = validated_data.pop('languages', [])
        # Handle services_provided

        if isinstance(languages, str):
            try:
                languages = json.loads(languages)
            except json.JSONDecodeError:
                languages = [] 
        if languages:
            instance.languages.set(languages)        
        instance.save()
        return instance


class UserProfileSerializer(serializers.ModelSerializer):
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
            "languages",
            "work_place",
            "expertise",
            "professional_stat",
            "working_time",
            "profile_picture",
        ]
    
    