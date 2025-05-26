from rest_framework import serializers

from doctors.models import Specialization
from patients.models import Patient
from users.models import User
from doctors.models import Doctor

class PatientListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields =['id','profile_picture','first_name','last_name','phone_number','country','is_active']


class PatientDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'profile_picture','email','first_name', 'last_name', 'phone_number', 'country','dob','gender','bio','city','residence',
                  'languages','work_place','expertise','professional_stat','is_active']

class DoctorDetailSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='user.id')
    profile_picture = serializers.ImageField(source='user.profile_picture')
    email = serializers.EmailField(source='user.email')
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    phone_number = serializers.CharField(source='user.phone_number')
    country = serializers.CharField(source='user.country')
    dob = serializers.DateField(source='user.dob')
    gender = serializers.CharField(source='user.gender')
    bio = serializers.CharField(source='user.bio')
    city = serializers.CharField(source='user.city')
    residence = serializers.CharField(source='user.residence')
    languages = serializers.SerializerMethodField()
    work_place = serializers.CharField(source='user.work_place')
    expertise = serializers.CharField(source='user.expertise')
    professional_stat = serializers.CharField(source='user.professional_stat')
    is_active = serializers.BooleanField(source='user.is_active')

    class Meta:
        model = Doctor
        fields = [
            # User fields
            'id', 'profile_picture', 'email', 'first_name', 'last_name', 'phone_number', 'country',
            'dob', 'gender', 'bio', 'city', 'residence', 'languages', 'work_place',
            'expertise', 'professional_stat', 'is_active',
            
            # Doctor fields
            'specialty', 'qualifications', 'experience_years', 'available_dates',
            'is_verified', 'planned_hourly_rate', 'urgent_hourly_rate', 'stripe_link'
        ]
    def get_languages(self, obj):
        return [lang.title for lang in obj.user.languages.all()]

class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "phone_number", "is_active"]



class SpecializationSerializer(serializers.ModelSerializer):
    class Meta:
        model=Specialization
        fields=["id","name","description","is_approved","created_date"]
        
    def validate_name(self, value):
        if Specialization.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("A specialization with this name already exists.")
        return value
