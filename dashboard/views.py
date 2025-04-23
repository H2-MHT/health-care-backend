from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from appointments.models import Appointment
from doctors.models import Doctor
from patients.models import DashboardMedicalHistory
from reviews.models import Review
from users.models import User
from patients.models import Patient
from datetime import timedelta
from doctors.models import BookedAppointment
from django.utils import timezone
from rest_framework import status
from users.models import Notes
from users.serializers import NotesSerializer
from datetime import datetime
# Create your views here.

class DashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            if request.user.role != "Doctor":
                return Response({"error": "Access restricted to doctors only."}, status=403)

            try:
                doctor = Doctor.objects.get(user=request.user)
            except Doctor.DoesNotExist:
                return Response({"error": "Doctor profile not found."}, status=404)
            
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            try:
                converted_start_date = datetime.strptime(start_date, '%d-%m-%Y').date()
                converted_end_date = datetime.strptime(end_date, '%d-%m-%Y').date()
            except ValueError:
                return Response({"error": "Invalid date format. Expected DD-MM-YYYY."}, status=400)
            # Reviews
            total_reviews = Review.objects.filter(doctor=doctor).count()
            reviews = Review.objects.filter(doctor=doctor).select_related("patient__user", "doctor__user")[:10]
            reviews_data = [
                {
                    "doctor_id": review.doctor.id,
                    "patient_name": f"{review.patient.user.first_name} {review.patient.user.last_name}",
                    "doctor_name": f"{review.doctor.user.first_name} {review.doctor.user.last_name}",
                    "rating": review.rating,
                    "content": review.content,
                    "recommend": review.recommend,
                    "created_at": review.created_at.isoformat(),
                }
                for review in reviews
            ]

            # Appointments
            appointments = BookedAppointment.objects.filter(doctor=request.user.id, date__gte=converted_start_date, date__lte=converted_end_date).order_by("date")[:10]
            appointment_data = []
            for appointment in appointments:
                doc = User.objects.filter(pk=appointment.doctor).first()
                pat = User.objects.filter(pk=appointment.patient).first()
                appointment_data.append(
                    {
                        "appointment_id": appointment.id,
                        "doctor_id": doc.id if doc else None,
                        "doctor_name": f"{doc.first_name} {doc.last_name}" if doc else "Unknown",
                        "patient_id": pat.id if pat else None,
                        "patient_name": f"{pat.first_name} {pat.last_name}" if pat else "Unknown",
                        "date": appointment.date,
                        "slot": appointment.slot,
                        "status": appointment.status,
                    }
                )

            # Upcoming Requests
            upcoming_requests = BookedAppointment.objects.filter(
                doctor=request.user.id,
                date__gte=timezone.now().date(),
            ).exclude(status="Completed").order_by("date")[:10]
            upcoming_requests_data = []
            for appt in upcoming_requests:
                doc = User.objects.filter(pk=appt.doctor).first()
                pat = User.objects.filter(pk=appt.patient).first()
                upcoming_requests_data.append(
                    {
                        "appointment_id": appt.id,
                        "doctor_id": doc.id if doc else None,
                        "doctor_name": f"{doc.first_name} {doc.last_name}" if doc else "Unknown",
                        "patient_id": pat.id if pat else None,
                        "patient_name": f"{pat.first_name} {pat.last_name}" if pat else "Unknown",
                        "date": appt.date,
                        "slot": appt.slot,
                        "status": appt.status,
                    }
                )

            # Archived Appointments
            archived_appointments = BookedAppointment.objects.filter(
                doctor=request.user.id, status="Cancelled",
                date__gte=converted_start_date, date__lte=converted_end_date
            ).order_by("date")
            archived_data = []
            for appt in archived_appointments:
                pat = User.objects.filter(pk=appt.patient).first()
                doc = User.objects.filter(pk=appt.doctor).first()
                archived_data.append({
                    "appointment_id": appt.id,
                    "patient_name": f"{pat.first_name} {pat.last_name}" if pat else "Unknown",
                    "doctor_name": f"{doc.first_name} {doc.last_name}" if doc else "Unknown",
                    "date": appt.date.isoformat() if appt.date else None,
                    "slot": appt.slot,
                    "status": appt.status,
                })

            # Confirmed Appointments
            confirmed_appointments = BookedAppointment.objects.filter(
                doctor=request.user.id, status="Confirmed",
                date__gte=converted_start_date, date__lte=converted_end_date
            ).order_by("date")
                
            confirmed_data = []
            for appt in confirmed_appointments:
                pat = User.objects.filter(pk=appt.patient).first()
                doc = User.objects.filter(pk=appt.doctor).first()
                confirmed_data.append({
                    "appointment_id": appt.id,
                    "patient_name": f"{pat.first_name} {pat.last_name}" if pat else "Unknown",
                    "doctor_name": f"{doc.first_name} {doc.last_name}" if doc else "Unknown",
                    "date": appt.date.isoformat() if appt.date else None,
                    "slot": appt.slot,
                    "status": appt.status,
                })



            # Doctor Notes
            doctor_notes = Notes.objects.filter(user=request.user, user__role="Doctor").order_by('-created_at')
            doctor_notes_data = NotesSerializer(doctor_notes, many=True).data

            # Patient Diagnoses
            patients = Patient.objects.filter(appointment__doctor=doctor).distinct()
            diagnoses = DashboardMedicalHistory.objects.filter(patient__in=patients).select_related("patient__user")[:5]
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

            # Last Report for Patients
            last_reports_data = []
            for patient in patients:
                last_diagnosis = DashboardMedicalHistory.objects.filter(patient=patient).order_by("-diagnosis_date").first()
                last_reports_data.append(
                    {
                        "patient_name": f"{patient.user.first_name} {patient.user.last_name}",
                        "diagnosis_date": last_diagnosis.diagnosis_date.strftime("%d-%m-%Y") if last_diagnosis and last_diagnosis.diagnosis_date else None,
                        "time": f"{last_diagnosis.diagnosis_date.strftime('%H:%M')} - {last_diagnosis.diagnosis_date.strftime('%H:%M')}" if last_diagnosis and last_diagnosis.diagnosis_date else None,
                        "notes": last_diagnosis.notes if last_diagnosis else "No Notes",
                        "status": getattr(last_diagnosis, "status", "Unknown"),
                    }
                )

            # Stats
            total_consultations = BookedAppointment.objects.filter(doctor=request.user.id).count()
            patient_ids = BookedAppointment.objects.filter(doctor=request.user.id).values_list('patient', flat=True).distinct()
            total_clients = patient_ids.count()
            returns_percentage = round((total_clients / total_consultations) * 100 if total_consultations else 0, 2)

            # Final Response
            data = {
                "doctor_id": doctor.id,
                "total_reviews": total_reviews,
                "reviews": reviews_data,
                "appointments": appointment_data,
                "confirmed_data": confirmed_data,
                "upcoming_requests": upcoming_requests_data,
                "archived_data": archived_data,
                "doctor_notes": doctor_notes_data,
                "patient_diagnoses": diagnoses_data,
                "last_report": last_reports_data,
                "total_consultations": total_consultations,
                "total_clients": total_clients,
                "returns_percentage": returns_percentage,
            }

            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=400)