from rest_framework import serializers
from users.models import User


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "username",
            "email",
            "password",
            "role",
            "dob",
            "gender",
            "country",
            "city",
            "phone_number",
            "bio",
        ]

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user
