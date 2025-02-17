from rest_framework import serializers
import os
import base64
from django.core.files.base import ContentFile
from .models import Education, Media, Skill, User

class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["name"]

class MediaSerializer(serializers.ModelSerializer):
    file = serializers.FileField()

    class Meta:
        model = Media
        fields = ["file"]

    def create(self, validated_data):
        return super().create(validated_data)

class EducationSerializer(serializers.ModelSerializer):
    skills = serializers.ListField(
        child=serializers.CharField(max_length=100), required=False
    )
    media = serializers.ImageField(required=False)

    class Meta:
        model = Education
        fields = [
            'id', 'school', 'degree', 'field_of_study', 'start_month_year', 'end_month_year',
            'grade', 'activities_and_societies', 'description', 'skills', 'media'
        ]
    
    def create(self, validated_data):
        media = validated_data.pop('media', None)
        # Create Education instance
        education = Education.objects.create(**validated_data)
        # If media exists, store it in the ImageField
        if media:
            education.media = media
            education.save()
        return education

    def update(self, instance, validated_data):
        media = validated_data.pop('media', None)
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # If media exists, update it
        if media:
            instance.media = media
            instance.save()
        return instance
    
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "email", "phone_number", "gender", "dob", "profile_picture", "bio", "country", "city", "residence", "role"
        ]