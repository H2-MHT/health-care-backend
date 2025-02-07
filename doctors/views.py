import logging
import random
from datetime import datetime

import pytz
import sendgrid
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.forms import ValidationError
from django.shortcuts import get_object_or_404
from django.utils.crypto import get_random_string
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound
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
    DoctorNotes,
    Invitation,
    NoShowPolicy,
    Referral,
    ReschedulePolicy,
    TwoFactorAuthentication,
    UserPreference,
    UserMembership,
    MembershipPlan,
)
from .serializers import (
    AppointmentManagementSerializer,
    CancellationPolicySerializer,
    CommunicationPreferencesSerializer,
    UserMembershipSerializer,
    DoctorNotesSerializer,
    ReferralSerializer,
    NoShowPolicySerializer,
    ReschedulePolicySerializer,
    ConsultationSettingsSerializer,
)
from django.utils.crypto import get_random_string
import pytz
from datetime import datetime
from django.contrib.auth.hashers import check_password
import random
from django.conf import settings
import sendgrid

from django.utils.translation import gettext
from rest_framework.exceptions import NotFound
from django.contrib.auth.hashers import make_password

from rest_framework.decorators import api_view

# Initialize logger
logger = logging.getLogger(__name__)

class DoctorNotesCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        logger.info("Doctor %s is attempting to create a note.", request.user.email)

        if request.user.role != "Doctor":
            logger.warning(
                "Unauthorized attempt to create a note by user: %s", request.user.email
            )
            return Response(
                {"error": "Only doctors can create notes."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = DoctorNotesSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            logger.info("Doctor note created successfully by %s", request.user.email)
            return Response(
                {
                    "message": "Doctor note created successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        logger.warning(
            "Doctor note creation failed for user: %s, errors: %s",
            request.user.email,
            serializer.errors,
        )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, *args, **kwargs):
        logger.info("Doctor %s is attempting to update a note.", request.user.email)

        if request.user.role != "Doctor":
            logger.warning(
                "Unauthorized attempt to update a note by user: %s", request.user.email
            )
            return Response(
                {"error": "Only doctors can update notes."},
                status=status.HTTP_403_FORBIDDEN,
            )

        note_id = kwargs.get("pk")
        try:
            note = DoctorNotes.objects.get(id=note_id, doctor=request.user)
        except DoctorNotes.DoesNotExist:
            logger.warning(
                "Doctor note update failed - Note not found for user: %s",
                request.user.email,
            )
            return Response(
                {"error": "Note not found or you do not have permission to update it."},
                status=status.HTTP_404_NOT_FOUND,
            )

        new_content = request.data.get("note", "").strip()
        if new_content:
            request.data["note"] = (note.note or "") + " " + new_content

        serializer = DoctorNotesSerializer(
            note, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            serializer.save()
            logger.info("Doctor note updated successfully by %s", request.user.email)
            return Response(
                {
                    "message": "Doctor note updated successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        logger.warning(
            "Doctor note update failed for user: %s, errors: %s",
            request.user.email,
            serializer.errors,
        )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        logger.info("Doctor %s is attempting to delete a note.", request.user.email)

        if request.user.role != "Doctor":
            logger.warning(
                "Unauthorized attempt to delete a note by user: %s", request.user.email
            )
            return Response(
                {"error": "Only doctors can delete notes."},
                status=status.HTTP_403_FORBIDDEN,
            )

        note_id = kwargs.get("pk")
        try:
            note = DoctorNotes.objects.get(id=note_id, doctor=request.user)
        except DoctorNotes.DoesNotExist:
            logger.warning(
                "Doctor note deletion failed - Note not found for user: %s",
                request.user.email,
            )
            return Response(
                {"error": "Note not found or you do not have permission to delete it."},
                status=status.HTTP_404_NOT_FOUND,
            )

        note.delete()
        logger.info("Doctor note deleted successfully by %s", request.user.email)
        return Response(
            {"message": "Note deleted successfully."}, status=status.HTTP_204_NO_CONTENT
        )


class DoctorListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        logger.info("User %s is requesting the doctor list.", request.user.email)

        doctors = User.objects.filter(role="Doctor")
        serializer = UserSerializer(doctors, many=True)

        return Response(
            {"message": "Doctor list retrieved successfully.", "data": serializer.data}
        )


class AppointmentManagementAPIView(APIView):
    """
    API to manage appointment preferences (list, create, update, delete).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get all appointment preferences for the logged-in user with pagination.
        """
        logger.info(
            "User %s is retrieving appointment preferences.", request.user.email
        )
        preferences = AppointmentManagement.objects.filter(user=request.user)
        serializer = AppointmentManagementSerializer(preferences, many=True)

        return Response(
            {
                "message": "Appointment preferences retrieved successfully.",
                "data": serializer.data,
            }
        )

    def post(self, request):
        """
        Create a new appointment preference for the logged-in user.
        """
        logger.info(
            "User %s is creating a new appointment preference.", request.user.email
        )
        serializer = AppointmentManagementSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            logger.info(
                "Appointment preference created successfully by %s", request.user.email
            )
            return Response(
                {
                    "message": "Appointment preference created successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        logger.warning(
            "Appointment preference creation failed for user: %s, errors: %s",
            request.user.email,
            serializer.errors,
        )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        """
        Update an existing appointment preference.
        """
        logger.info(
            "User %s is attempting to update appointment preference ID %s.",
            request.user.email,
            pk,
        )
        try:
            preference = AppointmentManagement.objects.get(pk=pk, user=request.user)
        except AppointmentManagement.DoesNotExist:
            logger.warning(
                "Update failed - Preference not found for user: %s", request.user.email
            )
            return Response(
                {"error": "Preference not found or unauthorized"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AppointmentManagementSerializer(
            preference, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            logger.info(
                "Appointment preference updated successfully by %s", request.user.email
            )
            return Response(
                {
                    "message": "Appointment preference updated successfully.",
                    "data": serializer.data,
                }
            )

        logger.warning(
            "Appointment preference update failed for user: %s, errors: %s",
            request.user.email,
            serializer.errors,
        )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        """
        Delete an appointment preference by ID provided in the request body.
        """
        pk = request.data.get("pk")
        if not pk:
            logger.warning(
                "Delete failed - Missing 'pk' field in request by user: %s",
                request.user.email,
            )
            raise ValidationError("The 'pk' field is required in the request body.")

        try:
            preference = AppointmentManagement.objects.get(pk=pk, user=request.user)
            preference.delete()
            logger.info(
                "Appointment preference deleted successfully by %s", request.user.email
            )
            return Response(
                {"message": "Preference deleted successfully"},
                status=status.HTTP_204_NO_CONTENT,
            )
        except AppointmentManagement.DoesNotExist:
            logger.warning(
                "Delete failed - Preference not found for user: %s", request.user.email
            )
            return Response(
                {"error": "Preference not found or unauthorized"},
                status=status.HTTP_404_NOT_FOUND,
            )


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

            # Update referral points for completed first appointments
            with transaction.atomic():
                updated_count = Invitation.objects.filter(
                    invited_by=referral,
                    first_appointment=True,
                    invited_user__isnull=False,
                ).update(first_appointment=False)
                if updated_count > 0:
                    referral.referral_points += updated_count * 10
                    referral.save()
                    logger.info(
                        "Updated referral points for user: %s (added %d points)",
                        request.user.email,
                        updated_count * 10,
                    )

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
                referral.referral_use = True
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
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


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
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UserPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
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

    def post(self, request):
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


class ReschedulePolicyView(APIView):
    """API to create or update a Reschedule Policy for each day."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Update an existing data or create a new one."""
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

    def get(self, request):
        """Fetch all reschedule policies for the logged-in user."""
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


class NoShowPolicyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
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

    def post(self, request, *args, **kwargs):
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

    def put(self, request, *args, **kwargs):
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


class CommunicationPreferencesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """Retrieve the current user's communication preferences"""
        preferences, created = CommunicationPreferences.objects.get_or_create(
            user=request.user
        )
        serializer = CommunicationPreferencesSerializer(preferences)
        logger.info(f"Fetched communication preferences for user {request.user}")
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
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


class SelectMethodsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Retrieve all selected 2FA methods for the current user."""
        user = request.user
        print(f"Authenticated user: {user.username}, ID: {user.id}")

        # Get all stored 2FA methods for the user
        two_factor_methods = TwoFactorAuthentication.objects.filter(user=user)
        methods = [method.method for method in two_factor_methods]

        print(f"Methods for {user.username}: {methods}")

        return Response({"methods": methods}, status=status.HTTP_200_OK)

    def post(self, request):
        """Add or update 2FA methods while keeping previous selections."""
        user = request.user
        selected_methods = request.data.get("methods", ["email"])  # Default: email

        # Ensure input is a list
        if not isinstance(selected_methods, list):
            return Response({"error": "Methods should be a list"}, status=status.HTTP_400_BAD_REQUEST)

        valid_methods = {"email", "sms", "whatsapp"}
        if not set(selected_methods).issubset(valid_methods):
            return Response({"error": "Invalid methods selected"}, status=status.HTTP_400_BAD_REQUEST)

        # Get existing methods from the database
        existing_methods = set(TwoFactorAuthentication.objects.filter(user=user).values_list("method", flat=True))

        # Add new methods
        new_methods = set(selected_methods) - existing_methods
        TwoFactorAuthentication.objects.bulk_create([
            TwoFactorAuthentication(user=user, method=method) for method in new_methods
        ])

        return Response({"message": "Authentication methods updated successfully"}, status=status.HTTP_200_OK)


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


class VerifyOTPAndChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
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



class UserMembershipAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Retrieve the user's membership plan."""
        try:
            membership = UserMembership.objects.get(user=request.user)
            serializer = UserMembershipSerializer(membership)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserMembership.DoesNotExist:
            return Response({"error": "User has no membership plan"}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        """Assign a membership to a user (Basic by default)."""
        if UserMembership.objects.filter(user=request.user).exists():
            return Response({"error": "User already has a membership"}, status=status.HTTP_400_BAD_REQUEST)

        plan_key = request.data.get("plan_key", "basic")  # Default to Basic

        try:
            plan = MembershipPlan.objects.get(key=plan_key)
            membership = UserMembership.objects.create(user=request.user, plan=plan)
            serializer = UserMembershipSerializer(membership)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except MembershipPlan.DoesNotExist:
            return Response({"error": "Invalid plan selected"}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        """Allows user to update their membership plan."""
        try:
            membership = UserMembership.objects.get(user=request.user)
            plan_key = request.data.get("plan_key")

            if not plan_key:
                return Response({"error": "Plan key is required"}, status=status.HTTP_400_BAD_REQUEST)

            plan = MembershipPlan.objects.get(key=plan_key)
            membership.plan = plan
            membership.save()

            serializer = UserMembershipSerializer(membership)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserMembership.DoesNotExist:
            return Response({"error": "User has no membership plan"}, status=status.HTTP_404_NOT_FOUND)
        except MembershipPlan.DoesNotExist:
            return Response({"error": "Invalid plan selected"}, status=status.HTTP_400_BAD_REQUEST)
        
        