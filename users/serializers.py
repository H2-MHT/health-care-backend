from rest_framework import serializers
import os
import base64
from django.core.files.base import ContentFile
from django.utils.timesince import timesince
from .models import (
    Education,
    Media,
    Skill,
    User,
    Notes,
    DeviceAccess,
    AppLanguage,
    Ticket,
    )
from doctors.models import ConsultationSessionAndFee
import pycountry
class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["id", "name"]

class MediaSerializer(serializers.ModelSerializer):

    class Meta:
        model = Media
        fields = ["id","file"]


class EducationSerializer(serializers.ModelSerializer):
    skills = serializers.PrimaryKeyRelatedField(
        queryset=Skill.objects.all(), many=True, required=False, write_only=True
    )

    media = MediaSerializer(many=True, required=False)

    class Meta:
        model = Education
        fields = [
            'id', 'school', 'degree', 'field_of_study', 'start_month_year', 'end_month_year',
            'grade', 'activities_and_societies', 'description', 'media', 'skills'
        ]


    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['skills'] = [skill.name for skill in instance.skills.all()]  # Return skill objects
        return data

    def create(self, validated_data):
        skills = validated_data.pop('skills', [])
        media_files = self.context['request'].FILES.getlist('media')

        # Create Education instance
        education = Education.objects.create(**validated_data)

        # Assign selected skills
        if skills:
            education.skills.set(skills)

        # If media exists, store it
        if media_files:
            for file in media_files:
                Media.objects.create(education=education, file=file)

        return education

    def update(self, instance, validated_data):
        skills = validated_data.pop('skills', None)
        media_files = self.context['request'].FILES.getlist('media')

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update skills only if provided
        if skills is not None:
            instance.skills.set(skills)

        # If media exists, update it
        if media_files:
            instance.media.all().delete()
            for file in media_files:
                Media.objects.create(education=instance, file=file)

        return instance

    
class UserSerializer(serializers.ModelSerializer):
    speciality = serializers.CharField(source="doctor.specialty", read_only=True)
    planned_hourly_rate = serializers.CharField(source="doctor.planned_hourly_rate", read_only=True)
    urgent_hourly_rate = serializers.CharField(source="doctor.urgent_hourly_rate", read_only=True)
    experience_years = serializers.IntegerField(source="doctor.experience_years", read_only=True)
    doctor_id = serializers.IntegerField(source="doctor.id", read_only=True)
    country_code = serializers.SerializerMethodField()
    stripe_link = serializers.CharField(source="doctor.stripe_link", read_only=True)
    class Meta:
        model = User
        fields = [
            "id", "doctor_id", "first_name", "last_name", "email", "phone_number", "gender", "dob", "profile_picture",
            "bio", "country", "country_code", "city", "residence", "languages", "role", "speciality", "rating",
            "planned_hourly_rate", "urgent_hourly_rate", "professional_stat", "experience_years","stripe_link"
        ]

    def get_planned_hourly_rate(self, obj):
        """Calculate planned hourly rate dynamically."""
        consultation = ConsultationSessionAndFee.objects.filter(doctor=obj.doctor).first()
        if consultation and consultation.planned_fees and consultation.planned_session_length:
            return round((consultation.planned_fees / consultation.planned_session_length) * 60, 2)
        return None

    def get_urgent_hourly_rate(self, obj):
        """Calculate urgent hourly rate dynamically."""
        consultation = ConsultationSessionAndFee.objects.filter(doctor=obj.doctor).first()
        if consultation and consultation.urgent_fees and consultation.urgent_session_length:
            return round((consultation.urgent_fees / consultation.urgent_session_length) * 60, 2)
        return None
    
    def get_country_code(self, obj):
        try:
            return pycountry.countries.get(name=obj.country).alpha_2
        except AttributeError:
            for country in pycountry.countries:
                if country.name.lower() == obj.country.lower():
                    return country.alpha_2
            return None
    
    def to_representation(self, instance):
        data = super().to_representation(instance)

        if data['stripe_link'] != None:
            data['stripe_link'] = True
        else:
            data['stripe_link'] = False

        return data


class NotesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notes
        fields = ["id", "title", "note", "created_at", "updated_at", "user"]
        read_only_fields = ["id", "created_at", "updated_at", "user"]
        

class DeviceAccessSerializer(serializers.ModelSerializer):
    logged_in_time = serializers.TimeField(format='%H:%M:%S')

    class Meta:
        model = DeviceAccess
        fields = '__all__'


class UserRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'role', 'is_doctor_switched']
        
class AppLanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppLanguage
        fields = ['language_name', 'code']

    def create(self, validated_data):
        user = self.context['request'].user

        # Clear existing languages for the user
        AppLanguage.objects.filter(user=user).delete()

        return AppLanguage.objects.create(
            user=user,
            language_name=validated_data['language_name'],
            code=validated_data['code'],
        )
        

class SupportTicketSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    class Meta:
        model = Ticket
        fields = ['ticket_id','title', 'description', 'attachment', 'status','admin_comment', "resolved_at", "created_at", "updated_at"]
        
    def get_status(self, obj):
        return obj.get_status_display()
        
class AdminSupportTicketSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    admin_comment = serializers.CharField(allow_blank=True, required=False)
    role = serializers.CharField(source='user.role', read_only=True, default="")
    status = serializers.ChoiceField(choices=Ticket.STATUS_CHOICES)
    attachment = serializers.FileField(required=False, allow_null=True)
    class Meta:
        model = Ticket
        fields = [
            'ticket_id', 'role','user_name', 'title', 'description', 'attachment',
            'status', 'admin_comment', 'resolved_at', 'created_at', 'updated_at'
        ]
        
    def to_representation(self, instance):
        # original key
        representation = super().to_representation(instance)
        # value of status key
        representation['status'] = instance.get_status_display()
        return representation
    
    def get_user_name(self, obj):
        first_name = obj.user.first_name or ""
        last_name = obj.user.last_name or ""
        full_name = f"{first_name} {last_name}".strip()
        return full_name if full_name else obj.user.email
    

