import logging
import random
import re
from datetime import timedelta

from django.conf import settings
from django.utils.timezone import now
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from social_core.backends.apple import AppleIdAuth
from social_django.utils import load_strategy

from authify.utils import validate_google_id_token
from doctors.models import Doctor
from users.models import User

from .serializers import (
    OTPVerificationSerializer,
    RegistrationSerializer,
    SignInSerializer,
    SocialLoginSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
)

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

    def send_otp_email(self, email, otp):
        """
        Send the OTP to the user's email via SendGrid.
        """
        logger.info(f"Sending OTP to email: {email}")
        message = Mail(
            from_email=settings.SENDGRID_FROM_EMAIL,
            to_emails=email,
            subject="Your OTP Code",
            plain_text_content=f"Your OTP code is {otp}",
        )

        try:
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            response = sg.send(message)
            logger.info(f"OTP sent successfully to {email}")
            return response
        except Exception as e:
            logger.error(f"Failed to send OTP to {email}: {str(e)}")
            return str(e)

    def post(self, request, *args, **kwargs):
        logger.info("User sign-up request received.")
        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            logger.info(f"User registered successfully: {user.email}")

            # Generate OTP
            otp = self.generate_otp()

            # Send OTP to user's email
            email_response = self.send_otp_email(user.email, otp)

            if isinstance(email_response, str):
                logger.error(f"Failed to send OTP to {user.email}: {email_response}")
                return Response(
                    {"message": f"Failed to send OTP: {email_response}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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


class OTPVerificationView(APIView):
    """
    API view to verify OTP for the given user using email and OTP.
    """

    def post(self, request, *args, **kwargs):
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
            user.otp = None  # Clear OTP after verification
            user.save()
            logger.info(f"User {email} verified successfully.")

            # **Ensure Doctor profile is created**
            self.create_doctor_profile(user)

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

    def create_doctor_profile(self, user):
        if user.role == "Doctor":
            logger.info(
                f"User {user.email} is a doctor. Attempting to create Doctor profile..."
            )
            try:
                doctor, created = Doctor.objects.get_or_create(user=user)
                if created:
                    doctor.is_verified = (
                        True  # Mark doctor as verified after OTP verification
                    )
                    doctor.save()
                    logger.info(f"Doctor profile created for user {user.email}.")
                else:
                    logger.info(f"Doctor profile already exists for user {user.email}.")
            except Exception as e:
                logger.error(
                    f"Error creating Doctor profile for user {user.email}: {str(e)}"
                )
                return Response(
                    {"message": "Error creating Doctor profile."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            logger.info(
                f"User {user.email} is not a doctor, skipping Doctor profile creation."
            )


class SignInView(APIView):
    """
    API view for user sign-in and account activation.
    """

    def post(self, request, *args, **kwargs):
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


class ForgotPasswordView(APIView):
    """
    API view for handling forgot password requests.
    Generates an OTP and sends it to the user's registered email for verification.
    """

    def generate_otp(self):
        """
        Generate a 6-digit OTP.
        """
        otp = str(random.randint(100000, 999999))
        logger.info(f"Generated OTP: {otp}")
        return otp

    def send_otp_email(self, email, otp):
        """
        Send the OTP to the user's email using SendGrid.
        """
        message = Mail(
            from_email=settings.SENDGRID_FROM_EMAIL,
            to_emails=email,
            subject="Password Reset OTP",
            plain_text_content=f"Your OTP for password reset is {otp}. It is valid for 10 minutes.",
        )

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
        email_response = self.send_otp_email(email, otp)
        if isinstance(email_response, str):
            logger.error(f"Failed to send OTP to {email}. Error: {email_response}")
            return Response(
                {"message": f"Failed to send OTP: {email_response}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Store OTP in user's model
        user.otp = otp  # Custom User model with 'otp' field
        user.save()
        logger.info(f"OTP stored successfully for user {email}")

        return Response(
            {"message": "OTP sent successfully to your email."},
            status=status.HTTP_200_OK,
        )


class VerifyEmailAndGenerateTokensView(APIView):
    """
    API view to verify email using OTP and generate access and refresh tokens.
    """

    def post(self, request, *args, **kwargs):
        """
        Verify OTP and email, then generate access and refresh tokens.
        """
        email = request.data.get("email", "").lower().strip()
        otp = request.data.get("otp")

        logger.info(f"Received OTP verification request for email: {email}")

        # Validate input fields
        if not all([email, otp]):
            logger.warning("Missing email or OTP in request.")
            return Response(
                {"message": "Email and OTP are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get the user
        try:
            user = User.objects.get(email=email)
            logger.info(f"User found: {user.email} | Role: {user.role}")
        except User.DoesNotExist:
            logger.error(f"User not found for email: {email}")
            return Response(
                {"message": "Invalid email or OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if OTP matches
        if user.otp != otp:
            logger.warning(f"Invalid OTP attempt for user {email}.")
            return Response(
                {"message": "Invalid email or OTP."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Clear OTP after successful verification
        user.otp = None
        user.save()
        logger.info(f"OTP verified successfully for {email}.")

        # Generate access and refresh tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        logger.info(f"Tokens generated successfully for {email}.")

        return Response(
            {
                "message": "Email verified successfully.",
                "access_token": access_token,
                "refresh_token": str(refresh),
            },
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    """
    API view for changing the password after email verification.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Change the password for the authenticated user.
        """
        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")
        user = request.user

        logger.info(f"Password change request received for user: {user.email}")

        # Validate the provided data
        if not current_password or not new_password:
            logger.warning(f"User {user.email} provided incomplete password data.")
            return Response(
                {"message": "Current password and new password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Password strength validation
        if len(new_password) < 8:
            logger.warning(
                f"User {user.email} provided a weak password (less than 8 characters)."
            )
            return Response(
                {"message": "New password must be at least 8 characters long."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not re.search(r"[A-Za-z]", new_password):
            logger.warning(f"User {user.email} provided a password without letters.")
            return Response(
                {"message": "New password must contain at least one letter."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not re.search(r"[0-9]", new_password):
            logger.warning(f"User {user.email} provided a password without numbers.")
            return Response(
                {"message": "New password must contain at least one number."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not re.search(r"[@$!%*?&]", new_password):
            logger.warning(
                f"User {user.email} provided a password without special characters."
            )
            return Response(
                {
                    "message": "New password must contain at least one special character (e.g., @$!%*?&)."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if the current password matches
        if not user.check_password(current_password):
            logger.error(f"User {user.email} provided an incorrect current password.")
            return Response(
                {"message": "Current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Change the user's password
        user.set_password(new_password)
        user.save()
        logger.info(f"Password changed successfully for user: {user.email}")

        return Response(
            {"message": "Password changed successfully."},
            status=status.HTTP_200_OK,
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
        Send the OTP to the user's email using SendGrid.
        """
        message = Mail(
            from_email=settings.SENDGRID_FROM_EMAIL,
            to_emails=email,
            subject="Password Reset OTP - Resend",
            plain_text_content=f"Your new OTP for password reset is {otp}. It is valid for 10 minutes.",
        )

        try:
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            response = sg.send(message)
            return response
        except Exception as e:
            logger.error(f"Failed to send OTP email to {email}: {str(e)}")
            return None  # Return None instead of error details for security reasons

    def post(self, request, *args, **kwargs):
        """
        Handle resend OTP request.
        """
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
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AppleLoginView(APIView):
    """
    API view for Apple-based authentication.
    Handles login or registration using an Apple ID token.
    """

    def post(self, request):
        """
        Handles POST requests for Apple login.
        """
        logger.info("Received Apple login request.")
        strategy = load_strategy(request)  # Load the social authentication strategy
        token = request.data.get("token")  # Get the Apple ID token from the request

        if not token:
            logger.warning("Token is missing in the request.")
            return Response(
                {"error": "Token is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Use the Apple ID backend to authenticate the user
            backend = AppleIdAuth(strategy=strategy)
            user = backend.do_auth(token)

            if user:
                logger.info("Apple authentication successful for user: %s", user.email)
                # Generate tokens for the authenticated user
                jwt_token = get_tokens_for_user(user)
                return Response(
                    {"message": "Login successful", "token": jwt_token},
                    status=status.HTTP_200_OK,
                )

            # Return error if authentication fails
            logger.warning("Apple authentication failed.")
            return Response(
                {"error": "Authentication failed"}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception("Unexpected error during Apple login: %s", str(e))
            return Response(
                {"error": "An error occurred. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class UpdateUserProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def patch(self, request):
        logger.info(
            "Received request to update user profile for user: %s", request.user.email
        )
        serializer = UserProfileUpdateSerializer(
            instance=request.user, data=request.data, partial=True
        )

        if serializer.is_valid():
            user = serializer.save()
            logger.info("User profile updated successfully: %s", request.user.email)
            user_data = {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "dob": user.dob,
                "gender": user.gender,
                "phone_number": user.phone_number,
                "bio": user.bio,
                "country": user.country,
                "city": user.city,
                "languages": user.languages,
                "work_place": user.work_place,
                "expertise": user.expertise,
                "professional_stat": user.professional_stat,
                "working_time": user.working_time,
                "profile_picture": (
                    user.profile_picture.url if user.profile_picture else None
                ),
            }
            return Response(
                {"message": "Profile updated successfully.", "data": user_data},
                status=status.HTTP_200_OK,
            )

        logger.warning(
            "Profile update failed for user: %s, errors: %s",
            request.user.email,
            serializer.errors,
        )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
                logger.warning(
                    "User role is not assigned for user: %s", request.user.email
                )
                return Response(
                    {"message": "User role is not assigned."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer = UserProfileSerializer(user)
            data = serializer.data

            if role == "Patient":
                logger.info(
                    "Returning patient profile for user: %s", request.user.email
                )
                return Response(
                    {"message": "Patient profile.", "data": data},
                    status=status.HTTP_200_OK,
                )
            elif role == "Doctor":
                logger.info("Returning doctor profile for user: %s", request.user.email)
                return Response(
                    {"message": "Doctor profile.", "data": data},
                    status=status.HTTP_200_OK,
                )
            else:
                logger.error("Invalid role assigned to user: %s", request.user.email)
                return Response(
                    {"message": "Invalid role assigned to user."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except AuthenticationFailed as e:
            logger.warning("Authentication failed: %s", str(e))
            return Response({"message": str(e)}, status=status.HTTP_401_UNAUTHORIZED)

        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
