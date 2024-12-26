from django.contrib.auth import authenticate
from rest_framework import serializers

from users.models import User


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

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
            "licenses_certificate",
            "media_digest",
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
        user = User(**validated_data)
        user.set_password(validated_data["password"])  # Hash the password
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

        # Authenticate the user
        user = authenticate(email=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("Account is inactive.")

        data["user"] = user
        return data


class SocialLoginSerializer(serializers.Serializer):
    ROLE_CHOICES = [
        ("Patient", "Patient"),
        ("Doctor", "Doctor"),
    ]
    role = serializers.ChoiceField(choices=ROLE_CHOICES, required=False)
    token = serializers.CharField(required=True)


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "role",
            "dob",
            "gender",
            "phone_number",
            "profile_picture",
            "bio",
            "country",
            "city",
            "residence",
            "languages",
            "work_place",
            "expertise",
            "professional_stat",
            "working_time",
            "licenses_certificate",
            "media_digest",
        ]
        read_only_fields = ["email", "role", "is_verified"]

    def validate_first_name(self, value):
        if not value:
            raise serializers.ValidationError("First name is required.")
        return value

    def validate_last_name(self, value):
        if not value:
            raise serializers.ValidationError("Last name is required.")
        return value

    def validate_phone_number(self, value):
        if value and not value.isdigit():
            raise serializers.ValidationError("Phone number must contain only digits.")
        return value

    def validate(self, data):
        """
        Ensure mandatory fields are not empty during update.
        """
        user = self.instance  # Existing user instance

        if "first_name" in data and not data["first_name"]:
            raise serializers.ValidationError({"first_name": "First name cannot be empty."})
        if "last_name" in data and not data["last_name"]:
            raise serializers.ValidationError({"last_name": "Last name cannot be empty."})

        if not user.first_name:
            raise serializers.ValidationError({"first_name": "First name is required."})
        if not user.last_name:
            raise serializers.ValidationError({"last_name": "Last name is required."})

        return data

