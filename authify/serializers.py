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

        languages = validated_data.pop("languages", [])
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
    if not value.name.lower().endswith((".png", ".jpg", ".jpeg")):
        raise serializers.ValidationError("Profile picture must be a PNG or JPG file.")
    return value


class UserProfileSerializer(serializers.ModelSerializer):
    years = serializers.IntegerField(source="doctor.experience_years", read_only=True)

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
            "years",
        ]


class UserProfileUpdateSerializer(UserProfileSerializer):
    profile_picture = serializers.ImageField(
        required=False, validators=[validate_profile_picture]
    )
    languages = serializers.CharField(required=False)

    def update(self, instance, validated_data):

        languages = validated_data.pop('languages', [])
        if isinstance(languages, str):
            try:
                languages = json.loads(languages)
            except json.JSONDecodeError:
                languages = []

        # Update other fields dynamically
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if languages:
            instance.languages.set(languages)

        instance.save()
        return instance
    
    def to_representation(self, instance):
        """Customize GET response for languages"""
        data = super().to_representation(instance)
        data['languages'] = list(instance.languages.values_list("id", flat=True))
        return data