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

# Create your views here.


class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Reviews Data
        total_reviews = Review.objects.count()
        reviews = Review.objects.select_related("patient__user", "doctor__user")[:10]
        reviews_data = [
            {
                "patient": f"{review.patient.user.first_name} {review.patient.user.last_name}",
                "doctor": f"{review.doctor.user.first_name} {review.doctor.user.last_name}",
                "rating": review.rating,
                "content": review.content,
                "recommend": review.recommend,
                "reply": review.reply,
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
                "id": appointment.id,
                "patient": f"{appointment.patient.user.first_name} {appointment.patient.user.last_name}",
                "doctor": f"{appointment.doctor.user.first_name} {appointment.doctor.user.last_name}",
                "clinic": appointment.clinic.name,
                "date_time": appointment.date_time.isoformat(),
                "status": appointment.status,
            }
            for appointment in appointments
        ]

        # Doctor Notes Data (Example placeholder notes)
        doctor_notes = [
            {
                "doctor": f"Dr. {doctor.user.first_name} {doctor.user.last_name}",
                "note": "Sample note for patient follow-up",
                "date": datetime.now().isoformat(),
            }
            for doctor in Doctor.objects.all()[:5]
        ]

        # Patient Diagnoses
        diagnoses = MedicalHistory.objects.select_related("patient__user")[:5]
        diagnoses_data = [
            {
                "patient": f"{history.patient.user.first_name} {history.patient.user.last_name}",
                "condition": history.condition,
                "diagnosis_date": (
                    history.diagnosis_date.isoformat()
                    if history.diagnosis_date
                    else None
                ),
                "notes": history.notes,
            }
            for history in diagnoses
        ]

        # Statistics
        total_consultations = Appointment.objects.count()
        total_clients = User.objects.filter(role="Patient").count()
        returns_percentage = round(
            (total_consultations / total_clients) * 100 if total_clients else 0, 2
        )

        # Final Response
        data = {
            "total_reviews": total_reviews,
            "reviews": reviews_data,
            "appointments": appointments_data,
            "doctor_notes": doctor_notes,
            "patient_diagnoses": diagnoses_data,
            "total_consultations": total_consultations,
            "total_clients": total_clients,
            "returns_percentage": returns_percentage,
        }

        return Response(data)
