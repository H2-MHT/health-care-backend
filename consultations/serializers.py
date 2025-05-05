from rest_framework import serializers
from .models import Prescription

class PrescriptionSerializer(serializers.ModelSerializer):
    # notes = serializers.CharField(source='appointment.notes', read_only=False)

    class Meta:
        model = Prescription
        fields = ['medicines', 'diagnosis', 'additional_instruction']

    def update(self, instance, validated_data):
        # Update medicines, diagnosis, and additional instruction
        instance.medicines = validated_data.get('medicines', instance.medicines)
        instance.diagnosis = validated_data.get('diagnosis', instance.diagnosis)

        # appointment_data = validated_data.get('appointment', {})
        # if 'notes' in appointment_data:
        #     instance.appointment.notes = appointment_data['notes']
        #     instance.appointment.save()

        instance.save()
        return instance
