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
        def parse_datetime(date_str, time_str):
            try:
                combined_str = f"{date_str} {time_str}"
                return datetime.strptime(combined_str, "%d-%m-%Y %H:%M")
            except ValueError:
                raise ValueError("Invalid date or time format. Use DD-MM-YYYY for date and HH:mm for time.")

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
                "created_at": review.created_at.strftime("%d-%m-%Y %H:%M"),
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
                "date_time": appointment.date_time,
                "status": appointment.status,
            }
            for appointment in appointments
        ]

        # Filter for archived and confirmed appointments
        def format_appointment_data(appointments):
            return [
                {
                    "patient_name": f"{appt['patient__user__first_name']} {appt['patient__user__last_name']}",
                    "doctor_name": f"{appt['doctor__user__first_name']} {appt['doctor__user__last_name']}",
                    "clinic": appt["clinic__name"],
                    "date": appt["date_time"].strftime("%d-%m-%Y"),
                    "time": appt["date_time"].strftime("%H:%M"),
                    "status": appt["status"],
                }
                for appt in appointments
            ]

        archived_appointments = Appointment.objects.filter(status="Archived").values(
            "patient__user__first_name",
            "patient__user__last_name",
            "doctor__user__first_name",
            "doctor__user__last_name",
            "clinic__name",
            "date_time",
            "status"
        )

        confirmed_appointments = Appointment.objects.filter(status="Confirmed").values(
            "patient__user__first_name",
            "patient__user__last_name",
            "doctor__user__first_name",
            "doctor__user__last_name",
            "clinic__name",
            "date_time",
            "status"
        )

        archived_data = format_appointment_data(archived_appointments)
        confirmed_data = format_appointment_data(confirmed_appointments)

        # Final Response
        data = {
            "total_reviews": total_reviews,
            "reviews": reviews_data,
            "appointments": appointments_data,
            "archived_data": archived_data,
            "confirmed_data": confirmed_data,
        }

        return Response(data)
