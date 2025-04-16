import logging
import random
import time
import requests
import jwt
import re
import sendgrid
from datetime import timedelta
from django.utils import timezone
from rest_framework.authtoken.models import Token

from django.conf import settings
from django.utils.timezone import now
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from sendgrid import SendGridAPIClient
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.exceptions import AuthenticationFailed
from datetime import timedelta
from django.contrib.auth import authenticate, login
from authify.utils import validate_google_id_token
from doctors.models import Doctor
from doctors.serializers import OtherClinicSerializer
from users.models import User
from patients.models import Patient
from .serializers import (
    OTPVerificationSerializer,
    RegistrationSerializer,
    SignInSerializer,
    SocialLoginSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    ResetPasswordSerializer,
)
from clinics.models import(
    OtherClinic,
)
from clinics.serializers import ClinicInfoSerializer
import logging
from sendgrid.helpers.mail import Mail, To, Personalization
from django.utils.timezone import now


# from doctors.models import LoginHistory

logger = logging.getLogger(__name__)


def get_tokens_for_user(user):
    """
    Generate refresh and access tokens for the given user.

    Args:
        user (User): The user instance for which tokens are generated.

    Returns:
        dict: A dictionary containing 'refresh' and 'access' tokens.
    """
    logger.info(f"Generating tokens for user: {user.email}")
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class SignUpView(APIView):
    """
    API view for user sign-up.
    Handles the registration of a new user by validating the provided data
    and creating a new user instance.
    """

    def generate_otp(self):
        """
        Generate a 6-digit OTP.
        """
        otp = str(random.randint(100000, 999999))
        logger.info(f"Generated OTP: {otp}")
        return otp

    def send_otp_email(self, email, otp, name):
        """
        Send the OTP to the user's email with SendGrid Dynamic Template.
        """
        logger.info(f"Sending OTP to email: {email}")

        # email message
        message = Mail(
            from_email='otp@my-health.today',
        )

        # dynamic template ID
        message.template_id = settings.SENDGRID_TEMPLATE_ID

        # Personalization instance
        personalization = Personalization()
        personalization.add_to(To(email))  # recipient
        personalization.dynamic_template_data = {
            "name": name,
            "otp": otp,
            # "image_url":"http://cdn.mcauto-images-production.sendgrid.net/dfcd8f3f9616c668/c74a987d-d57e-4bfb-9715-053eba5fa1f6/62x62.png"
        }

        message.add_personalization(personalization)

        try:
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            response = sg.send(message)
            logger.info(f"OTP sent successfully to {email}")
            return response
        except Exception as e:
            logger.error(f"Failed to send OTP to {email}: {str(e)}")
            return str(e)

    def post(self, request, *args, **kwargs):
        try:
            logger.info("User sign-up request received.")
            serializer = RegistrationSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.save()
                logger.info(f"User registered successfully: {user.email}")
                name = user.first_name if user.first_name else "User"
                # Generate OTP
                otp = self.generate_otp()

                # Send OTP to user's email
                email_response = self.send_otp_email(user.email, otp, name)

                if isinstance(email_response, str):
                    logger.error(f"Failed to send OTP to {user.email}: {email_response}")
                    return Response(
                        {"message": f"Failed to send OTP: {email_response}"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Store OTP in the database for verification later
                user.otp = otp
                user.save()
                logger.info(f"OTP stored for user {user.email}")

                return Response(
                    {
                        "message": "User registered successfully. OTP sent to your email.",
                        "user": serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            logger.error(f"User registration failed: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

class OTPVerificationView(APIView):
    """
    API view to verify OTP for the given user using email and OTP.
    """

    def post(self, request, *args, **kwargs):
        try:
            serializer = OTPVerificationSerializer(data=request.data)
            if serializer.is_valid():
                email = serializer.validated_data["email"]
                otp = serializer.validated_data["otp"]
                logger.info(f"Verifying OTP for email: {email}")

                # Retrieve user by email
                try:
                    user = User.objects.get(email=email)
                    logger.info(f"User found: {user.email} | Role: {user.role}")
                except User.DoesNotExist:
                    logger.error(f"User with email {email} not found.")
                    return Response(
                        {"message": "User not found."}, status=status.HTTP_404_NOT_FOUND
                    )

                # Check if OTP matches
                if user.otp != otp:
                    logger.warning(f"Invalid OTP for user {email}.")
                    return Response(
                        {"message": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST
                    )

                # OTP is valid, mark user as verified
                user.is_verified = True
                user.otp = ""  # Clear OTP after verification
                user.save()
                logger.info(f"User {email} verified successfully.")

                # **Ensure Doctor and Patient profile is created**
                if user.role == "Doctor":
                    self.create_doctor_profile(user)
                elif user.role == "Patient":
                    self.create_patient_profile(user)

                # Generate JWT tokens after OTP verification
                tokens = get_tokens_for_user(user)
                logger.info(f"OTP verification successful for {email}. Tokens generated.")

                return Response(
                    {
                        "message": "OTP verified successfully!",
                        "tokens": tokens,
                    },
                    status=status.HTTP_200_OK,
                )

            logger.error(f"OTP verification failed. Errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
            
    @staticmethod
    def create_doctor_profile(user):
        if user.role == "Doctor":
            logger.info(f"User {user.email} is a doctor. Creating profile...")
            try:
                doctor, created = Doctor.objects.get_or_create(user=user)
                if created:
                    doctor.is_verified = True
                    doctor.save()
                    logger.info(f"Doctor profile created for {user.email}.")

                    # Send doctor profile email content
                    subject = f"Doctor Onboarding Team"
                    body = f"""
                    Dear Admin/Team,

                    A new Doctor has onboarded. Below are the details for your action:

                    **Doctor Details:**
                    - **Doctor ID:** {doctor.id}
                    - **Doctor Name:** {user.get_full_name()}
                    - **Email:** {user.email}
                    - **Phone Number:** {user.phone_number}
                    - **Specialization:** {doctor.specialization}
                    - **Experience:** {doctor.experience}
                    - **Availability:** {doctor.availability}
                    - **Registration Date:** {doctor.created_at}
                    - **Verification Status:** {doctor.is_verified}
                    - **Last Login:** {doctor.last_login}
                    Best regards,  
                    My Health Today Team
                    """

                    message = Mail(
                        from_email="it@my-health.today",
                        to_emails="onboarding-doctor@my-health.today",
                        subject=subject,
                        plain_text_content=body.strip(),
                    )
                    try:
                        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
                        response = sg.send(message)
                        logger.info(f"Doctor profile email sent. Response: {response.status_code}")
                        return response
                    except Exception as email_error:
                        logger.error(f"Failed to send doctor profile email: {str(email_error)}")
                        return str(email_error)
                        
                else:
                    logger.info(f"Doctor profile already exists for {user.email}.")
            except Exception as e:
                logger.error(f"Error creating Doctor profile for {user.email}: {str(e)}")

    @staticmethod
    def create_patient_profile(user):
        if user.role == "Patient":
            logger.info(f"User {user.email} is a patient. Creating profile...")
            try:
                patient, created = Patient.objects.get_or_create(user=user)
                if created:
                    patient.is_verified = True
                    patient.save()
                    logger.info(f"Patient profile created for {user.email}.")

                    # Send patient profile email content
                    subject = f"Patient Onboarding Team"
                    body = f"""
                    Dear Admin/Team,

                    A new Patient has onboarded. Below are the details for your action:

                    **Patient Details:**
                    - **Patient ID:** {patient.id}
                    - **Patient Name:** {user.get_full_name()}
                    - **Email:** {user.email}
                    - **Phone Number:** {user.phone_number}
                    - **Date of Birth:** {user.dob}
                    - **Country:** {user.country}
                    - **City:** {user.city}
                    - **Registration Date:** {patient.created_at}
                    - **Verification Status:** {patient.is_verified}
                    - **Last Login:** {patient.last_login}
                    Best regards,  
                    My Health Today Team
                    """

                    message = Mail(
                        from_email="it@my-health.today",
                        to_emails="onboarding-patient@my-health.today",
                        subject=subject,
                        plain_text_content=body.strip(),
                    )
                    try:
                        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
                        response = sg.send(message)
                        logger.info(f"Patient profile email sent. Response: {response.status_code}")
                        return response
                    except Exception as email_error:
                        logger.error(f"Failed to send patient profile email: {str(email_error)}")
                        return str(email_error)

                else:
                    logger.info(f"Patient profile already exists for {user.email}.")
            except Exception as e:
                logger.error(f"Error creating Patient profile for {user.email}: {str(e)}")

class SignInView(APIView):
    """
    API view for user sign-in and account activation.
    """

    def post(self, request, *args, **kwargs):
        try:
            logger.info("Sign-in attempt")
            serializer = SignInSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.validated_data["user"]
                logger.info(f"User {user.email} authenticated successfully.")

                # Generate JWT tokens
                tokens = get_tokens_for_user(user)
                logger.info(f"Tokens generated for user {user.email}.")

                return Response(
                    {
                        "message": "Login successful.",
                        "user": {
                            "id": user.id,
                            "email": user.email,
                            "first_name": user.first_name,
                            "last_name": user.last_name,
                            "role": user.role,
                            "is_verified": user.is_verified,
                        },
                        "tokens": tokens,
                    },
                    status=status.HTTP_200_OK,
                )

            logger.warning("Sign-in failed. Invalid credentials.")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class LogoutView(APIView):
    """
    API view for user logout. Invalidates the refresh token and reverts role if switched.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            user = request.user

            # Revert role if temporarily switched
            if user.is_doctor_switched:
                user.role = 'Doctor'
                user.is_doctor_switched = False
                user.save(update_fields=['role', 'is_doctor_switched'])

            refresh_token = request.data.get("refresh")
            if not refresh_token:
                logger.warning("Logout failed: Refresh token not provided.")
                return Response(
                    {"message": "Refresh token is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            token = RefreshToken(refresh_token)
            token.blacklist()  # Blacklist the refresh token

            logger.info(f"User {user.email} logged out successfully and role reverted if switched.")
            return Response(
                {"message": "Logout successful."},
                status=status.HTTP_205_RESET_CONTENT,
            )

        except TokenError as e:
            logger.error(f"Invalid token during logout: {str(e)}")
            return Response(
                {"message": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.exception("Unexpected error during logout: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ForgotPasswordView(APIView):
    """
    API view for handling forgot password requests using SendGrid dynamic templates.
    """

    def generate_otp(self):
        """
        Generate a 6-digit OTP.
        """
        otp = str(random.randint(100000, 999999))
        logger.info(f"Generated OTP: {otp}")
        return otp

    def send_otp_email(self, email, otp, name=None):
        """
        Send the OTP to the user's email using SendGrid.
        """
        logger.info(f"Sending OTP to {email} using dynamic template...")

        # Prepare message
        message = Mail()
        message.from_email = 'no-reply@my-health.today'
        message.template_id = 'd-57e53ebd7031463c95856cacfc09d52b'

        # Personalization with dynamic data
        personalization = Personalization()
        personalization.add_to(To(email))
        personalization.dynamic_template_data = {
            "name": name or "User",  # fallback if name is None
            "otp": otp,
        }
        message.add_personalization(personalization)

        try:
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            response = sg.send(message)
            logger.info(
                f"OTP email sent successfully to {email}. Response: {response.status_code}"
            )
            return response
        except Exception as e:
            logger.error(f"Failed to send OTP email to {email}: {str(e)}")
            return str(e)

    def post(self, request, *args, **kwargs):
        """
        Handle forgot password request.
        """
        email = request.data.get("email")
        logger.info(f"Received forgot password request for email: {email}")

        # Check if user exists with the provided email
        try:
            user = User.objects.get(email=email)
            logger.info(f"User found for email: {email}")
        except User.DoesNotExist:
            logger.error(f"No user found with email: {email}")
            return Response(
                {"message": "No user found with this email."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Generate and send OTP
        otp = self.generate_otp()
        email_response = self.send_otp_email(email, otp, name=user.first_name)

        if isinstance(email_response, str):
            logger.error(f"Failed to send OTP to {email}. Error: {email_response}")
            return Response(
                {"message": f"Failed to send OTP: {email_response}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Store OTP in user's model
        user.otp = otp  # Custom User model with 'otp' field
        user.save()
        logger.info(f"OTP stored successfully for user {email}")

        return Response(
            {"message": "OTP sent successfully to your email."},
            status=status.HTTP_200_OK,
        )

class ResetPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Password reset successful!"}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(APIView):
    """
    API view to handle password change with OTP verification.
    """
    permission_classes = [IsAuthenticated]

    def send_otp_email(self, email, otp, name=None):
        """
        Send OTP via SendGrid using a dynamic email template.
        """
        message = Mail()
        message.from_email = 'no-reply@my-health.today'
        message.template_id = 'd-6cda674d2e124575b8c8a45e88b3596b'
        
        personalization = Personalization()
        personalization.add_to(To(email))
        personalization.dynamic_template_data = {
            "name": name or "User",
            "otp": otp,
            "purpose": "Change Password"  # Optional additional context for the email
        }
        message.add_personalization(personalization)

        try:
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            response = sg.send(message)
            logger.info(f"Dynamic OTP email sent to {email}. Status: {response.status_code}")
            return response
        except Exception as e:
            logger.error(f"Failed to send OTP email: {str(e)}")
            return str(e)

    def post(self, request, *args, **kwargs):
        """
        User provides old password & new password, OTP is sent to email.
        """
        try:
            user = request.user
            old_password = request.data.get("old_password")
            new_password = request.data.get("new_password")

            # Validate required fields
            if not old_password or not new_password:
                return Response(
                    {"message": "Old password and new password are required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Validate current password
            if not user.check_password(old_password):
                return Response(
                    {"message": "Old password is incorrect."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Enforce password complexity policies
            if len(new_password) < 8:
                return Response({"message": "Password must be at least 8 characters long."}, status=status.HTTP_400_BAD_REQUEST)
            if not re.search(r'[A-Za-z]', new_password):
                return Response({"message": "Password must contain at least one letter."}, status=status.HTTP_400_BAD_REQUEST)
            if not re.search(r'[0-9]', new_password):
                return Response({"message": "Password must contain at least one number."}, status=status.HTTP_400_BAD_REQUEST)
            if not re.search(r'[@$!%*?&]', new_password):
                return Response({"message": "Password must contain at least one special character."}, status=status.HTTP_400_BAD_REQUEST)

            # Generate OTP and persist temporarily
            otp_code = str(random.randint(100000, 999999))
            user.otp = otp_code
            user.otp_created_at = timezone.now()
            user.temp_new_password = new_password
            user.save()

            # Dispatch dynamic template OTP
            send_result = self.send_otp_email(user.email, otp_code, name=user.first_name)
            if isinstance(send_result, str):
                return Response({"message": "Failed to send OTP. Try again later."}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"message": "OTP sent to your email."}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Error processing change password request: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
            
    def put(self, request, *args, **kwargs):
        """
        User enters OTP, If valid, update the password immediately.
        """
        try:
            user = request.user
            otp = request.data.get("otp")

            if not otp:
                return Response({"message": "OTP is required."}, status=status.HTTP_400_BAD_REQUEST)

            # Check if OTP is expired (valid for 10 minutes)
            if user.otp_created_at is None:
                return Response({"message": "OTP not generated yet. Please request a new OTP."}, status=status.HTTP_400_BAD_REQUEST)

            otp_expiry_time = user.otp_created_at + timedelta(minutes=10)
            if timezone.now() > otp_expiry_time:
                return Response({"message": "OTP has expired. Request a new one."}, status=status.HTTP_400_BAD_REQUEST)

            # Verify OTP
            if user.otp != otp:
                return Response({"message": "Invalid OTP. Please try again."}, status=status.HTTP_400_BAD_REQUEST)

            # Update password immediately
            user.set_password(request.data.get("new_password"))
            user.otp = ""
            user.otp_created_at = None
            user.save()
            logger.info(f"Password changed successfully for user: {user.email}")

            # Authenticate and log the user in after updating the password
            user = authenticate(request, email=user.email, password=request.data.get("new_password"))
            if user is not None:
                login(request, user)  # Log the user in if authenticated successfully
                return Response({"message": "Password updated and user logged in successfully."}, status=status.HTTP_200_OK)
            else:
                return Response({"message": "Invalid email or password."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

class AccountDeactivateDeleteView(APIView):
    """
    API view to deactivate or delete the user's account.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Deactivate the authenticated user's account.
        """
        try:
            user = request.user
            logger.info(f"User {user.email} requested account deactivation.")

            # Deactivate the account
            user.is_active = False
            user.save()

            logger.info(f"User {user.email} account deactivated successfully.")
            return Response(
                {"message": "Account deactivated successfully."},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def delete(self, request, *args, **kwargs):
        """
        Delete the authenticated user's account (Doctor) and all related data.
        """
        user = request.user
        logger.info(f"User {user.email} requested account deletion.")

        try:
            # Check if the logged-in user is a doctor
            if user.role != "Doctor":
                logger.warning(f"Unauthorized deletion attempt by {user.email}.")
                return Response(
                    {"message": "You are not authorized to perform this action."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Delete related data if the user is a doctor
            if hasattr(user, "doctor"):
                doctor = user.doctor
                logger.info(
                    f"Deleting doctor profile and related data for {user.email}."
                )

                # 1. Delete appointments and related data
                if hasattr(doctor, "appointments"):
                    for appointment in doctor.appointments.all():
                        if hasattr(appointment, "consultation_summary"):
                            appointment.consultation_summary.delete()
                        if hasattr(appointment, "prescriptions"):
                            appointment.prescriptions.all().delete()
                        if hasattr(appointment, "doctors_notes"):
                            appointment.doctors_notes.all().delete()
                        appointment.delete()
                    logger.info(
                        f"Appointments and related data deleted for {user.email}."
                    )

                # 2. Delete doctor's account details
                if hasattr(doctor, "account_details"):
                    doctor.account_details.all().delete()

                # 3. Delete transactions
                if hasattr(doctor, "transactions"):
                    doctor.transactions.all().delete()

                # 4. Delete reviews
                if hasattr(doctor, "reviews"):
                    doctor.reviews.all().delete()

                # 5. Delete education, media, and skills
                if hasattr(doctor, "education"):
                    doctor.education.all().delete()
                if hasattr(doctor, "media"):
                    doctor.media.all().delete()
                if hasattr(doctor, "skills"):
                    doctor.skills.clear()

                # 6. Delete the Doctor object
                doctor.delete()
                logger.info(f"Doctor profile deleted for {user.email}.")

            # Delete the user
            user.delete()
            logger.info(f"User {user.email} account deleted successfully.")

            return Response(
                {
                    "message": "Doctor account and all related data deleted successfully."
                },
                status=status.HTTP_204_NO_CONTENT,
            )
        except Exception as e:
            logger.error(f"Error deleting account for {user.email}: {str(e)}")
            return Response(
                {"message": f"Error deleting account: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ResendOTPView(APIView):
    """
    API view for resending an OTP if the previous OTP has expired or is invalid.
    """

    def generate_otp(self):
        """
        Generate a 6-digit OTP.
        """
        return str(random.randint(100000, 999999))

    def send_otp_email(self, email, otp):
        """
        Send OTP using a dynamic SendGrid template.
        """
        message = Mail(
            from_email='no-reply@my-health.today',
            to_emails=email,
        )
        message.template_id = 'd-7c64dfda916a4a2b801af519ccee57c7'
        message.dynamic_template_data = {
            "otp": otp,
            "support_email": "support@example.com",  # optional placeholder
        }

        try:
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            response = sg.send(message)
            return response
        except Exception as e:
            logger.error(f"SendGrid Error: {str(e)}")
            return str(e)

    def post(self, request, *args, **kwargs):
        """
        Handle resend OTP request.
        """
        try:
            email = request.data.get("email")
            if not email:
                return Response(
                    {"message": "Email is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # Check if user exists with the provided email
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                logger.warning(f"OTP resend requested for non-existing email: {email}")
                return Response(
                    {
                        "message": "If the email exists, a new OTP will be sent."
                    },  # Generic response to avoid email enumeration
                    status=status.HTTP_200_OK,
                )
            # Check if the user has requested an OTP recently (within 2 minutes)
            if user.otp_created_at and now() - user.otp_created_at < timedelta(minutes=2):
                return Response(
                    {"message": "Please wait a few minutes before requesting a new OTP."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,  # Rate limiting status code
                )

            # Generate and send a new OTP
            new_otp = self.generate_otp()
            email_response = self.send_otp_email(email, new_otp)

            if email_response is None:
                return Response(
                    {"message": "Failed to resend OTP. Please try again later."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Update the user's OTP and set the timestamp
            user.otp = new_otp
            user.otp_created_at = now()
            user.save()

            logger.info(f"OTP resent successfully to {email}")

            return Response(
                {
                    "message": "If the email exists, a new OTP has been sent successfully."
                },  # Consistent response
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class GoogleLoginView(APIView):
    """
    API view for Google-based authentication.
    Handles login or registration using a Google OAuth2 token.
    """

    def post(self, request):
        """
        Handles POST requests for Google login.
        """
        try:
            logger.info("Received Google login request.")

            # Validate the input data
            social_login_serializer = SocialLoginSerializer(data=request.data)
            if not social_login_serializer.is_valid():
                logger.warning("Invalid input data: %s", social_login_serializer.errors)
                return Response(
                    social_login_serializer.errors, status=status.HTTP_400_BAD_REQUEST
                )

            token = request.data.get("token")
            client_id = "853181483027-b3pgc8d9m5vq2l83f4hu10mu5se690gi.apps.googleusercontent.com"

            if not token:
                logger.warning("Token is missing in the request.")
                return Response(
                    {"error": "Token is required"}, status=status.HTTP_400_BAD_REQUEST
                )

            # Validate the Google token
            validation_result = validate_google_id_token(token, client_id)
            if validation_result["status"] == "valid":
                user_info = validation_result["user_info"]
                logger.info(
                    "Google token validation successful for email: %s",
                    user_info.get("email"),
                )

                # Extract user information
                email = user_info.get("email")
                full_name = user_info.get("name", "")
                first_name = user_info.get("given_name", "")
                last_name = user_info.get("family_name", "")
                role = request.data.get("role", None)

                if not first_name or not last_name:
                    name_parts = full_name.split()
                    first_name = name_parts[0] if name_parts else ""
                    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

                # Retrieve or create the user
                user, created = User.objects.get_or_create(email=email)
                if created:
                    logger.info("New user created: %s", email)
                    user.first_name = first_name
                    user.last_name = last_name
                    if role:
                        user.role = role
                    user.save()
                else:
                    logger.info("Existing user logged in: %s", email)

                # Generate JWT tokens
                jwt_token = get_tokens_for_user(user)
                logger.info("JWT token generated for user: %s", email)

                return Response(
                    {"message": "Login successful", "token": jwt_token},
                    status=status.HTTP_200_OK,
                )

            elif validation_result["status"] == "expired":
                logger.warning("Expired token received for Google login.")
                return Response(
                    {"error": "Token is expired"}, status=status.HTTP_400_BAD_REQUEST
                )
            else:
                logger.error(
                    "Google token validation failed: %s", validation_result["message"]
                )
                return Response(
                    {"error": validation_result["message"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            logger.exception("Unexpected error in Google login: %s", str(e))
            return Response(
                {"error": "An error occurred. Please try again later."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AppleLoginView(APIView):
    """
    API endpoint for handling Sign in with Apple via POST /auth/apple/
    """

    def post(self, request):
        code = request.data.get('code')
        if not code:
            return Response({"error": "Authorization code is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Step 1: Generate client secret
            client_secret = self._generate_client_secret()

            # Step 2: Exchange code for tokens
            token_response = self._exchange_code_for_token(code, client_secret)
            id_token = token_response.get('id_token')

            if not id_token:
                return Response({"error": "No ID token received from Apple."}, status=status.HTTP_400_BAD_REQUEST)

            # Step 3: Decode and verify ID token
            user_info = self._decode_id_token(id_token)

            # Step 4: Create or authenticate user
            user = self._get_or_create_user(user_info)

            # Step 5: Generate DRF auth token
            token, _ = Token.objects.get_or_create(user=user)

            return Response({"token": token.key}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _generate_client_secret(self):
        headers = {
            "kid": settings.APPLE_KEY_ID,
            "alg": "ES256"
        }
        payload = {
            "iss": settings.APPLE_TEAM_ID,
            "iat": int(time.time()),
            "exp": int(time.time()) + 86400 * 180,
            "aud": "https://appleid.apple.com",
            "sub": settings.APPLE_CLIENT_ID
        }

        client_secret = jwt.encode(
            payload,
            settings.APPLE_PRIVATE_KEY,
            algorithm="ES256",
            headers=headers
        )
        return client_secret

    def _exchange_code_for_token(self, code, client_secret):
        data = {
            "client_id": settings.APPLE_CLIENT_ID,
            "client_secret": client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.APPLE_REDIRECT_URI,
        }

        response = requests.post("https://appleid.apple.com/auth/token", data=data)
        if response.status_code != 200:
            raise Exception(f"Apple token endpoint error: {response.content}")
        return response.json()

    def _decode_id_token(self, id_token):
        decoded = jwt.decode(id_token, options={"verify_signature": False})
        return decoded

    def _get_or_create_user(self, user_info):
        sub = user_info.get("sub")
        email = user_info.get("email")

        if not sub:
            raise Exception("Apple user ID (sub) missing.")

        user, created = User.objects.get_or_create(apple_sub=sub, defaults={
            "email": email if email else f"{sub}@appleid.apple.com",
            "username": email if email else f"user_{sub[:8]}",
            "is_active": True
        })

        return user

class UpdateUserProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def patch(self, request):
        try:
            logger.info(f"User profile update initiated by: {request.user.email}")

            serializer = UserProfileUpdateSerializer(
                instance=request.user,
                data=request.data,
                partial=True
            )

            if serializer.is_valid():
                serializer.save()
                user = request.user
                doctor = getattr(user, "doctor", None)

                # Load default serialized data
                response_data = serializer.data

                # Clinic handling logic
                if request.data.get("clinic") == "other":
                    response_data["work_place"] = "other"

                    clinic_name = request.data.get("clinic_name")
                    clinic_location = request.data.get("clinic_location")
                    clinic_website = request.data.get("clinic_website")

                    # Inject clinic info directly into response
                    response_data["clinic_name"] = clinic_name
                    response_data["clinic_location"] = clinic_location
                    response_data["clinic_website"] = clinic_website

                    # Save to DB if applicable
                    if doctor and clinic_name and clinic_location:
                        OtherClinic.objects.update_or_create(
                            doctor=doctor,
                            clinic_name=clinic_name,
                            defaults={
                                "address": clinic_location,
                                "website": clinic_website
                            }
                        )

                        # Optional: Notify via email
                        try:
                            html_content = f"""
                            <strong>Doctor:</strong> {user.get_full_name()}<br>
                            <strong>Email:</strong> {user.email}<br>
                            <strong>Clinic Name:</strong> {clinic_name}<br>
                            <strong>Location:</strong> {clinic_location}<br>
                            <strong>Website:</strong> {clinic_website or 'N/A'}
                            """
                            message = Mail(
                                from_email='no-reply@my-health.today',
                                to_emails='new-clinic@my-health.today',
                                subject='New Other Clinic Added',
                                html_content=html_content
                            )
                            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
                            sg.send(message)
                        except Exception as email_err:
                            logger.warning(f"SendGrid failed: {email_err}")

                else:
                    # Ensure work_place is returned as ID and no extra clinic fields are present
                    response_data["other_clinic"] = None
                    response_data.pop("clinic_name", None)
                    response_data.pop("clinic_location", None)
                    response_data.pop("clinic_website", None)

                return Response({
                    "message": "Profile updated successfully.",
                    "data": response_data
                }, status=status.HTTP_200_OK)

            logger.warning(f"Validation failed: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as ex:
            logger.exception("Critical failure in UpdateUserProfileAPIView.")
            return Response(
                {"message": f"Unexpected server error: {str(ex)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DeleteProfilePictureAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        try:
            user = request.user

            if not user.profile_picture:
                return Response(
                    {"message": "No profile picture found."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Delete the profile picture
            user.profile_picture.delete(save=False)  # Deletes file from storage
            user.profile_picture = None  # Remove reference in DB
            user.save()

            logger.info(f"Profile picture deleted for user: {user.email}")

            return Response(
                {"message": "Profile picture deleted successfully."},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.exception(f"Error deleting profile picture: {str(e)}")
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
            
class GetUserProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            logger.info(
                "Received request to fetch user profile for user: %s",
                request.user.email,
            )

            if not request.user.is_authenticated:
                logger.warning("Unauthorized access attempt.")
                raise AuthenticationFailed("User is not authenticated.")

            user = request.user
            role = user.role

            if not role:
                return Response({"message": "User role is not assigned."}, status=status.HTTP_400_BAD_REQUEST)

            serializer = UserProfileSerializer(user)
            data = serializer.data

            if role == "Doctor":
                logger.info("Returning doctor profile.")

                clinic = user.work_place
                if clinic is None:
                    try:
                        doctor = user.doctor
                        other_clinic = OtherClinic.objects.get(doctor=doctor)
                        data["other_clinic"] = OtherClinicSerializer(other_clinic).data
                    except (Doctor.DoesNotExist, OtherClinic.DoesNotExist):
                        data["other_clinic"] = {}
                    data["clinic_data"] = {}
                else:
                    data["clinic_data"] = ClinicInfoSerializer(clinic).data
                    data["other_clinic"] = {}

                return Response({
                    "message": "Doctor profile.",
                    "data": data,
                }, status=status.HTTP_200_OK)

            elif role == "Patient":
                return Response({
                    "message": "Patient profile.",
                    "data": data
                }, status=status.HTTP_200_OK)

            return Response({
                "message": "Invalid role assigned to user."
            }, status=status.HTTP_400_BAD_REQUEST)

        except AuthenticationFailed as e:
            return Response({"message": str(e)}, status=status.HTTP_401_UNAUTHORIZED)

        except Exception as e:
            logger.exception("Error fetching user profile: %s", str(e))
            return Response({"message": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)



class UserDeviceTokenAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def put(self ,request):
        try:
            user_id = request.data.get('user_id')
            firebase_token = request.data.get("device_token", None)
            
            if not user_id or not firebase_token:
                return Response({'message': 'User ID and device token are required.'}, status=status.HTTP_400_BAD_REQUEST)
            
            if user_id != request.user.id:
                return Response({'message': 'User ID does not match the authenticated user.'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:        
                 user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return Response({'message': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)
            
            if str(user.device_token) == str(firebase_token):
                return Response({'message': 'Device token already exists.'}, status=status.HTTP_400_BAD_REQUEST)
            
            user.device_token = firebase_token
            user.save()
            return Response({'message': 'Device token updated successfully.'}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
