from rest_framework import serializers
from patients.models import Patient
from users.models import User

class PatientListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields =['id','profile_picture','first_name','last_name','phone_number','country','is_active']


class PatientDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'profile_picture','email','first_name', 'last_name', 'phone_number', 'country','dob','gender','bio','city','residence',
                  'languages','work_place','expertise','professional_stat','is_active']


class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "phone_number", "is_active"]