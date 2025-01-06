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

# Create your views here.


class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Reviews Data
        total_reviews = Review.objects.count()
        reviews = Review.objects.select_related("patient__user", "doctor__user")[:10]
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
        appointments = Appointment.objects.select_related(
            "patient__user", "doctor__user", "clinic"
        )[:10]
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
        
        # Filter for archived appointments
        archived_appointments = Appointment.objects.filter(status="Archived").values(
            "patient__user__first_name",
            "patient__user__last_name",
            "doctor__user__first_name",
            "doctor__user__last_name",
            "clinic__name",
            "date_time",
            "status"
        )

        # Filter for confirmed appointments
        confirmed_appointments = Appointment.objects.filter(status="Confirmed").values(
            "patient__user__first_name",
            "patient__user__last_name",
            "doctor__user__first_name",
            "doctor__user__last_name",
            "clinic__name",
            "date_time",
            "status"
        )

        # Format the results with required date and time formatting
        def format_appointment_data(appointments):
            return [
                {
                    "patient_name": f"{appt['patient__user__first_name']} {appt['patient__user__last_name']}",
                    "doctor_name": f"{appt['doctor__user__first_name']} {appt['doctor__user__last_name']}",
                    "clinic": appt["clinic__name"],
                    "date": appt["date_time"].strftime("%d-%m-%Y"),
                    "time": f"{appt['date_time'].strftime('%H:%M')} - {(appt['date_time'] + timedelta(minutes=30)).strftime('%H:%M')}",
                    "status": appt["status"],
                }
                for appt in appointments
            ]

        # Process archived and confirmed appointments
        archived_data = format_appointment_data(archived_appointments)
        confirmed_data = format_appointment_data(confirmed_appointments)

        # Doctor Notes Data (Example placeholder notes)
        doctor_notes = [
            {
                "doctor_name": f"Dr. {doctor.user.first_name} {doctor.user.last_name}",
                "note": "Sample note for patient follow-up",
                "date": datetime.now().isoformat(),
            }
            for doctor in Doctor.objects.all()[:5]
        ]

        # Patient Diagnoses
        diagnoses = MedicalHistory.objects.select_related("patient__user")[:5]
        diagnoses_data = [
            {
                "doctor_name": f"Dr. {doctor.user.first_name} {doctor.user.last_name}",
                "patient_name": f"{history.patient.user.first_name} {history.patient.user.last_name}",
                "condition": history.condition,
                "diagnosis_date": (
                    history.diagnosis_date.isoformat()
                    if history.diagnosis_date
                    else None
                ),
                "notes": history.notes,
            }
            for doctor in Doctor.objects.all()[:5]
            for history in diagnoses
        ]
        
        # Last Reports for Patients from MedicalHistory
        patients = Patient.objects.all()
        last_reports_data = []
        for patient in patients:
            last_diagnosis = (
                MedicalHistory.objects.filter(patient=patient)
                .order_by("-diagnosis_date")
                .first()
            )
            last_reports_data.append(
                {
                    "patient_name": f"{patient.user.first_name} {patient.user.last_name}",
                    "condition": last_diagnosis.condition if last_diagnosis else "No Diagnosis",
                    "diagnosis_date": (
                        last_diagnosis.diagnosis_date.strftime("%d-%m-%Y")
                        if last_diagnosis and last_diagnosis.diagnosis_date
                        else None
                    ),
                    "time": (
                        f"{last_diagnosis.diagnosis_date.strftime('%H:%M')} - {last_diagnosis.diagnosis_date.strftime('%H:%M')}"
                        if last_diagnosis and last_diagnosis.diagnosis_date
                        else None
                    ),
                    "notes": last_diagnosis.notes if last_diagnosis else "No Notes",
                    "status": last_diagnosis.status
                    if last_diagnosis and hasattr(last_diagnosis, "status")
                    else "Unknown",
                }
            )

        # Statistics
        total_consultations = Appointment.objects.count()
        total_clients = User.objects.filter(role="Patient").count()
        returns_percentage = round(
            (total_clients / total_consultations) * 100 if total_clients else 0, 2
        )

        # Final Response
        data = {
            "total_reviews": total_reviews,
            "reviews": reviews_data,
            "appointments": appointments_data,
            "doctor_notes": doctor_notes,
            "patient_diagnoses": diagnoses_data,
            "archived_data": archived_data,
            "confirmed_data": confirmed_data,
            "last_report": last_reports_data,
            "total_consultations": total_consultations,
            "total_clients": total_clients,
            "returns_percentage": returns_percentage,
        }

        return Response(data)
