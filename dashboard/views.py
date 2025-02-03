from datetime import datetime

from django.db.models import Avg, Count
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from appointments.models import Appointment
from doctors.models import Doctor
from patients.models import MedicalHistory
from reviews.models import Review
from users.models import User
from patients.models import Patient
from datetime import timedelta
from appointments.models import Appointment
from doctors.models import DoctorNotes
from doctors.serializers import DoctorNotesSerializer

# Create your views here.


class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Ensure only doctors can access this view
        if request.user.role != "Doctor":
            return Response({"error": "Access restricted to doctors only."}, status=403)

        # Get the doctor associated with the current authenticated user
        try:
            doctor = Doctor.objects.get(user=request.user)
        except Doctor.DoesNotExist:
            return Response({"error": "Doctor profile not found."}, status=404)

        # Reviews Data
        total_reviews = Review.objects.filter(doctor=doctor).count()
        reviews = Review.objects.filter(doctor=doctor).select_related("patient__user", "doctor__user")[:10]
        reviews_data = [
            {
                "patient_name": f"{review.patient.user.first_name} {review.patient.user.last_name}",
                "doctor_name": f"{review.doctor.user.first_name} {review.doctor.user.last_name}",
                "rating": review.rating,
                "content": review.content,
                "recommend": review.recommend,
                "created_at": review.created_at.isoformat(),
            }
            for review in reviews
        ]

        # Appointments Data
        appointments = Appointment.objects.filter(doctor=doctor).select_related("patient__user", "doctor__user", "clinic")[:10]
        appointments_data = [
            {
                "appointment_id": appointment.id,
                "patient_id": appointment.patient.id,
                "patient_name": f"{appointment.patient.user.first_name} {appointment.patient.user.last_name}",
                "doctor_name": f"{appointment.doctor.user.first_name} {appointment.doctor.user.last_name}",
                "clinic": appointment.clinic.name,
                "date_time": appointment.date_time.isoformat(),
                "status": appointment.status,
            }
            for appointment in appointments
        ]
        
        # Archived and Confirmed Appointments
        archived_appointments = Appointment.objects.filter(doctor=doctor, status="Archived").values(
            "patient__user__first_name",
            "patient__user__last_name",
            "doctor__user__first_name",
            "doctor__user__last_name",
            "clinic__name",
            "date_time",
            "status"
        )

        confirmed_appointments = Appointment.objects.filter(doctor=doctor, status="Confirmed").values(
            "patient__user__first_name",
            "patient__user__last_name",
            "doctor__user__first_name",
            "doctor__user__last_name",
            "clinic__name",
            "date_time",
            "status"
        )

        def format_appointment_data(appointments):
            return [
                {
                    "patient_name": f"{appt['patient__user__first_name']} {appt['patient__user__last_name']}",
                    "doctor_name": f"{appt['doctor__user__first_name']} {appt['doctor__user__last_name']}",
                    "clinic": appt["clinic__name"],
                    "date": appt["date_time"].isoformat(),
                    "status": appt["status"],
                }
                for appt in appointments
            ]

        archived_data = format_appointment_data(archived_appointments)
        confirmed_data = format_appointment_data(confirmed_appointments)

        # Doctor Notes
        doctor_notes = DoctorNotes.objects.filter(doctor=doctor).order_by('-created_at')
        doctor_notes_serializer = DoctorNotesSerializer(doctor_notes, many=True)
        doctor_notes_data = doctor_notes_serializer.data
            
        # Diagnoses Data
        diagnoses = MedicalHistory.objects.filter(patient__appointment__doctor=doctor).select_related("patient__user")[:5]
        diagnoses_data = [
            {
                "doctor_name": f"Dr. {doctor.user.first_name} {doctor.user.last_name}",
                "patient_name": f"{history.patient.user.first_name} {history.patient.user.last_name}",
                "condition": history.condition,
                "diagnosis_date": history.diagnosis_date.isoformat() if history.diagnosis_date else None,
                "notes": history.notes,
            }
            for history in diagnoses
        ]

        # Last Reports for Patients
        patients = Patient.objects.filter(appointment__doctor=doctor).distinct()
        last_reports_data = []
        for patient in patients:
            last_diagnosis = MedicalHistory.objects.filter(patient=patient).order_by("-diagnosis_date").first()
            last_reports_data.append(
                {
                    "patient_name": f"{patient.user.first_name} {patient.user.last_name}",
                    "condition": last_diagnosis.condition if last_diagnosis else "No Diagnosis",
                    "diagnosis_date": last_diagnosis.diagnosis_date.strftime("%d-%m-%Y") if last_diagnosis and last_diagnosis.diagnosis_date else None,
                    "time": f"{last_diagnosis.diagnosis_date.strftime('%H:%M')} - {last_diagnosis.diagnosis_date.strftime('%H:%M')}" if last_diagnosis and last_diagnosis.diagnosis_date else None,
                    "notes": last_diagnosis.notes if last_diagnosis else "No Notes",
                    "status": last_diagnosis.status if last_diagnosis and hasattr(last_diagnosis, "status") else "Unknown",
                }
            )

        # Statistics
        total_consultations = Appointment.objects.filter(doctor=doctor).count()
        total_clients = patients.count()
        returns_percentage = round((total_clients / total_consultations) * 100 if total_consultations else 0, 2)

        # Final Response
        data = {
            "total_reviews": total_reviews,
            "reviews": reviews_data,
            "appointments": appointments_data,
            "doctor_notes": doctor_notes_data,
            "patient_diagnoses": diagnoses_data,
            "archived_data": archived_data,
            "confirmed_data": confirmed_data,
            "last_report": last_reports_data,
            "total_consultations": total_consultations,
            "total_clients": total_clients,
            "returns_percentage": returns_percentage,
        }

        return Response(data)
    
    
    