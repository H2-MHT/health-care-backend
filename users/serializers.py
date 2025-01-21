from rest_framework import serializers

from .models import Education, Media, Skill, User


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ["id", "name"]


class MediaSerializer(serializers.ModelSerializer):
    file = serializers.FileField()
    class Meta:
        model = Media
        fields = ["id", "file", "description"]


class EducationSerializer(serializers.ModelSerializer):
    skills = SkillSerializer(many=True, required=False)  # Allow nested skills input

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
        ]

    def create(self, validated_data):
        skills_data = validated_data.pop('skills', [])
        education = Education.objects.create(**validated_data)

        # Add or create skills
        for skill_data in skills_data:
            skill, _ = Skill.objects.get_or_create(**skill_data)
            education.skills.add(skill)

        return education

    def update(self, instance, validated_data):
        skills_data = validated_data.pop('skills', None)
        # Update all other fields in the Education model
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Handle the 'skills' field
        if skills_data is not None:
            # Clear existing skills before adding the new ones
            instance.skills.clear()
            # Add or create the new skills and associate them with the instance
            for skill_data in skills_data:
                skill, _ = Skill.objects.get_or_create(**skill_data)
                instance.skills.add(skill)
        return instance


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "email", "phone_number", "gender", "dob", "profile_picture", "bio", "country", "city", "residence", "role"
        ]