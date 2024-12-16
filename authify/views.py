from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import update_last_login
from django.contrib.auth.tokens import (
    PasswordResetTokenGenerator,
    default_token_generator,
)
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from social_core.backends.apple import AppleIdAuth
from social_core.backends.google import GoogleOAuth2
from social_django.utils import load_strategy
import random
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from .serializers import RegistrationSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.sessions.models import Session
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model

from users.models import User
import random
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from django.conf import settings
from .serializers import RegistrationSerializer, SignInSerializer, OTPVerificationSerializer


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
            subject='Your OTP Code',
            plain_text_content=f'Your OTP code is {otp}',
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
    API view to verify OTP for user registration.
    """

    def post(self, request, *args, **kwargs):
        serializer = OTPVerificationSerializer(data=request.data)
        if serializer.is_valid():
            otp = serializer.validated_data['otp']
            user = request.user  # Assuming the user is already authenticated or another way to identify the user

            try:
                # Check if OTP exists and is still valid
                if user.otp != otp:
                    return Response(
                        {"message": "Invalid OTP."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Check if OTP expired (e.g., 5 minutes)
                otp_timestamp = user.date_joined  # Assuming OTP was set when user was created
                if (timezone.now() - otp_timestamp).total_seconds() > 300:  # Expire OTP after 5 minutes
                    return Response(
                        {"message": "OTP has expired. Please request a new one."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # OTP is valid, now activate the user's account
                user.is_verified = True
                user.save()

                return Response(
                    {"message": "OTP verified successfully!"},
                    status=status.HTTP_200_OK,
                )
            except User.DoesNotExist:
                return Response(
                    {"message": "User does not exist."},
                    status=status.HTTP_400_BAD_REQUEST,
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

class OTPVerificationView(APIView):
    """
    API view to verify OTP for user registration.
    """

    def post(self, request, *args, **kwargs):
        serializer = OTPVerificationSerializer(data=request.data)
        if serializer.is_valid():
            otp = serializer.validated_data['otp']
            user = request.user
            email = user.email
            
            try:
                # Check if OTP exists and is still valid
                user_otp = User.objects.get(email=email, otp=otp)
                if (timezone.now() - user_otp.created_at).total_seconds() > 300:  # Expire OTP after 5 minutes
                    return Response(
                        {"message": "OTP has expired. Please request a new one."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # OTP is valid, now activate the user's account or proceed with your logic
                # For example, you could set a field like user.is_active = True
                user.is_verified = True
                user.save()

                return Response(
                    {"message": "OTP verified successfully!"},
                    status=status.HTTP_200_OK,
                )
            except User.DoesNotExist:
                return Response(
                    {"message": "Invalid OTP."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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


# Token generator for password reset
token_generator = PasswordResetTokenGenerator()


class ResetPasswordView(APIView):
    """
    API for resetting the password using the email and reset token from the headers.
    """

    permission_classes = [AllowAny]  # Allow any user to access this endpoint

    def patch(self, request):
        # Get email and token from headers
        email = request.headers.get("email")
        print(email, "--------------------------------------Email")
        token = request.headers.get("token")
        print(token, "--------------------------------------Token")

        if not email or not token:
            return Response(
                {"error": "Email and token must be provided in the headers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate user by email
        user = get_object_or_404(get_user_model(), email=email)
        print(user, type(user), "-----------------------------user>")
        
        # Check if the token is valid
        if not default_token_generator.check_token(user, token):
            return Response(
                {"error": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get new password and confirm password
        new_password = request.data.get("new_password")
        print(new_password, "-----------------------------new_password>")
        confirm_password = request.data.get("confirm_password")
        print(confirm_password, "-----------------------------confirm_password>")

        # Check if the passwords match
        if new_password != confirm_password:
            raise ValidationError("Passwords do not match.")

        # Check password strength (basic validation example)
        if len(new_password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")

        # Optionally, add more password complexity checks (e.g., uppercase, special characters)

        # Set the new password after hashing
        user.password = make_password(new_password)
        user.save()

        return Response(
            {"message": "Password has been reset successfully."},
            status=status.HTTP_200_OK,
        )