from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
import logging
from .serializers import EducationSerializer
from .models import Education, User, TwoFactorMethod

class UpdateEducationAPIView(APIView):
    """
    API to update or create an Education record for a user based on user ID.
    """

    def patch(self, request, user_id, *args, **kwargs):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        education = Education.objects.filter(user=user).first()

        # Use the serializer to validate and save data
        serializer = EducationSerializer(education, data=request.data, partial=True)
        if serializer.is_valid():
            if education:
                serializer.save()
                return Response(
                    {
                        "message": "Education record updated successfully.",
                        "data": serializer.data
                    },
                    status=status.HTTP_200_OK
                )
            else:
                serializer.save(user=user)
                return Response(
                    {
                        "message": "Education record created successfully.",
                        "data": serializer.data
                    },
                    status=status.HTTP_201_CREATED
                )
        return Response(
            {"message": "Invalid data provided.", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def get(self, request, user_id, *args, **kwargs):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        education = Education.objects.filter(user=user).first()
        serializer = EducationSerializer(education)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

logger = logging.getLogger(__name__)
class SelectMethodsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            """Retrieve all selected 2FA methods for the current user."""
            user = request.user
            print(f"Authenticated user: {user.email}, ID: {user.id}")

            # Get all selected 2FA methods
            methods = user.two_factor_methods.values_list("name", flat=True)

            print(f"Methods for {user.email}: {list(methods)}")

            return Response({"methods": list(methods)}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def post(self, request):
        try:
            user = request.user
            method_id = request.data.get("method_id")

            # Validate input
            if not method_id or not isinstance(method_id, (int, str)):
                return Response({"error": "Invalid method ID format"}, status=status.HTTP_400_BAD_REQUEST)

            # Convert to integer (if needed)
            try:
                method_id = int(method_id)
            except ValueError:
                return Response({"error": "Method ID must be an integer"}, status=status.HTTP_400_BAD_REQUEST)

            # Check if the method exists and is active
            try:
                method = TwoFactorMethod.objects.get(id=method_id, is_active=True)
            except TwoFactorMethod.DoesNotExist:
                return Response({"error": "Invalid method ID"}, status=status.HTTP_400_BAD_REQUEST)

            # Check if the method is already added
            if user.two_factor_methods.filter(id=method_id).exists():
                return Response({"message": "Method already added"}, status=status.HTTP_200_OK)

            # Add the method
            user.two_factor_methods.add(method)

            return Response({"message": "Authentication method added successfully"}, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.exception("Unexpected error updating authentication methods: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def delete(self, request):
        try:
            user = request.user
            method_id = request.data.get("method_id")

            # Validate input
            if not method_id or not isinstance(method_id, (int, str)):
                return Response({"error": "Invalid method ID format"}, status=status.HTTP_400_BAD_REQUEST)

            # Convert to integer (if needed)
            try:
                method_id = int(method_id)
            except ValueError:
                return Response({"error": "Method ID must be an integer"}, status=status.HTTP_400_BAD_REQUEST)

            # Check if the method is associated with the user
            if not user.two_factor_methods.filter(id=method_id).exists():
                return Response({"error": "Method not found or already deleted"}, status=status.HTTP_404_NOT_FOUND)

            # Remove the method from user's selection
            user.two_factor_methods.remove(method_id)

            return Response({"message": "Authentication method deleted successfully"}, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.exception("Unexpected error deleting authentication method: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
            
            
class AvailableMethodsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            """Retrieve all available 2FA methods."""
            methods = TwoFactorMethod.objects.filter(is_active=True).values("id", "name")
            return Response({"methods": list(methods)}, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.exception("Unexpected error fetching available methods: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )