from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser

from .serializers import EducationSerializer
from .models import Education, User

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