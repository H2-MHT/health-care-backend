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

from users.models import User

from .serializers import UserSerializer


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

    def post(self, request):
        """
        Handles POST requests for user registration.

        Args:
            request (Request): The HTTP request containing user registration data.

        Returns:
            Response: A success message and a JWT token on successful registration, or errors on failure.
        """
        serializer = UserSerializer(
            data=request.data
        )  # Validate the incoming data using the serializer
        if serializer.is_valid():
            # Save the user instance after validation
            user = serializer.save()
            # Generate tokens for the new user
            token = get_tokens_for_user(user)
            return Response(
                {"message": "User created successfully", "token": token},
                status=status.HTTP_201_CREATED,
            )
        # Return validation errors if any
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SignInView(APIView):
    """
    API view for user sign-in.
    Authenticates the user using the provided username and password
    and generates a JWT token for subsequent requests.
    """

    def post(self, request):
        """
        Handles POST requests for user login.

        Args:
            request (Request): The HTTP request containing username and password.

        Returns:
            Response: A success message and a JWT token on successful authentication, or an error on failure.
        """
        # Extract credentials from the request
        username = request.data.get("username")
        password = request.data.get("password")
        # Authenticate the user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Update the last login timestamp for the user
            update_last_login(None, user)
            # Generate tokens for the authenticated user
            token = get_tokens_for_user(user)
            return Response(
                {"message": "Login successful", "token": token},
                status=status.HTTP_200_OK,
            )
        # Return error if authentication fails
        return Response(
            {"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED
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


# Token generator for password reset
token_generator = PasswordResetTokenGenerator()


class ResetPasswordView(APIView):
    """
    API for resetting the password using the username and reset token from the headers.
    """

    permission_classes = [AllowAny]  # Allow any user to access this endpoint

    def patch(self, request):
        # Get username and token from headers
        username = request.headers.get("username")
        token = request.headers.get("token")

        if not username or not token:
            return Response(
                {"error": "Username and token must be provided in the headers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate username and token
        user = get_object_or_404(User, username=username)
        if not default_token_generator.check_token(user, token):
            return Response(
                {"error": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get new password and confirm password
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")

        # Check if the passwords match
        if new_password != confirm_password:
            raise ValidationError("Passwords do not match.")

        # Check password strength (basic validation example)
        if len(new_password) < 8:
            raise ValidationError("Password must be at least 8 characters long.")

        # Optionally, add more password complexity checks (e.g., uppercase, special characters)

        # Set new password
        user.password = make_password(new_password)  # Hash the new password
        user.save()

        return Response(
            {"message": "Password has been reset successfully."},
            status=status.HTTP_200_OK,
        )
