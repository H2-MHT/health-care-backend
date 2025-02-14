from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import PatientUserSerializer
from rest_framework.permissions import IsAuthenticated
from appointments.models import Appointment
# Create your views here.

class PatientListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        appointments = Appointment.objects.filter(doctor__user=request.user)
        # empty list for patients
        patients = []
        for appointment in appointments:
            if appointment.patient.user.role == 'Patient':
                patients.append(appointment.patient.user)
        serializer = PatientUserSerializer(patients, many=True)
        return Response({
            "total_assigned_patients": len(patients),
            "assigned_patients": serializer.data
        })