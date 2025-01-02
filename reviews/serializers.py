from rest_framework import serializers
from .models import Review, Reply
from patients.models import Patient

from appointments.models import Appointment

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['id', 'doctor', 'rating', 'content', 'recommend', 'created_at']
        # read_only_fields = ['reply', 'created_at']

    def validate(self, data):
        request = self.context.get('request')
        user = request.user

        # Ensure the user is a patient
        if not hasattr(user, 'patient'):
            raise serializers.ValidationError("Only patients can create reviews.")

        patient = user.patient
        doctor = data.get('doctor')

        # Ensure the doctor is assigned to the patient via an active appointment
        if not Appointment.objects.filter(patient=patient, doctor=doctor, status__in=["Pending", "Confirmed", "Completed"]).exists():
            raise serializers.ValidationError(
                {"doctor": "This doctor is not assigned to the logged-in patient through an appointment."}
            )
        return data
    

class ReplySerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()  # To show user (patient/doctor)
    parent_reply = serializers.PrimaryKeyRelatedField(queryset=Reply.objects.all(), required=False)

    class Meta:
        model = Reply
        fields = ['id', 'user', 'content', 'created_at', 'parent_reply']


# class ReviewSerializer(serializers.ModelSerializer):
#     patient_name = serializers.SerializerMethodField()
#     doctor_name = serializers.SerializerMethodField()

#     class Meta:
#         model = Review
#         fields = ['id', 'patient_name','doctor_name', 'rating', 'content', 'recommend', 'reply', 'created_at']

#     def get_patient_name(self, obj):
#         return obj.patient.user.first_name
    
#     def get_doctor_name(self, obj):
#         # Fetch the doctor's name from the User model
#         return obj.doctor.user.first_name