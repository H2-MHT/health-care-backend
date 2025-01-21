from rest_framework import serializers
import os
import base64
from django.core.files.base import ContentFile
from .models import Education, Media, Skill, User

class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["id", "name"]

class MediaSerializer(serializers.ModelSerializer):
    file = serializers.CharField()  # Accept file paths as strings

    class Meta:
        model = Media
        fields = ["id", "file"]

    def validate_file(self, value):
        # Check if the file exists
        if not os.path.exists(value):
            raise serializers.ValidationError(f"The file '{value}' does not exist.")
        return value

    def create(self, validated_data):
        file_path = validated_data["file"]
        # Read and encode the file as Base64
        with open(file_path, "rb") as f:
            file_data = f.read()
            ext = file_path.split(".")[-1]  # Get the file extension
            file_name = os.path.basename(file_path)  # Get the file name
        # Create a ContentFile object
        validated_data["file"] = ContentFile(
            base64.b64decode(base64.b64encode(file_data)), name=file_name
        )
        return super().create(validated_data)


class EducationSerializer(serializers.ModelSerializer):
    skills = SkillSerializer(many=True, required=False)
    media = MediaSerializer(many=True, required=False)  # Nested media input

    class Meta:
        model = Education
        fields = [
            'id',
            'school',
            'degree',
            'field_of_study',
            'start_month',
            'start_year',
            'end_month',
            'end_year',
            'grade',
            'activities_and_societies',
            'description',
            'skills',
            'media',
        ]

    def create(self, validated_data):
        skills_data = validated_data.pop('skills', [])
        media_data = validated_data.pop('media', [])
        education = Education.objects.create(**validated_data)

        # Add or create skills
        for skill_data in skills_data:
            skill, _ = Skill.objects.get_or_create(**skill_data)
            education.skills.add(skill)

        # Add or create media
        for media_item in media_data:
            media_serializer = MediaSerializer(data=media_item)
            if media_serializer.is_valid(raise_exception=True):
                media = media_serializer.save()
                education.media.add(media)
        return education

    def update(self, instance, validated_data):
        skills_data = validated_data.pop('skills', None)
        media_data = validated_data.pop('media', None)

        # Update fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update skills
        if skills_data is not None:
            instance.skills.clear()
            for skill_data in skills_data:
                skill, _ = Skill.objects.get_or_create(**skill_data)
                instance.skills.add(skill)
        # Update media
        if media_data is not None:
            instance.media.clear()
            for media_item in media_data:
                media_serializer = MediaSerializer(data=media_item)
                if media_serializer.is_valid(raise_exception=True):
                    media = media_serializer.save()
                    instance.media.add(media)
        return instance


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "email", "phone_number", "gender", "dob", "profile_picture", "bio", "country", "city", "residence", "role"
        ]