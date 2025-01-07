from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from users.models import User
from .serializers import DoctorNotesSerializer
from .models import DoctorNotes

class DoctorNotesCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        #  only doctors can create notes
        if request.user.role != "Doctor":
            return Response({"error": "Only doctors can create notes."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = DoctorNotesSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self, request, *args, **kwargs):
        # only doctors can access their notes
        if request.user.role != "Doctor":
            return Response({"error": "Only doctors can access their notes."}, status=status.HTTP_403_FORBIDDEN)
        
        # Fetch notes created by the logged-in doctor
        notes = DoctorNotes.objects.filter(doctor=request.user).order_by('-created_at')
        serializer = DoctorNotesSerializer(notes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)