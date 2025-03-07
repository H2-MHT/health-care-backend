import logging
from datetime import timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from sendgrid.helpers.mail import Content, Email, Mail, To

from users.models import User
from users.serializers import UserSerializer

from .models import (
    AppointmentManagement,
    CancellationPolicy,
    CommunicationPreferences,
    ConsultationSettings,
    Doctor,
    Invitation,
    NoShowPolicy,
    Referral,
    ReschedulePolicy,
    UserPreference,
    Membership,
    BookedAppointment,
)
from .serializers import (
    AppointmentManagementSerializer,
    CancellationPolicySerializer,
    CommunicationPreferencesSerializer,
    ReferralSerializer,
    NoShowPolicySerializer,
    ReschedulePolicySerializer,
    ConsultationSettingsSerializer,
    BookedAppointmentSerializer,
)
from django.utils.crypto import get_random_string
import pytz
from datetime import datetime
from django.contrib.auth.hashers import check_password
import random
from django.conf import settings
import sendgrid
from rest_framework.exceptions import NotFound
from django.contrib.auth.hashers import make_password

from rest_framework.decorators import api_view

# Initialize logger
logger = logging.getLogger(__name__)


class DoctorListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        logger.info("User %s is requesting the doctor list.", request.user.email)
        try:
            doctors = User.objects.filter(role="Doctor")
            serializer = UserSerializer(doctors, many=True)
            return Response(
                {"message": "Doctor list retrieved successfully.", "data": serializer.data}
            )
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AppointmentManagementAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            preferences = AppointmentManagement.objects.filter(user=request.user)
            serializer = AppointmentManagementSerializer(preferences, many=True)
            return Response({"message": "Appointment preferences retrieved successfully.", "data": serializer.data})
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        """Create a new appointment"""
        try:
            logger.info(f"User {request.user} is attempting to create an appointment with data: {request.data}")

            serializer = AppointmentManagementSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(user=request.user)

                logger.info(
                    f"User {request.user} successfully created an appointment with ID {serializer.instance.id}.")
                return Response(
                    {"message": "Appointment preference created successfully.", "data": serializer.data},
                    status=status.HTTP_201_CREATED
                )

            logger.warning(f"User {request.user} provided invalid data: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.exception(f"Error creating appointment for user {request.user}: {str(e)}")
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        """Update an existing appointment using pk from the request body"""
        try:
            pk = request.data.get("pk")
            if not pk:
                return Response({"message": "ID (pk) is required for updating."}, status=status.HTTP_400_BAD_REQUEST)

            appointment = get_object_or_404(AppointmentManagement, id=pk, user=request.user)
            
            serializer = AppointmentManagementSerializer(appointment, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                logger.info(f"Appointment with ID {pk} updated successfully by user {request.user}.")
                return Response(
                    {"message": "Appointment preference updated successfully.", "data": serializer.data},
                    status=status.HTTP_200_OK
                )

            logger.warning(f"Invalid data for updating appointment ID {pk}: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error while updating appointment: {str(e)}", exc_info=True)
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        """Delete an existing appointment using pk from the request body"""
        try:
            pk = request.data.get("pk")  # Get 'pk' from request body
            if not pk:
                logger.warning(f"User {request.user} attempted to delete an appointment without providing an ID.")
                return Response({"message": "ID is required for deletion."}, status=status.HTTP_400_BAD_REQUEST)

            appointment = AppointmentManagement.objects.filter(id=pk, user=request.user).first()
            if not appointment:
                logger.error(f"User {request.user} attempted to delete a non-existing appointment with ID {pk}.")
                return Response({"message": "Appointment preference not found."}, status=status.HTTP_404_NOT_FOUND)

            appointment.delete()
            logger.info(f"User {request.user} successfully deleted appointment with ID {pk}.")
            return Response({"message": "Appointment preference deleted successfully."},
                            status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Error deleting appointment for user {request.user}: {str(e)}")
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AvailableSlotsAPIView(APIView):
    """
    API to get available slots for a selected doctor.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            doctor_id = request.query_params.get("doctor_id")
            appointment_type = request.query_params.get("appointment_type")

            print(f"Doctor ID: {doctor_id}, Appointment Type: {appointment_type}")

            if not doctor_id:
                return Response({"error": "Doctor ID is required"}, status=400)

            # Validate doctor exists
            doctor = Doctor.objects.filter(user__id=doctor_id, user__role="Doctor").first()
            if not doctor:
                return Response({"error": "Invalid doctor ID"}, status=404)

            # Get today's day abbreviation (e.g., "Mon", "Tue")
            today = datetime.now().strftime("%a")[:3]
            print(f"Today's Day: {today}")

            # Fetch doctor's availability for today
            availability = AppointmentManagement.objects.filter(
                user=doctor.user, appointment_type=appointment_type, days=today
            ).first()

            print(f"Querying AppointmentManagement with: {doctor_id}, {appointment_type}, {today}")
            print(f"Availability Found: {availability}")

            if not availability:
                return Response({"message": "Doctor is not available today"}, status=200)

            # Get session length from ConsultationSettings
            settings = ConsultationSettings.objects.filter(doctor=doctor).first()
            if not settings:
                print("No consultation settings found!")
                return Response({"error": "Consultation settings not found"}, status=400)

            session_length = settings.planned_session_length if appointment_type == "Planned" else settings.urgent_session_length
            if not session_length:
                print("Session length not configured in ConsultationSettings!")
                return Response({"error": "Session length not configured"}, status=400)

            start_time = availability.start_time
            end_time = availability.end_time
            print(f"Doctor Available From {start_time} to {end_time}")

            # Fetch already booked slots
            booked_slots = BookedAppointment.objects.filter(
                doctor=doctor.user, appointment_type=appointment_type
            ).values_list('slot', flat=True)

            print(f"Booked Slots: {booked_slots}")

            # Generate available slots
            slots = []
            current_time = start_time
            while current_time < end_time:
                next_time = (datetime.combine(datetime.today(), current_time) + timedelta(minutes=session_length)).time()
                slot_str = f"{current_time.strftime('%H:%M')} - {next_time.strftime('%H:%M')}"

                if slot_str not in booked_slots:
                    slots.append(slot_str)  # Add only if not booked

                print(f"Generated Slot: {slot_str}")
                current_time = next_time

            print(f"Final Available Slots: {slots}")

            return Response({
                "message": "Available slots retrieved successfully",
                "doctor_id": doctor.user.id,
                "doctor_name": f"{doctor.user.first_name} {doctor.user.last_name}",
                "specialty": doctor.specialty,
                "available_slots": slots
            }, status=200)

        except Exception as e:
            print(f"Exception Occurred: {str(e)}")
            return Response({"error": str(e)}, status=400)


class BookAppointmentAPIView(APIView):
    """
    Allows patients to book an available appointment slot only if the doctor has availability.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user  # The logged-in patient
            if user.role != "Patient":
                return Response({"error": "Only patients can book an appointment"}, status=403)

            doctor_id = request.data.get("doctor_id")
            slot = request.data.get("slot")  # format: "10:00 - 10:30"
            appointment_type = request.data.get("appointment_type", "Planned")
            date = request.data.get("date") # (DD-MM-YYYY)

            # Convert date to correct format
            date_obj = datetime.strptime(date, "%d-%m-%Y").date()
            appointment_day = date_obj.strftime("%a")

            # Ensure doctor exists
            doctor = User.objects.filter(id=doctor_id, role="Doctor").first()
            if not doctor:
                return Response({"error": "Invalid doctor ID"}, status=404)

            # Ensure doctor has set availability for this day
            availability = AppointmentManagement.objects.filter(
                user=doctor,
                appointment_type=appointment_type,
                days__icontains=appointment_day
            ).first()

            if not availability:
                return Response({"error": "Doctor is not available on this day"}, status=400)

            # Convert slot start and end time
            slot_start, slot_end = slot.split(" - ")
            slot_start = datetime.strptime(slot_start, "%H:%M").time()
            slot_end = datetime.strptime(slot_end, "%H:%M").time()

            # Ensure slot falls within the doctor's available hours
            if not (availability.start_time <= slot_start and availability.end_time >= slot_end):
                return Response({"error": "Selected slot is outside doctor's available hours"}, status=400)

            # Ensure slot is not already booked
            is_booked = BookedAppointment.objects.filter(
                doctor=doctor, slot=slot, date=date_obj
            ).exists()

            if is_booked:
                return Response({"error": "Selected slot is already booked"}, status=400)

            # Create appointment
            appointment = BookedAppointment.objects.create(
                doctor=doctor,
                patient=user,
                appointment_type=appointment_type,
                slot=slot,
                status="Confirmed",
                date=date_obj,
                payment_status="Pending",  # Payment status should be pending initially
            )

            # Format response
            return Response({
                "message": "Appointment booked successfully",
                "data": {
                    "appointment_id": appointment.id,
                    "appointment_type": appointment.appointment_type,
                    "date": date,
                    "payment_status": appointment.payment_status,
                }
            })

        except Exception as e:
            return Response({"error": str(e)}, status=400)


class MyAppointmentsAPIView(APIView):
    """
    Allows patients to view their booked appointments.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            if user.role != "Patient":
                return Response({"error": "Only patients can view their appointments"}, status=403)

            appointments = BookedAppointment.objects.filter(patient=user).order_by("slot")
            data = [{
                "appointment_id": appt.id,
                "doctor_name": f"{appt.doctor.first_name} {appt.doctor.last_name}",
                "appointment_type": appt.appointment_type,
                "slot": appt.slot,
                "status": appt.status
            } for appt in appointments]

            return Response({"message": "Appointments retrieved successfully", "appointments": data})

        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Reschedule Appointment API
class RescheduleAppointmentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        """
        Allows a patient to reschedule their appointment.
        """
        appointment_id = kwargs.get("pk")
        new_slot = request.data.get("new_slot")

        try:
            appointment = BookedAppointment.objects.get(id=appointment_id, patient=request.user)

            if appointment.status in ["Canceled"]:
                return Response({"error": "Cannot reschedule a canceled appointment."}, status=status.HTTP_400_BAD_REQUEST)

            appointment.slot = new_slot
            appointment.status = "Rescheduled"
            appointment.save()

            return Response({"message": "Appointment rescheduled successfully"}, status=status.HTTP_200_OK)
        except BookedAppointment.DoesNotExist:
            return Response({"error": "Appointment not found"}, status=status.HTTP_404_NOT_FOUND)

# Cancel Appointment API
class CancelAppointmentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        """
        Allows a patient to cancel their appointment.
        """
        appointment_id = kwargs.get("pk")

        try:
            appointment = BookedAppointment.objects.get(id=appointment_id, patient=request.user)

            if appointment.status == "Canceled":
                return Response({"error": "Appointment is already canceled."}, status=status.HTTP_400_BAD_REQUEST)

            appointment.status = "Canceled"
            appointment.save()

            return Response({"message": "Appointment canceled successfully"}, status=status.HTTP_200_OK)
        except BookedAppointment.DoesNotExist:
            return Response({"error": "Appointment not found"}, status=status.HTTP_404_NOT_FOUND)

# Appointment Reminder API
class AppointmentReminderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        Fetch upcoming appointment reminders for the authenticated patient.
        """
        today = datetime.now()
        reminder_time = today + timedelta(days=1)

        reminders = BookedAppointment.objects.filter(patient=request.user, created_at__lte=reminder_time).exclude(status="Canceled")
        serializer = BookedAppointmentSerializer(reminders, many=True)

        return Response({"reminders": serializer.data}, status=status.HTTP_200_OK)

# Payment Confirmation API
class PaymentConfirmationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Allows a patient to confirm their payment status.
        """
        appointment_id = request.data.get("appointment_id")
        payment_status = request.data.get("payment_status")

        try:
            appointment = BookedAppointment.objects.get(id=appointment_id, patient=request.user)

            if payment_status not in ["Pending", "Paid"]:
                return Response({"error": "Invalid payment status"}, status=status.HTTP_400_BAD_REQUEST)

            appointment.payment_status = payment_status
            appointment.save()

            return Response({"message": "Payment status updated successfully"}, status=status.HTTP_200_OK)
        except BookedAppointment.DoesNotExist:
            return Response({"error": "Appointment not found"}, status=status.HTTP_404_NOT_FOUND)    
    
    
class GenerateReferralCodeView(APIView):
    """Generate and return a user's referral code, registration link, and update referral points."""

    def generate_referral_code(self):
        """Generate a unique referral code (7 characters)."""
        return get_random_string(length=7).upper()

    def get(self, request):
        try:
            logger.info(
                "User %s is retrieving or generating referral code.", request.user.email
            )

            # Get or create referral object for the current user
            referral, created = Referral.objects.get_or_create(user=request.user)

            if created:
                referral.personal_code = self.generate_referral_code()
                referral.save()
                logger.info(
                    "Generated new referral code for user: %s", request.user.email
                )

            # Return referral data
            serializer = ReferralSerializer(referral)
            return Response(
                {
                    "message": "Referral data retrieved successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except Referral.DoesNotExist:
            logger.warning("Referral code not found for user: %s", request.user.email)
            return Response(
                {"error": "Referral code not found."}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(
                "Error retrieving referral code for user %s: %s",
                request.user.email,
                str(e),
            )
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InviteUserView(APIView):
    """Apply referral code manually and mark it as used."""

    def post(self, request):
        referral_code = request.data.get(
            "referral_code"
        )  # Get referral code from request body

        if not request.user.is_authenticated:
            logger.warning(
                "Unauthorized attempt to use referral code by anonymous user."
            )
            return Response(
                {"error": "You must be logged in to use a referral code."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            # Check if the referral code exists
            referral = Referral.objects.get(personal_code=referral_code)
            logger.info(
                "User %s attempting to use referral code: %s",
                request.user.email,
                referral_code,
            )

            if referral.user == request.user:
                logger.warning(
                    "User %s tried to use their own referral code.", request.user.email
                )
                return Response(
                    {"error": "You cannot use your own referral code."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check if this referral code has already been used by the current user
            if Invitation.objects.filter(
                    invited_by=referral, invited_user=request.user
            ).exists():
                logger.warning(
                    "User %s already used referral code: %s",
                    request.user.email,
                    referral_code,
                )
                return Response(
                    {"error": "You have already used this referral code."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                # Create an invitation for the new user (invited by user A)
                invitation = Invitation.objects.create(
                    invited_by=referral,
                    invited_user=request.user,
                )

                # Update the inviter's invited users count
                referral.invited_users_count = Invitation.objects.filter(
                    invited_by=referral
                ).count()
                referral.save()

                logger.info(
                    "Referral code %s successfully used by user %s",
                    referral_code,
                    request.user.email,
                )

            return Response(
                {"message": "Referral code applied successfully."},
                status=status.HTTP_200_OK,
            )

        except Referral.DoesNotExist:
            logger.error(
                "Invalid referral code attempt: %s by user %s",
                referral_code,
                request.user.email,
            )
            return Response(
                {"error": "Invalid referral code."}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception(
                "Error applying referral code for user %s: %s",
                request.user.email,
                str(e),
            )
            return Response({"message": "You already applied other referral code"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def redeem_invitation(request, invitation_code):
    """Redeem the invitation and increase the inviter's stats."""
    try:
        logger.info(
            "User %s attempting to redeem invitation code: %s",
            request.user.email,
            invitation_code,
        )
        invitation = Invitation.objects.get(invitation_code=invitation_code)

        if invitation.redeemed:
            logger.warning(
                "User %s attempted to redeem already used invitation code: %s",
                request.user.email,
                invitation_code,
            )
            return Response(
                {"error": "This invitation has already been redeemed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            invitation.redeem()  # Redeem the invitation
            logger.info(
                "Invitation code %s redeemed successfully by user %s",
                invitation_code,
                request.user.email,
            )

        return Response(
            {"message": "Invitation redeemed successfully!"}, status=status.HTTP_200_OK
        )
    except Invitation.DoesNotExist:
        logger.error(
            "Invalid invitation code attempt: %s by user %s",
            invitation_code,
            request.user.email,
        )
        return Response(
            {"error": "Invalid invitation code."}, status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.exception(
            "Error redeeming invitation code %s for user %s: %s",
            invitation_code,
            request.user.email,
            str(e),
        )
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


def get_time_in_timezone(timezone):
    """Get the current time in the specified timezone."""
    try:
        tz = pytz.timezone(timezone)
        return datetime.now(tz).isoformat()
    except Exception as e:
        logger.error(f"Invalid timezone format: {timezone} - {str(e)}")
        return None


class ConsultationSettingsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            user = request.user
            if not hasattr(user, "doctor"):
                return Response(
                    {"error": "You are not a registered doctor."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            consultation_settings = ConsultationSettings.objects.filter(doctor=user.doctor)
            serializer = ConsultationSettingsSerializer(consultation_settings, many=True)
            return Response(
                {
                    "message": "Consultation settings retrieved successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def post(self, request, *args, **kwargs):
        user = request.user
        try:
            doctor = Doctor.objects.get(user=user)
        except Doctor.DoesNotExist:
            return Response(
                {"error": "You are not a registered doctor."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            with transaction.atomic():
                consultation_settings = ConsultationSettings.objects.filter(
                    doctor=doctor
                ).first()

                if consultation_settings:
                    serializer = ConsultationSettingsSerializer(
                        consultation_settings, data=request.data, partial=True
                    )
                else:
                    request.data["doctor"] = doctor.id
                    serializer = ConsultationSettingsSerializer(data=request.data)

                if serializer.is_valid():
                    serializer.save()
                    message = (
                        "Consultation settings updated successfully"
                        if consultation_settings
                        else "Consultation settings created successfully"
                    )
                    return Response(
                        {"message": message, "data": serializer.data},
                        status=(
                            status.HTTP_200_OK
                            if consultation_settings
                            else status.HTTP_201_CREATED
                        ),
                    )

                return Response(
                    {"error": "Invalid data", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            logger.error(f"Error in ConsultationSettingsAPIView: {str(e)}")
            return Response(
                {"error": "Something went wrong", "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class UserPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            preference, _ = UserPreference.objects.get_or_create(user=request.user)
            user_languages = (
                preference.language.split(",") if preference.language else ["en"]
            )
            user_timezone = "UTC" if preference.use_system_timezone else preference.timezone
            current_time = get_time_in_timezone(user_timezone) or "Invalid timezone"
            return Response(
                {
                    "message": "Data fetched successfully.",
                    "user_preference": {
                        "timezone": user_timezone,
                        "languages": user_languages,
                        "use_system_timezone": preference.use_system_timezone,
                        "use_system_language": preference.use_system_language,
                        "current_time": current_time,
                    },
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def post(self, request):
        try:
            preference, _ = UserPreference.objects.get_or_create(user=request.user)
            timezone = request.data.get("timezone")
            languages = request.data.get("languages")
            use_system_timezone = request.data.get("use_system_timezone")
            use_system_language = request.data.get("use_system_language")

            # Validate timezone
            if timezone and timezone not in pytz.all_timezones:
                return Response(
                    {"error": "Invalid timezone provided."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if languages and not isinstance(languages, list):
                return Response(
                    {"error": "Languages must be a list."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                if timezone is not None:
                    preference.timezone = timezone
                if languages is not None:
                    preference.language = ",".join(languages)
                if use_system_timezone is not None:
                    preference.use_system_timezone = use_system_timezone
                if use_system_language is not None:
                    preference.use_system_language = use_system_language

                preference.save()

            return Response(
                {
                    "message": "Data updated successfully.",
                    "user_preference": {
                        "timezone": preference.timezone,
                        "languages": (
                            languages if languages else preference.language.split(",")
                        ),
                        "use_system_timezone": preference.use_system_timezone,
                        "use_system_language": preference.use_system_language,
                    },
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ReschedulePolicyView(APIView):
    """API to create or update a Reschedule Policy for each day."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Update an existing data or create a new one."""
        try:
            data = request.data
            user = request.user
            reschedule_day = data.get("reschedule_days")
            valid_days = [choice[0] for choice in ReschedulePolicy.DAYS_CHOICES]

            if reschedule_day not in valid_days:
                logger.warning(
                    f"Invalid day format attempted by {user}. Input: {reschedule_day}"
                )
                return Response(
                    {"error": "Invalid day format. Use 'Mon', 'Tue', etc."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            existing_policy = ReschedulePolicy.objects.filter(
                user=user, reschedule_days=reschedule_day
            ).first()

            if existing_policy:
                logger.info(
                    f"Updating existing reschedule policy for {reschedule_day} by user {user}"
                )
                existing_policy.allow_reschedule = data.get(
                    "allow_reschedule", existing_policy.allow_reschedule
                )
                existing_policy.max_reschedules = data.get(
                    "max_reschedules", existing_policy.max_reschedules
                )
                existing_policy.reschedule_time_range = data.get(
                    "reschedule_time_range", existing_policy.reschedule_time_range
                )
                existing_policy.save()
                return Response(
                    {
                        "message": f"Reschedule policy for {reschedule_day} updated successfully.",
                        "data": ReschedulePolicySerializer(existing_policy).data,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                logger.info(
                    f"Creating new reschedule policy for {reschedule_day} by user {user}"
                )
                policy = ReschedulePolicy.objects.create(
                    user=user,
                    allow_reschedule=data.get("allow_reschedule", True),
                    max_reschedules=data.get("max_reschedules"),
                    reschedule_days=reschedule_day,
                    reschedule_time_range=data.get("reschedule_time_range"),
                )
                return Response(
                    {
                        "message": f"Reschedule policy for {reschedule_day} created successfully.",
                        "data": ReschedulePolicySerializer(policy).data,
                    },
                    status=status.HTTP_201_CREATED,
                )
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
    def get(self, request):
        """Fetch all reschedule policies for the logged-in user."""
        try:
            user = request.user
            logger.info(f"Fetching reschedule policies for user {user}")
            policies = ReschedulePolicy.objects.filter(user=user)
            serializer = ReschedulePolicySerializer(policies, many=True)
            return Response(
                {
                    "message": "Reschedule policies fetched successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class CancellationPolicyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            policy = CancellationPolicy.objects.get(doctor=request.user)
            logger.info(f"Fetching cancellation policy for user {request.user}")
        except CancellationPolicy.DoesNotExist:
            logger.warning(f"Cancellation policy not found for user {request.user}")
            raise NotFound("Cancellation policy not found.")

        serializer = CancellationPolicySerializer(policy)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        try:
            existing_policy = CancellationPolicy.objects.filter(doctor=request.user).first()
            if existing_policy:
                logger.info(
                    f"Updating existing cancellation policy for user {request.user}"
                )
                serializer = CancellationPolicySerializer(
                    existing_policy,
                    data=request.data,
                    context={"request": request},
                    partial=True,
                )
                if serializer.is_valid():
                    serializer.save()
                    return Response(
                        {
                            "message": "Cancellation policy updated successfully.",
                            "data": serializer.data,
                        },
                        status=status.HTTP_200_OK,
                    )
                logger.error(
                    f"Invalid data for updating cancellation policy by user {request.user}: {serializer.errors}"
                )
                return Response(
                    {"detail": "Invalid data.", "errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            logger.info(f"Creating new cancellation policy for user {request.user}")
            serializer = CancellationPolicySerializer(
                data=request.data, context={"request": request}
            )
            if serializer.is_valid():
                serializer.save(doctor=request.user)
                return Response(
                    {
                        "message": "Cancellation policy created successfully.",
                        "data": serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            logger.error(
                f"Invalid data for creating cancellation policy by user {request.user}: {serializer.errors}"
            )
            return Response(
                {"detail": "Invalid data.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class NoShowPolicyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                logger.warning("Unauthorized access attempt to NoShowPolicy GET endpoint")
                return Response(
                    {"detail": "Authentication credentials were not provided."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            logger.info(f"Fetching NoShowPolicy for user {request.user}")
            policies = NoShowPolicy.objects.filter(user=request.user)
            serializer = NoShowPolicySerializer(policies, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                logger.warning("Unauthorized access attempt to NoShowPolicy POST endpoint")
                return Response(
                    {"detail": "Authentication credentials were not provided."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            if NoShowPolicy.objects.filter(user=request.user).exists():
                logger.warning(
                    f"User {request.user} attempted to create a duplicate NoShowPolicy"
                )
                return Response(
                    {"detail": "You already have an existing NoShowPolicy."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            data = request.data.copy()
            data["user"] = request.user.id
            serializer = NoShowPolicySerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                logger.info(f"NoShowPolicy created successfully for user {request.user}")
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            logger.error(
                f"Invalid data for NoShowPolicy creation by user {request.user}: {serializer.errors}"
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
            

    def put(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                logger.warning("Unauthorized access attempt to NoShowPolicy PUT endpoint")
                return Response(
                    {"detail": "Authentication credentials were not provided."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            policy = get_object_or_404(NoShowPolicy, user=request.user)
            serializer = NoShowPolicySerializer(policy, data=request.data, partial=True)

            if serializer.is_valid():
                serializer.save()
                logger.info(f"NoShowPolicy updated successfully for user {request.user}")
                return Response(serializer.data)

            logger.error(
                f"Invalid data for NoShowPolicy update by user {request.user}: {serializer.errors}"
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class CommunicationPreferencesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            """Retrieve the current user's communication preferences"""
            preferences, created = CommunicationPreferences.objects.get_or_create(
                user=request.user
            )
            serializer = CommunicationPreferencesSerializer(preferences)
            logger.info(f"Fetched communication preferences for user {request.user}")
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def put(self, request, *args, **kwargs):
        try:
            """Update the current user's communication preferences"""
            preferences, created = CommunicationPreferences.objects.get_or_create(
                user=request.user
            )
            serializer = CommunicationPreferencesSerializer(
                preferences, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                logger.info(f"Updated communication preferences for user {request.user}")
                return Response(serializer.data, status=status.HTTP_200_OK)
            logger.error(
                f"Invalid data for updating communication preferences by user {request.user}: {serializer.errors}"
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


def send_otp(user):
    otp = str(random.randint(100000, 999999))
    user.otp = otp
    user.save()

    sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
    from_email = Email("akash.prajapati@techqware.com")  # Update with your sender email
    to_email = To(user.email)
    subject = "Your OTP for Password Change"
    content = Content("text/plain", f"Your OTP for password change is: {otp}")
    mail = Mail(from_email, to_email, subject, content)

    try:
        response = sg.send(mail)
        logger.info(f"Email sent to {user.email} with status code {response.status_code}")
    except Exception as e:
        logger.error(f"Error sending email: {e}")

    return otp


class RequestPasswordChangeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            current_password = request.data.get("current_password")
            new_password = request.data.get("new_password")
            if not check_password(current_password, user.password):
                return Response({"error": "Incorrect current password"}, status=status.HTTP_400_BAD_REQUEST)
            # Store new password in the database instead of session
            user.temp_password = new_password
            user.save()
            # Send OTP via email
            send_otp(user)
            return Response({"message": "OTP sent successfully to your email"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

class VerifyOTPAndChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            entered_otp = request.data.get("otp")
            if user.otp != entered_otp:
                return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)
            # Retrieve new password from the database
            new_password = user.temp_password
            if not new_password:
                return Response({"error": "No new password found. Please restart the process."}, status=status.HTTP_400_BAD_REQUEST)
            # Update the user's password
            user.password = make_password(new_password)
            user.otp = None  # Clear OTP
            user.temp_password = None  # Clear temp password
            user.save()
            return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

class MembershipAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Retrieve current user's membership plan (Requires authentication)"""
        try:
            membership = Membership.objects.get(user=request.user)
            return Response({"membership_type": membership.membership_type})
        except Membership.DoesNotExist:
            return Response({"message": "No membership found"}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        try:
            """Select a membership plan (Requires authentication)"""
            membership_type = request.data.get("membership_type")
            if membership_type not in ["basic", "premium"]:
                return Response(
                    {"error": "Invalid membership type. Choose 'basic' or 'premium'."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Create or update the user's membership
            membership, created = Membership.objects.update_or_create(
                user=request.user, defaults={"membership_type": membership_type}
            )
            return Response(
                {"message": f"Successfully subscribed to {membership.membership_type} membership!"},
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


