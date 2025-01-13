from rest_framework import serializers
from users.models import User
from .models import DoctorNotes

class DoctorNotesSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorNotes
        fields = ['id', 'title', 'note', 'created_at']
        read_only_fields = ['id', 'created_at', 'doctor']

    def create(self, validated_data):
        # Automatically set the doctor to the logged-in user
        request = self.context.get('request')
        validated_data['doctor'] = request.user
        return super().create(validated_data)