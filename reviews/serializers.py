from rest_framework import serializers
from .models import Review

class ReviewSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['id', 'patient_name','doctor_name', 'rating', 'content', 'recommend', 'reply', 'created_at']

    def get_patient_name(self, obj):
        return obj.patient.user.first_name
    
    def get_doctor_name(self, obj):
        # Fetch the doctor's name from the User model
        return obj.doctor.user.first_name