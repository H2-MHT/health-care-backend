import random

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from social_core.backends.apple import AppleIdAuth
from social_core.backends.google import GoogleOAuth2
from social_django.utils import load_strategy
from users.models import User
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model

from .serializers import (OTPVerificationSerializer, RegistrationSerializer,
                            SignInSerializer)


def get_tokens_for_user(user):
    """
    Generate refresh and access tokens for the given user.

    Args:
        user (User): The user instance for which tokens are generated.

    Returns:
        dict: A dictionary containing 'refresh' and 'access' tokens.
    """
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
        return str(random.randint(100000, 999999))

    def send_otp_email(self, email, otp):
        """
        Send the OTP to the user's email via SendGrid.
        """
        message = Mail(
            from_email=settings.SENDGRID_FROM_EMAIL,
            to_emails=email,
            subject="Your OTP Code",
            plain_text_content=f"Your OTP code is {otp}",
        )

        try:
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            response = sg.send(message)
            return response
        except Exception as e:
            return str(e)

    def post(self, request, *args, **kwargs):
        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Generate OTP
            otp = self.generate_otp()

            # Send OTP to user's email
            email_response = self.send_otp_email(user.email, otp)

            if isinstance(email_response, str):
                return Response(
                    {"message": f"Failed to send OTP: {email_response}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Store OTP in the database for verification later
            user.otp = otp
            user.save()

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            return Response(
                {
                    "message": "User registered successfully. OTP sent to your email.",
                    "user": serializer.data,
                    "tokens": {
                        "refresh": str(refresh),
                        "access": str(refresh.access_token),
                    },
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OTPVerificationView(APIView):
    """
    API view to verify OTP for the currently authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = OTPVerificationSerializer(data=request.data)
        if serializer.is_valid():
            otp = serializer.validated_data["otp"]
            user = request.user  # Get the currently logged-in user

            # Check if OTP matches
            if user.otp != otp:
                return Response(
                    {"message": "Invalid OTP."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # OTP expired (e.g., 5 minutes from `date_joined` or OTP timestamp)
            otp_timestamp = user.date_joined  # OTP sent when user is created
            if (timezone.now() - otp_timestamp).total_seconds() > 300:
                return Response(
                    {"message": "OTP has expired. Please request a new one."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # OTP is valid, verify the user's account
            user.is_verified = True
            user.save()
            return Response(
                {"message": "OTP verified successfully!"},
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SignInView(APIView):
    """
    API view for user sign-in.
    Authenticates the user using the provided username and password
    and generates a JWT token for subsequent requests.
    """

    def post(self, request, *args, **kwargs):
        serializer = SignInSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            tokens = get_tokens_for_user(user)
            return Response(
                {
                    "message": "Login successful.",
                    "user": {
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "role": user.role,
                    },
                    "tokens": tokens,
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

User = get_user_model()

class ForgotPasswordView(APIView):
    """
    API view for handling forgot password requests.
    Generates an OTP and sends it to the user's registered email for verification.
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
            subject="Password Reset OTP",
            plain_text_content=f"Your OTP for password reset is {otp}. It is valid for 10 minutes."
        )

        try:
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            response = sg.send(message)
            return response
        except Exception as e:
            return str(e)

    def post(self, request, *args, **kwargs):
        """
        Handle forgot password request.
        """
        email = request.data.get("email")
        print(email, "-----------------------------email")
        # Check if user exists with the provided email
        try:
            user = User.objects.get(email=email)
            print(user, "-----------------------------user")
        except User.DoesNotExist:
            return Response(
                {"message": "No user found with this email."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Generate and send OTP
        otp = self.generate_otp()
        print(otp, "-----------------------------otp")
        email_response = self.send_otp_email(email, otp)
        print(email_response, "-----------------------------email_response")
        if isinstance(email_response, str):
            return Response(
                {"message": f"Failed to send OTP: {email_response}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Store OTP in user's model
        user.otp = otp  # Custom User model with 'otp' field
        user.save()
        return Response(
            {"message": "OTP sent successfully to your email."},
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    """
    API view for resetting the password after OTP verification.
    """

    def post(self, request, *args, **kwargs):
        """
        Verify OTP and reset the user's password.
        """
        email = request.data.get("email")
        print(email, "-----------------------------email-----1")
        otp = request.data.get("otp")
        print(otp, "-----------------------------otp-----2")
        new_password = request.data.get("new_password")
        print(new_password, "-----------------------------new_password-----3")

        # Validate input fields
        if not all([email, otp, new_password]):
            return Response(
                {"message": "Email, OTP, and new password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Fetch the user
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"message": "No user found with this email."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if OTP matches
        if user.otp != otp:  # Custom User model with 'otp' field
            return Response(
                {"message": "Invalid OTP. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Reset password
        user.set_password(new_password)
        user.otp = None  # Clear OTP after successful reset
        user.save()

        return Response(
            {"message": "Password reset successfully."},
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

        Args:
            request (Request): The HTTP request containing the Google OAuth2 token.

        Returns:
            Response: A success message and a JWT token on successful authentication, or an error on failure.
        """
        strategy = load_strategy(request)  # Load the social authentication strategy
        token = request.data.get(
            "token"
        )  # Get the Google OAuth2 token from the request

        try:
            # Use the Google OAuth2 backend to authenticate the user
            backend = GoogleOAuth2(strategy=strategy)
            user = backend.do_auth(token)
            if user:
                # Generate tokens for the authenticated user
                token = get_tokens_for_user(user)
                return Response(
                    {"message": "Login successful", "token": token},
                    status=status.HTTP_200_OK,
                )
            # Return error if authentication fails
            return Response(
                {"error": "Authentication failed"}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # Catch and return any exceptions that occur
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AppleLoginView(APIView):
    """
    API view for Apple-based authentication.
    Handles login or registration using an Apple ID token.
    """

    def post(self, request):
        """
        Handles POST requests for Apple login.

        Args:
            request (Request): The HTTP request containing the Apple ID token.

        Returns:
            Response: A success message and a JWT token on successful authentication, or an error on failure.
        """
        strategy = load_strategy(request)  # Load the social authentication strategy
        token = request.data.get("token")  # Get the Apple ID token from the request

        try:
            # Use the Apple ID backend to authenticate the user
            backend = AppleIdAuth(strategy=strategy)
            user = backend.do_auth(token)
            if user:
                # Generate tokens for the authenticated user
                token = get_tokens_for_user(user)
                return Response(
                    {"message": "Login successful", "token": token},
                    status=status.HTTP_200_OK,
                )
            # Return error if authentication fails
            return Response(
                {"error": "Authentication failed"}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # Catch and return any exceptions that occur
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
