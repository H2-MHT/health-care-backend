from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.http.multipartparser import MultiPartParser
from .serializers import EducationSerializer
from .models import Education, User

class UpdateEducationAPIView(APIView):
    """
    API to update or create Education record for a user based on user ID.
    If an education record for the user already exists, it will be updated.
    If it does not exist, a new record will be created.
    """

    def patch(self, request, user_id, *args, **kwargs):
        try:
            # Fetch the user by ID
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        # Check if the user already has an education record
        education = Education.objects.filter(user=user).first()
        # updating or creating new record
        serializer = EducationSerializer(education, data=request.data, partial=True)
        if serializer.is_valid():
            if education:
                # Update the existing record
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                # Create a new record if no existing education record was found
                serializer.save(user=user)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    