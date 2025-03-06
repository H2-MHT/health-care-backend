from rest_framework import serializers
from users.models import User

class PatientUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "phone_number", "profile_picture", "role", "city", "country", "residence"]
