from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import PatientUserSerializer
from rest_framework.permissions import IsAuthenticated
from appointments.models import Appointment
from rest_framework import status
from .models import Patient
from django.utils import timezone
from users.models import Notes

# Create your views here.


class PatientDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Ensure only patients can access this view
            if request.user.role != "Patient":
                return Response({"error": "Access restricted to patients only."}, status=403)

            # Fetch the patient profile
            try:
                patient = Patient.objects.get(user=request.user)
            except Patient.DoesNotExist:
                return Response({"error": "Patient profile not found."}, status=404)

            # Get patient details
            patient_data = {
                "patient_id": patient.id,
                "patient_name": f"{request.user.first_name} {request.user.last_name}",
            }

            # Fetch patient-created notes
            patient_notes = Notes.objects.filter(user=request.user)
            notes_data = [
                {
                    "note_id": note.id,
                    "title": note.title,
                    "note": note.note,
                    "created_at": note.created_at.isoformat(),
                }
                for note in patient_notes
            ]

            # Completed Appointments (Confirmed & Completed)
            completed_appointments = Appointment.objects.filter(
                patient=patient, status__in=["Confirmed", "Completed"]
            ).select_related("doctor__user", "clinic")

            completed_data = [
                {
                    "appointment_id": appt.id,
                    "doctor_name": f"{appt.doctor.user.first_name} {appt.doctor.user.last_name}",
                    "clinic": appt.clinic.user.first_name if appt.clinic and appt.clinic.user else "N/A",
                    "date_time": appt.date_time.isoformat(),
                    "status": appt.status,
                    "records": appt.records,
                    "notes": appt.notes,
                }
                for appt in completed_appointments
            ]

            # Upcoming Requests (Future Pending Appointments)
            upcoming_appointments = Appointment.objects.filter(
                patient=patient,
                date_time__gte=timezone.now(),  # Future appointments
                status="Pending"
            ).select_related("doctor__user", "clinic")

            upcoming_data = [
                {
                    "appointment_id": appt.id,
                    "doctor_name": f"{appt.doctor.user.first_name} {appt.doctor.user.last_name}",
                    "clinic": appt.clinic.user.first_name if appt.clinic and appt.clinic.user else "N/A",
                    "date_time": appt.date_time.isoformat(),
                    "status": appt.status,
                }
                for appt in upcoming_appointments
            ]

            # Archived Appointments
            archived_appointments = Appointment.objects.filter(
                patient=patient, status__in=["Archived", "Cancelled"]
            ).select_related("doctor__user", "clinic")

            archived_data = [
                {
                    "appointment_id": appt.id,
                    "doctor_name": f"{appt.doctor.user.first_name} {appt.doctor.user.last_name}",
                    "clinic": appt.clinic.user.first_name if appt.clinic and appt.clinic.user else "N/A",
                    "date_time": appt.date_time.isoformat(),
                    "status": appt.status,
                }
                for appt in archived_appointments
            ]

            return Response(
                {
                    "patient": patient_data,
                    "notes": notes_data,  # Only patient-created notes
                    "completed_appointments": completed_data,
                    "upcoming_appointments": upcoming_data,
                    "archived_appointments": archived_data,
                },
                status=200
            )

        except Exception as e:
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PatientListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
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
        except Exception as e:
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
            

