from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from users.models import User
from .serializers import DoctorNotesSerializer
from .models import DoctorNotes, Doctor
from users.serializers import UserSerializer
from .models import Referral,AppointmentManagement, ConsultationSettings
from .serializers import ReferralSerializer, InvitationSerializer, AppointmentManagementSerializer, ConsultationSettingsSerializer

class DoctorNotesCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Only doctors can create notes
        if request.user.role != "Doctor":
            return Response({"error": "Only doctors can create notes."}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = DoctorNotesSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Doctor note created successfully.",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, *args, **kwargs):
        # Only doctors can update notes
        if request.user.role != "Doctor":
            return Response({"error": "Only doctors can update notes."}, status=status.HTTP_403_FORBIDDEN)

        # Ensure the note exists and belongs to the logged-in doctor
        note_id = kwargs.get('pk')
        try:
            note = DoctorNotes.objects.get(id=note_id, doctor=request.user)
        except DoctorNotes.DoesNotExist:
            return Response({"error": "Note not found or you do not have permission to update it."}, status=status.HTTP_404_NOT_FOUND)

        # Check if the 'note' field exists in the request and append its content
        new_content = request.data.get('note', "").strip()
        if new_content:  # Append only if new content is provided
            request.data['note'] = (note.note or "") + " " + new_content

        # Serialize and save the updated note
        serializer = DoctorNotesSerializer(note, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Doctor note updated successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    def delete(self, request, *args, **kwargs):
        # Only doctors can delete notes
        if request.user.role != "Doctor":
            return Response({"error": "Only doctors can delete notes."}, status=status.HTTP_403_FORBIDDEN)
        
        # Ensure the note exists and belongs to the logged-in doctor
        note_id = kwargs.get('pk')
        try:
            note = DoctorNotes.objects.get(id=note_id, doctor=request.user)
        except DoctorNotes.DoesNotExist:
            return Response({"error": "Note not found or you do not have permission to delete it."}, status=status.HTTP_404_NOT_FOUND)

        # Delete the note
        note.delete()
        return Response({
            "message": "Note deleted successfully."
        }, status=status.HTTP_204_NO_CONTENT)


class DoctorListAPIView(APIView):
    # permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Filter users with role="Doctor"
        doctors = User.objects.filter(role="Doctor")
        serializer = UserSerializer(doctors, many=True)
        return Response(serializer.data)
    

class ReferralView(APIView):
    """
    API to fetch personal referral details (personal code, registry link, etc.).
    """
    def get(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            referral = Referral.objects.get(user=user)
            serializer = ReferralSerializer(referral)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Referral.DoesNotExist:
            return Response({"error": "Referral system not set up for this user."}, status=status.HTTP_404_NOT_FOUND)


class InvitationView(APIView):
    """
    API to create an invitation using a personal referral code.
    """
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        # Fetch the user's referral
        try:
            referral = Referral.objects.get(user=user)
        except Referral.DoesNotExist:
            return Response({"error": "Referral system not set up for this user."}, status=status.HTTP_404_NOT_FOUND)

        serializer = InvitationSerializer(data=request.data, context={'invited_by': referral})
        if serializer.is_valid():
            invitation = serializer.save()
            referral.users_invited += 1  # Increment users invited count
            referral.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AppointmentManagementAPIView(APIView):
    """
    API to manage appointment preferences (list, create, update, delete).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Get all appointment preferences for the logged-in user.
        """
        preferences = AppointmentManagement.objects.filter(user=request.user)
        serializer = AppointmentManagementSerializer(preferences, many=True)
        return Response(serializer.data)

    def post(self, request):
        """
        Create a new appointment preference for the logged-in user.
        """
        serializer = AppointmentManagementSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        """
        Update an existing appointment preference.
        """
        try:
            preference = AppointmentManagement.objects.get(pk=pk, user=request.user)
        except AppointmentManagement.DoesNotExist:
            return Response({"error": "Preference not found or unauthorized"}, status=status.HTTP_404_NOT_FOUND)

        serializer = AppointmentManagementSerializer(preference, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """
        Delete an appointment preference.
        """
        try:
            preference = AppointmentManagement.objects.get(pk=pk, user=request.user)
            preference.delete()
            return Response({"message": "Preference deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except AppointmentManagement.DoesNotExist:
            return Response({"error": "Preference not found or unauthorized"}, status=status.HTTP_404_NOT_FOUND)
        
        
class ConsultationSettingsAPIView(APIView):
    """
    API for managing Consultation Settings for authenticated doctors.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Create a new consultation setting for the authenticated doctor.
        """
        if request.user.role != "Doctor":
            return Response({"message": "Only doctors can create consultation settings."}, status=status.HTTP_403_FORBIDDEN)

        # Fetch the authenticated doctor's profile
        try:
            doctor = request.user.doctor
        except Doctor.DoesNotExist:
            return Response({"message": "Doctor profile not found."}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        data["doctor"] = doctor.id

        # save the consultation setting
        serializer = ConsultationSettingsSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Consultation setting created successfully.", "data": serializer.data},
                status=status.HTTP_201_CREATED
            )

        return Response(
            {"message": "Failed to create consultation setting.", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    def get(self, request, *args, **kwargs):
        """
        Retrieve all consultation settings for the authenticated doctor.
        """
        if request.user.role != "Doctor":
            return Response({"message": "Only doctors can view consultation settings."}, status=status.HTTP_403_FORBIDDEN)

        try:
            doctor = request.user.doctor
        except Doctor.DoesNotExist:
            return Response({"message": "Doctor profile not found."}, status=status.HTTP_404_NOT_FOUND)

        # Retrieve consultation settings for the authenticated doctor
        consultations = ConsultationSettings.objects.filter(doctor=doctor)
        serializer = ConsultationSettingsSerializer(consultations, many=True)
        return Response(
            {"message": "Consultation settings retrieved successfully.", "data": serializer.data},
            status=status.HTTP_200_OK
        )


class ConsultationSettingsDetailAPIView(APIView):
    """
    API for retrieving, updating, and deleting a single Consultation Setting.
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, doctor):
        try:
            return ConsultationSettings.objects.get(pk=pk, doctor=doctor)
        except ConsultationSettings.DoesNotExist:
            return None

    def get(self, request, pk, *args, **kwargs):
        """
        Retrieve a single consultation setting for the authenticated doctor.
        """
        if request.user.role != "Doctor":
            return Response({"message": "Only doctors can view consultation settings."}, status=status.HTTP_403_FORBIDDEN)

        try:
            doctor = request.user.doctor
        except Doctor.DoesNotExist:
            return Response({"message": "Doctor profile not found."}, status=status.HTTP_404_NOT_FOUND)

        consultation = self.get_object(pk, doctor)
        if not consultation:
            return Response(
                {"message": "Consultation setting not found or does not belong to you."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ConsultationSettingsSerializer(consultation)
        return Response(
            {"message": "Consultation setting retrieved successfully.", "data": serializer.data},
            status=status.HTTP_200_OK
        )

    def put(self, request, pk, *args, **kwargs):
        """
        Update a single consultation setting for the authenticated doctor.
        """
        if request.user.role != "Doctor":
            return Response({"message": "Only doctors can update consultation settings."}, status=status.HTTP_403_FORBIDDEN)

        try:
            doctor = request.user.doctor
        except Doctor.DoesNotExist:
            return Response({"message": "Doctor profile not found."}, status=status.HTTP_404_NOT_FOUND)

        consultation = self.get_object(pk, doctor)
        if not consultation:
            return Response(
                {"message": "Consultation setting not found or does not belong to you."},
                status=status.HTTP_404_NOT_FOUND
            )

        data = request.data.copy()
        
        serializer = ConsultationSettingsSerializer(consultation, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Consultation setting updated successfully.", "data": serializer.data},
                status=status.HTTP_200_OK
            )
        
        return Response(
            {"message": "Failed to update consultation setting.", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

