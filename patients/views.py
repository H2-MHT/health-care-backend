import logging

from rest_framework.decorators import permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from tinycss2 import serialize

from .serializers import(
    PatientUserSerializer,
    MedicalDocumentSerializer,
    AllergyDocumentSerializer,
    FavouriteSerializer,
    FavouriteDoctorSerializer,
    FavouriteClinicSerializer,
    ReminderSerializer,
)
from doctors.models import BookedAppointment
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
from utils.pagination import pagination_view, create_paginated_response
from .tasks import(
    send_email_reminder,
    send_whatsapp_reminder,
)
from datetime import timedelta, datetime
from users.serializers import UserSerializer
from doctors.serializers import DoctorSerializer
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
            # Get all patients who have an appointment with the logged-in doctor
            appointments = Appointment.objects.filter(doctor__user=request.user)

            patients_data = []
            for appointment in appointments:
                patient_user = appointment.patient.user  # Patient's User object
                if patient_user.role == "Patient":
                    patient_profile = appointment.patient  # Patient Profile (OneToOneField)
                    
                    # Prepare patient data, respecting privacy settings
                    patient_data = {
                        "appointment_id": appointment.id,
                        "first_name": patient_user.first_name,
                        "last_name": patient_user.last_name,
                        "profile_picture": patient_user.profile_picture.url if patient_user.profile_picture else None,
                        "bio": patient_user.bio,
                        "city": patient_user.city,
                        "country": patient_user.country,
                    }

                    # Include email & phone only if patient has allowed it
                    if patient_profile.show_email:
                        patient_data["email"] = patient_user.email
                    if patient_profile.show_phone:
                        patient_data["phone_number"] = patient_user.phone_number

                    patients_data.append(patient_data)

            return Response({
                "total_assigned_patients": len(patients_data),
                "assigned_patients": patients_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class MedicalDocumentUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            serializer = MedicalDocumentSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(patient=request.user)
                return Response({"message": "Document Added Successfully", "data": serializer.data}, status=status.HTTP_201_CREATED)
            return Response({"message": "Validation Error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def get(self, request):
        """
        Retrieve all medical documents associated with the current logged-in patient.

        Returns:
            Response: A response with a 200 status if the documents are retrieved
                    successfully, or a 400 status if an unexpected error occurs.

        Raises:
            Exception: If an unexpected error occurs.
        """

        try:
            medical_documents = MedicalHistory.objects.filter(patient=request.user)
            if not medical_documents.exists():
                return Response({"message": "No medical documents found", "data": []}, status=status.HTTP_200_OK)
            serializer = MedicalDocumentSerializer(medical_documents, many=True)
            return Response({"message": "Documents Retrieved Successfully", "data": serializer.data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        """
        Update a medical document.

        Parameters:
            request (Request): The request object.
            pk (int): The primary key of the document to update.

        Returns:
            Response: A response with a 200 status if the document is updated
                    successfully, or a 400 status if the request is invalid.

        Raises:
            Exception: If an unexpected error occurs.
        """
        try:
            try:
                medical_document = MedicalHistory.objects.get(pk=pk)
            except MedicalHistory.DoesNotExist:
                return Response({"message": "Document not found"}, status=status.HTTP_404_NOT_FOUND)
            serializer = MedicalDocumentSerializer(instance=medical_document, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({"message": "Document Updated Successfully", "data": serializer.data}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def delete(self, request, pk):
        """
        Delete a medical document.

        Parameters:
            request (Request): The request object.
            pk (int): The primary key of the document to delete.

        Returns:
            Response: A response with a 200 status if the document is deleted
                    successfully, or a 404 status if the document is not found.

        Raises:
            Exception: If an unexpected error occurs.
        """

        try:
            try:
                medical_document = MedicalHistory.objects.get(pk=pk)
            except MedicalHistory.DoesNotExist:
                return Response({"message": "Document not found"}, status=status.HTTP_404_NOT_FOUND)
            medical_document.delete()
            return Response({"message": "Document removed successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AllergyDocumentUploadView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        """
        Post an allergy document

        --

        Parameters:
            request (Request): Request object

        Returns:
            Response: A response with a 201 status if the document is added
                    successfully, or a 400 status if the request is invalid.

        Raises:
            Exception: If an unexpected error occurs.
        """

        try:
            serializer = AllergyDocumentSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(patient=request.user)
                return Response({"message": "Document Added Successfully", "data": serializer.data}, status=status.HTTP_201_CREATED)
            return Response({"message": "Invalid data", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request):
        """
        Retrieve all allergy documents associated with the current logged-in patient.

        Returns:
            Response: A response with a 200 status if the documents are retrieved
                    successfully, or a 400 status if an unexpected error occurs.

        Raises:
            Exception: If an unexpected error occurs.
        """
        try:
            allergy_documents = AllergyDocument.objects.filter(patient=request.user)
            if not allergy_documents.exists():
                return Response({"message": "No allergy documents found", "data": []}, status=status.HTTP_200_OK)
            serializer = AllergyDocumentSerializer(allergy_documents, many=True)
            return Response({"message": "Documents Retrieved Successfully", "data": serializer.data}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        """
        Update an allergy document

        --

        Parameters:
            pk (int): The id of the document to update

        Returns:
            Response: A response with a 200 status if the document is updated
                    successfully, or a 400 status if the document is not found
                    or the request is invalid.

        Raises:
            Exception: If an unexpected error occurs.
        """
        try:
            try:
                patient_document = AllergyDocument.objects.get(pk=pk, patient=request.user)
            except AllergyDocument.DoesNotExist:
                return Response({"message": "Document not found or access denied"}, status=status.HTTP_404_NOT_FOUND)
            serializer = AllergyDocumentSerializer(instance=patient_document, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({"message": "Document Updated Successfully", "data": serializer.data}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def delete(self, request, pk):
        """
        Delete an allergy document
        ---

        Parameters:
            pk (int): The id of the document to delete

        Returns:
            Response: A response with a 200 status if the document is deleted
                    successfully, or a 400 status if the document is not found
                    or the request is invalid.

        Raises:
            Exception: If an unexpected error occurs.
        """
        try:
            try:
                patient_document = AllergyDocument.objects.get(pk=pk, patient=request.user)
            except AllergyDocument.DoesNotExist:
                return Response({"message": "Document not found or access denied"},
                                status=status.HTTP_404_NOT_FOUND)
            patient_document.delete()
            return Response({"message": "Document removed successfully"},
                            status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



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

class ListFavouriteDoctors(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            user = request.user
            try:
                patient = user.patient_profile
            except AttributeError:
                return Response({"error": "User has no patient."}, status=status.HTTP_404_NOT_FOUND) 
            search_key = request.query_params.get("search_key", "").strip()
            if search_key:
                fav_doctors = Favourite.objects.filter(fav_doc__user__first_name__istartswith=search_key,patient=patient, fav_doc__isnull=False) | \
                        Favourite.objects.filter(fav_doc__user__last_name__istartswith=search_key,patient=patient, fav_doc__isnull=False)
            else:
                fav_doctors = Favourite.objects.filter(patient=patient, fav_doc__isnull=False) 
            paginated_data, headers = pagination_view(fav_doctors, request)
            serializer = FavouriteDoctorSerializer(paginated_data, many=True)
            return create_paginated_response(" Favourite doctors list retrieved successfully.",serializer.data,headers)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        
class ListFavouriteClinics(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            user = request.user
            try:
                patient = user.patient_profile
            except AttributeError:
                return Response({"error": "User has no patient."}, status=status.HTTP_404_NOT_FOUND) 
            
            search_key = request.query_params.get("search_key", "").strip()
            if search_key:
                fav_clinics = Favourite.objects.filter(fav_clinic__user__first_name__istartswith=search_key, patient=patient, fav_clinic__isnull=False) | \
                    Favourite.objects.filter(fav_clinic__user__last_name__istartswith=search_key, patient=patient, fav_clinic__isnull=False)
            else:
                fav_clinics = Favourite.objects.filter(patient=patient, fav_clinic__isnull=False)   
            paginated_data, headers = pagination_view(fav_clinics, request)
            serializer = FavouriteClinicSerializer(paginated_data, many=True)
            return create_paginated_response("Favourite clinics retrieved successfully.",serializer.data,headers)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

class AddFamilyMemberView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        patient = get_object_or_404(Patient, user=request.user)

        member_name = request.data.get("member_name")
        family_status = request.data.get("family_status")
        member_profile = request.FILES.get("member_profile")
        member_email=request.data.get("member_email")

        if not (member_name and family_status):
            return Response(
                {"error": "Member name and family status are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create a new family member
        family_member = FamilyMember.objects.create(
            patient=patient,
            member_name=member_name,
            family_status=family_status,
            member_profile=member_profile,
            member_email=member_email
        )

        # Delete any old OTPs for this family member
        OTPVerification.objects.filter(family_member=family_member).delete()

        # Generate a new OTP
        otp_code = ''.join(random.choices(string.digits, k=6))
        print(f"Generated OTP: {otp_code}")

        # Save OTP in the database
        OTPVerification.objects.create(family_member=family_member, otp=otp_code)

        # Send OTP to the patient's email
        self.send_otp_email(patient.user.email, member_name, family_status, otp_code)

        return Response(
            {
                "message": "Family member added. OTP sent to patient email for verification.",
                "family_member": {
                    "id": family_member.id,
                    "member_email":family_member.member_email,
                    "member_name": family_member.member_name,
                    "family_status": family_member.family_status,
                    "member_profile": request.build_absolute_uri(family_member.member_profile.url) if family_member.member_profile else None,
                    "is_verified": family_member.is_verified
                }
            },
            status=status.HTTP_201_CREATED
        )

    def send_otp_email(self, to_email, member_name, family_status, otp_code):
        """Send OTP email using SendGrid"""
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

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
    permission_classes = [IsAuthenticated]

    def post(self, request):
        otp_code = request.data.get("otp")
        member_id = request.data.get("family_member_id")

        if not (otp_code and member_id):
            return Response({"error": "Family member ID and OTP are required."}, status=status.HTTP_400_BAD_REQUEST)

        # Get the family member
        family_member = FamilyMember.objects.filter(id=member_id, is_verified=False).first()

        if not family_member:
            return Response({"error": "Family member not found or already verified."}, status=status.HTTP_404_NOT_FOUND)

        # Get the latest OTP entry
        otp_entry = OTPVerification.objects.filter(family_member=family_member).order_by('-created_at').first()

        if not otp_entry or str(otp_entry.otp).strip() != str(otp_code).strip():
            return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

        # Mark the family member as verified
        family_member.is_verified = True
        family_member.save()

        # Delete OTP after verification
        otp_entry.delete()

        return Response(
            {
                "message": "Family member verified successfully.",
                "family_member": {
                    "id": family_member.id,
                    "member_name": family_member.member_name,
                    "family_status": family_member.family_status,
                    "member_profile": request.build_absolute_uri(family_member.member_profile.url) if family_member.member_profile else None,
                    "is_verified": family_member.is_verified
                }
            },
            status=status.HTTP_200_OK
        )


class UpdateFamilyMemberView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        # Extract family_member_id from query parameters
        member_id = request.query_params.get("family_member_id")

        if not member_id:
            return Response({"error": "Family member ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Get the authenticated user's patient profile
        patient = get_object_or_404(Patient, user=request.user)

        # Ensure the family member belongs to the current user
        family_member = get_object_or_404(FamilyMember, id=member_id, patient=patient)

        # Get updated data from request
        member_name = request.data.get("member_name", family_member.member_name)
        family_status = request.data.get("family_status", family_member.family_status)
        member_profile = request.FILES.get("member_profile")

        # Update the fields
        family_member.member_name = member_name
        family_member.family_status = family_status

        if member_profile:
            family_member.member_profile = member_profile

        family_member.save()

        # Prepare response
        updated_data = {
            "id": family_member.id,
            "member_name": family_member.member_name,
            "family_status": family_member.family_status,
            "member_profile": request.build_absolute_uri(family_member.member_profile.url) if family_member.member_profile else None,
            "is_verified": family_member.is_verified
        }

        return Response(
            {"message": "Family member updated successfully.", "family_member": updated_data},
            status=status.HTTP_200_OK
        )

    
    
class GetFamilyMembersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get the authenticated user's patient profile
        patient = get_object_or_404(Patient, user=request.user)

        # Fetch only the family members of the current user
        family_members = FamilyMember.objects.filter(patient=patient, is_verified=True)

        # Serialize the data
        family_members_data = [
            {
                "id": member.id,
                "member_name": member.member_name,
                "family_status": member.family_status,
                "member_profile": request.build_absolute_uri(member.member_profile.url) if member.member_profile else None,
                "is_verified": member.is_verified
            }
            for member in family_members
        ]

        return Response({"family_members": family_members_data}, status=status.HTTP_200_OK)


class AppointmentDetailAPIView(APIView):
    """API to fetch appointment details with doctor info, restricted to the patient."""
    permission_classes = [IsAuthenticated]
    def get(self, request, appointment_id):
        """Retrieve appointment details if the user is the patient."""
        appointment = get_object_or_404(BookedAppointment, id=appointment_id)

        # Check if the logged-in user is the patient
        if appointment.patient != request.user.id:  
            return Response({"error": "You can only access your own appointments."}, status=status.HTTP_403_FORBIDDEN)

        # Fetch doctor details
        doctor = get_object_or_404(User, id=appointment.doctor)
        doctor_specialty = get_object_or_404(Doctor, user=doctor)
        
        data = {
            "doctor_name": doctor.get_full_name(),
            "doctor_specialty": doctor_specialty.specialty,  # Adjust based on your model
            "experience": f"{doctor_specialty.experience_years} years practice",
            # "location": f"{doctor_specialty.city}, {doctor_specialty.country}",  # Adjust
            "appointment_time": appointment.slot,  # Assuming slot stores time
            "appointment_date": appointment.date.strftime("%d/%m/%Y"),
            # "doctor_image": request.build_absolute_uri(doctor_specialty.profile_picture.url) if doctor_specialty.profile_picture else None,
        }
        return Response(data, status=status.HTTP_200_OK)
    
    
class AppointmentReminderAPIView(APIView):
    """API to set reminders for a specific appointment."""
    
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Set a reminder for a specific appointment."""
        appointment_id = request.data.get("appointment_id")

        if not appointment_id:
            return Response({"error": "Appointment ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        appointment = get_object_or_404(BookedAppointment, id=appointment_id)
        # Ensure the appointment belongs to the logged-in user
        if appointment.patient != request.user.id:
            return Response(
                {"error": "You can only set reminders for your own appointments."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ReminderSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            reminder = serializer.save(appointment=appointment)

            # Extract start time from slot
            try:
                start_time_str = appointment.slot.split(" - ")[0]  # Extract 'HH:MM' from '15:30 - 16:00'
                appointment_datetime = datetime.combine(
                    appointment.date, 
                    datetime.strptime(start_time_str, "%H:%M").time()
                )
            except ValueError:
                return Response({"error": "Invalid slot format. Expected 'HH:MM - HH:MM'."}, status=status.HTTP_400_BAD_REQUEST)

            # Calculate reminder time
            reminder_time = None
            if reminder.notification_time_type == "days":
                reminder_time = timezone.make_aware(
                    appointment_datetime, timezone.get_current_timezone()
                ) - timedelta(days=reminder.notification_time)
            elif reminder.notification_time_type == "hours":
                reminder_time = timezone.make_aware(
                    appointment_datetime, timezone.get_current_timezone()
                ) - timedelta(hours=reminder.notification_time)
            elif reminder.notification_time_type == "minutes":
                reminder_time = timezone.make_aware(
                    appointment_datetime, timezone.get_current_timezone()
                ) - timedelta(minutes=reminder.notification_time)
                
            # Schedule the reminder task
            if reminder_time and reminder_time > timezone.now():  # Ensure it's scheduled in the future
                send_email_reminder.apply_async(args=[reminder.id], utc=reminder_time)
                send_whatsapp_reminder.apply_async(args=[reminder.id], utc=reminder_time)
                print(f"Email Reminder scheduled for {reminder_time}")
                print(f"WhatsApp Reminder scheduled for {reminder_time}")
                
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DoctorAssociatedToPatientListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            patient = request.user

            if patient.role != "Patient":
                return Response({
                    "data": None,
                    "message": "Only patients can view their associated doctors.",
                    "status": "error"
                }, status=status.HTTP_403_FORBIDDEN)

            doctor_ids = BookedAppointment.objects.filter(
                patient=patient.id
            ).values_list("doctor", flat=True).distinct()

            doctors = User.objects.filter(id__in=doctor_ids, role="Doctor")
            serializer = DoctorSerializer(doctors, many=True)

            return Response({
                "data": {
                    "message": "Associated doctors retrieved successfully.",
                    "associated_doctors": serializer.data
                },
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "message": str(e),
                "status": "error"
            }, status=status.HTTP_400_BAD_REQUEST)
