import logging
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import(
    PatientUserSerializer,
    MedicalDocumentSerializer,
    AllergyDocumentSerializer,
    FavouriteSerializer,
)
from sendgrid import SendGridAPIClient

from sendgrid.helpers.mail import Mail

from rest_framework.permissions import IsAuthenticated
from appointments.models import Appointment
from rest_framework import status
from .models import *
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from users.models import Notes
from clinics.models import Clinic
from doctors.models import Doctor
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction


# Create your views here.
logger = logging.getLogger(__name__)


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
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MedicalDocumentUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        # Get the patient linked to the logged-in user
        try:
            patient = Patient.objects.get(user=request.user)
        except Patient.DoesNotExist:
            return Response({"error": "Patient profile not found"}, status=status.HTTP_404_NOT_FOUND)

        # Serialize the data
        serializer = MedicalDocumentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(patient=patient)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AllergyDocumentUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        # Get the patient linked to the logged-in user
        try:
            patient = Patient.objects.get(user=request.user)
        except Patient.DoesNotExist:
            return Response({"error": "Patient profile not found"}, status=status.HTTP_404_NOT_FOUND)

        # Serialize the data
        serializer = AllergyDocumentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(patient=patient)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            

class AddToFavouriteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """ Add a doctor or clinic to favorites """
        try:
            patient = request.user.patient_profile
        except AttributeError:
            return Response({"error": "You are not registered as a patient."}, status=status.HTTP_400_BAD_REQUEST)

        fav_doc_id = request.data.get("fav_doc")
        fav_clinic_id = request.data.get("fav_clinic")

        if not fav_doc_id and not fav_clinic_id:
            return Response({"error": "Provide a doctor or clinic to add to favorites."}, status=status.HTTP_400_BAD_REQUEST)

        if fav_doc_id:
            try:
                doctor = Doctor.objects.get(id=fav_doc_id)
            except Doctor.DoesNotExist:
                return Response({"error": "Doctor not found."}, status=status.HTTP_404_NOT_FOUND)

            favourite, created = Favourite.objects.get_or_create(patient=patient, fav_doc=doctor)
            favourite.doc_status = True
            favourite.save()

            return Response({"message": "Doctor added to favorites!", "data": FavouriteSerializer(favourite).data}, status=status.HTTP_201_CREATED)

        if fav_clinic_id:
            try:
                clinic = Clinic.objects.get(id=fav_clinic_id)
            except Clinic.DoesNotExist:
                return Response({"error": "Clinic not found."}, status=status.HTTP_404_NOT_FOUND)

            favourite, created = Favourite.objects.get_or_create(patient=patient, fav_clinic=clinic)
            favourite.clinic_status = True
            favourite.save()

            return Response({"message": "Clinic added to favorites!", "data": FavouriteSerializer(favourite).data}, status=status.HTTP_201_CREATED)

    def get(self, request):
        """ Get all favorite doctors and clinics for the logged-in patient """
        try:
            patient = request.user.patient_profile
        except AttributeError:
            return Response({"error": "You are not registered as a patient."}, status=status.HTTP_400_BAD_REQUEST)

        favourites = Favourite.objects.filter(patient=patient)

        if not favourites.exists():
            return Response({"message": "No favorites found."}, status=status.HTTP_404_NOT_FOUND)

        serialized_favourites = FavouriteSerializer(favourites, many=True)
        return Response({"favorites": serialized_favourites.data}, status=status.HTTP_200_OK)

    def delete(self, request):
        """ Remove a doctor or clinic from favorites """
        try:
            patient = request.user.patient_profile
        except AttributeError:
            return Response({"error": "You are not registered as a patient."}, status=status.HTTP_400_BAD_REQUEST)

        fav_doc_id = request.data.get("fav_doc")
        fav_clinic_id = request.data.get("fav_clinic")

        if not fav_doc_id and not fav_clinic_id:
            return Response({"error": "Provide a doctor or clinic to remove from favorites."}, status=status.HTTP_400_BAD_REQUEST)

        if fav_doc_id:
            try:
                favourite = Favourite.objects.get(patient=patient, fav_doc_id=fav_doc_id)
                favourite.delete()
                return Response({"message": "Doctor removed from favorites."}, status=status.HTTP_200_OK)
            except Favourite.DoesNotExist:
                return Response({"error": "Doctor favorite entry not found."}, status=status.HTTP_404_NOT_FOUND)

        if fav_clinic_id:
            try:
                favourite = Favourite.objects.get(patient=patient, fav_clinic_id=fav_clinic_id)
                favourite.delete()
                return Response({"message": "Clinic removed from favorites."}, status=status.HTTP_200_OK)
            except Favourite.DoesNotExist:
                return Response({"error": "Clinic favorite entry not found."}, status=status.HTTP_404_NOT_FOUND)
            
class AddFamilyMemberView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        patient = get_object_or_404(Patient, user=request.user)

        member_name = request.data.get("member_name")
        member_email = request.data.get("member_email")
        family_status = request.data.get("family_status")
        member_profile = request.FILES.get("member_profile")

        if not (member_name and member_email and family_status):
            return Response({"error": "All fields are required except profile picture."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            family_member = FamilyMember.objects.create(
                patient=patient,
                member_name=member_name,
                member_email=member_email,
                family_status=family_status,
                member_profile=member_profile
            )

            # Generate OTP
            otp_code = OTPVerification.generate_otp()
            print(f"Generated OTP: {otp_code} for {member_email}")

            # Save OTP to the database
            otp_entry = OTPVerification.objects.create(family_member=family_member, otp=otp_code)
            print(f"Saved OTP: {otp_entry.otp} for FamilyMember ID: {family_member.id}")

        # Send OTP via email
        self.send_otp_email(member_email, member_name, family_status, otp_code)

        return Response({"message": "Family member added. OTP sent for verification."}, status=status.HTTP_201_CREATED)

    def send_otp_email(self, to_email, member_name, family_status, otp_code):
        """Send OTP email using SendGrid"""
        subject = "Family Member Verification"
        message_content = f"""
        Hello,

        Your OTP for verifying {member_name} ({family_status}) is: {otp_code}

        Please enter this OTP in the application to verify the family member.

        """

        email = Mail(
            from_email=settings.SENDGRID_FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            plain_text_content=message_content
        )

        try:
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            response = sg.send(email)
            print(f"SendGrid Response: {response.status_code}")
        except Exception as e:
            print(f"SendGrid Error: {e}")


class VerifyFamilyMemberOTPAPIView(APIView):
    def post(self, request):
        member_email = request.data.get("member_email")
        otp_code = request.data.get("otp")

        if not (member_email and otp_code):
            return Response({"error": "Email and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)

        family_member = FamilyMember.objects.filter(member_email=member_email, is_verified=False).order_by('-id').first()

        if not family_member:
            return Response({"error": "Family member not found or already verified."}, status=status.HTTP_404_NOT_FOUND)

        # Get the latest OTP
        otp_entry = OTPVerification.objects.filter(family_member=family_member).order_by('-created_at').first()

        if not otp_entry:
            return Response({"error": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate OTP
        if str(otp_entry.otp).strip() != str(otp_code).strip():
            print(f"Entered OTP: {otp_code}, Expected OTP: {otp_entry.otp}")
            return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

        # Mark the family member verified
        family_member.is_verified = True
        family_member.save()

        # Delete OTP entry after successful verification
        otp_entry.delete()

        return Response({"message": "Family member verified successfully."}, status=status.HTTP_200_OK)
