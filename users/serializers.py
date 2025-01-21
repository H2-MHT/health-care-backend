from rest_framework import serializers

from .models import Education, Media, Skill, User


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["id", "name"]


class MediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Media
        fields = ["id", "file", "description"]


class EducationSerializer(serializers.ModelSerializer):
    skills = SkillSerializer(many=True)
    media = MediaSerializer(many=True)

    class Meta:
        model = Education
        fields = [
            "id",
            "school",
            "degree",
            "field_of_study",
            "start_date",
            "end_date",
            "grade",
            "activities_and_societies",
            "description",
            "skills",
            "media",
        ]

    def create(self, validated_data):
        skills_data = validated_data.pop("skills", [])
        media_data = validated_data.pop("media", [])

        # Create the Education instance
        education = Education.objects.create(**validated_data)

        # Create or get Skill instances
        for skill_data in skills_data:
            skill, _ = Skill.objects.get_or_create(**skill_data)
            education.skills.add(skill)

        # Create Media instances
        for media_item in media_data:
            media = Media.objects.create(**media_item)
            education.media.add(media)

        return education


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "email", "phone_number", "gender", "dob", "profile_picture", "bio", "country", "city", "residence", "role"
        ]