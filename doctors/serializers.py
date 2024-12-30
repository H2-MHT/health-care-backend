from rest_framework import serializers
from users.models import User
from .models import DoctorNotes

class DoctorNotesSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()

    class Meta:
        model = DoctorNotes
        fields = ['id', 'patient', 'title', 'note', 'patient_name', 'doctor_name', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}"

    def get_doctor_name(self, obj):
        return f"{obj.doctor.first_name} {obj.doctor.last_name}"
