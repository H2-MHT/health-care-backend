from django.forms import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from users.models import User
from .serializers import DoctorNotesSerializer
from .models import DoctorNotes, Invitation
from users.serializers import UserSerializer
from .models import Referral,AppointmentManagement, Doctor, ConsultationSettings
from .serializers import ReferralSerializer, InvitationSerializer, AppointmentManagementSerializer, ConsultationSettingsSerializer
from django.utils.crypto import get_random_string

from rest_framework.decorators import api_view


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

    def delete(self, request):
        """
        Delete an appointment preference by ID provided in the request body.
        """
        # Get the 'pk' from the request body
        pk = request.data.get('pk')
        
        if not pk:
            raise ValidationError("The 'pk' field is required in the request body.")
        
        try:
            # Retrieve the preference based on pk and the logged-in user
            preference = AppointmentManagement.objects.get(pk=pk, user=request.user)
            preference.delete()
            return Response({"message": "Preference deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except AppointmentManagement.DoesNotExist:
            return Response({"error": "Preference not found or unauthorized"}, status=status.HTTP_404_NOT_FOUND)

class GenerateReferralCodeView(APIView):
    """Generate and return a user's referral code and registration link."""

    def generate_referral_code(self):
        """Generate a unique referral code (7 characters)."""
        return get_random_string(length=7).upper()

    def get(self, request):
        try:
            # Get or create the referral object for the current user
            referral, created = Referral.objects.get_or_create(user=request.user)

            if created:
                # Generate and assign a unique referral code
                referral.personal_code = self.generate_referral_code()
                referral.save()

            # Check if the user was invited by someone
            if referral.invited_by:
                inviter_referral = Referral.objects.get(user=referral.invited_by)

                # Debugging: check if inviter referral is found
                print(f"Inviter: {inviter_referral.user.first_name} - Current Count: {inviter_referral.invited_users_count}")

                # Use the increase_invite_count method to increase the count
                inviter_referral.increase_invite_count()

                # Debugging: print count after increment
                print(f"Updated Inviter Count: {inviter_referral.invited_users_count}")

            # Serialize and return the referral data (referral code, registration link, etc.)
            serializer = ReferralSerializer(referral)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Referral.DoesNotExist:
            return Response({'error': 'Referral code not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)



class InviteUserView(APIView):
    """Apply referral code manually and mark it as used."""

    def post(self, request):
        referral_code = request.data.get('referral_code')  # Get referral code from request body

        try:
            # Check if the referral code exists and has not been used
            referral = Referral.objects.get(personal_code=referral_code)

            # Debugging: Print referral details
            print(f"Referral Found: {referral.user.first_name}, {referral.personal_code}")

            # Check if this referral code has already been used
            if Invitation.objects.filter(invitation_code=referral_code, is_used=True).exists():
                return Response({'error': 'This referral code has already been used.'}, status=status.HTTP_400_BAD_REQUEST)

            # Create an invitation for the new user (invited by user A)
            invitation = Invitation.objects.create(invited_by=referral, invitation_code=referral_code, invited_user=request.user)

            # Debugging: Check invitation details
            print(f"Invitation Created: {invitation.invited_user.first_name}, {invitation.invitation_code}")

            # Mark the invitation as used (only once)
            invitation.is_used = True
            invitation.save()

            # Increase the invited user count for the inviter (user A)
            referral.increase_invite_count()

            # Debugging: Check if the count was increased
            print(f"Inviter's Count After Increase: {referral.invited_users_count}")

            # Also increase the inviter's referral count (for the inviter's code usage)
            inviter_referral = referral.invited_by.referral if referral.invited_by else None
            if inviter_referral:
                inviter_referral.invited_users_count += 1
                inviter_referral.save()

                # Debugging: Check inviter's updated count
                print(f"Inviter's Referral Count After Increase: {inviter_referral.invited_users_count}")

            return Response({'message': 'Referral code applied successfully.'}, status=status.HTTP_200_OK)

        except Referral.DoesNotExist:
            return Response({'error': 'Invalid referral code.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Catch any unexpected exceptions
            print(f"Error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        
        
@api_view(['POST'])
def redeem_invitation(request, invitation_code):
    """Redeem the invitation and increase the inviter's stats."""
    try:
        invitation = Invitation.objects.get(invitation_code=invitation_code)

        if invitation.redeemed:
            return Response({'error': 'This invitation has already been redeemed.'}, status=status.HTTP_400_BAD_REQUEST)

        invitation.redeem()  # Redeem the invitation
        return Response({'message': 'Invitation redeemed successfully!'}, status=status.HTTP_200_OK)
    except Invitation.DoesNotExist:
        return Response({'error': 'Invalid invitation code.'}, status=status.HTTP_400_BAD_REQUEST)
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


class CombinedAPIView(APIView):
    """
    API to return combined response for Referral, Invitation, and Consultation Settings (GET, POST, PUT).
    """

    def get(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        # Initialize response with empty placeholders
        response_data = {
            "referral": {},
            "invitation": {},
            "consultation_settings": {}
        }

        # Fetch Referral details
        referral_response = self.get_referral_data(request)
        response_data["referral"] = referral_response if referral_response else {}

        # Fetch Invitation details
        invitation_response = self.get_invitation_data(request)
        response_data["invitation"] = invitation_response if invitation_response else {}

        # Fetch Consultation Settings
        consultation_response = self.get_consultation_settings(request)
        response_data["consultation_settings"] = consultation_response if consultation_response else {}

        return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        # Initialize response with empty placeholders
        response_data = {
            "referral": {},
            "invitation": {},
            "consultation_settings": {}
        }

        # Handle Referral
        referral_response = self.create_or_get_referral(request)
        response_data["referral"] = referral_response if referral_response else {}

        # Handle Invitation creation
        invitation_response = self.create_invitation(request)
        response_data["invitation"] = invitation_response if invitation_response.get("success") else {}

        # Handle Consultation Settings creation
        consultation_response = self.create_consultation_settings(request)
        response_data["consultation_settings"] = consultation_response if consultation_response.get("success") else {}

        return Response(response_data, status=status.HTTP_201_CREATED)

    def put(self, request, pk):
        user = request.user
        if not user.is_authenticated:
            return Response({"error": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        # Initialize response with empty placeholders
        response_data = {
            "referral": {"message": "Referral update not supported."},
            "invitation": {"message": "Invitation update not supported."},
            "consultation_settings": {}
        }

        # Handle Consultation Settings update
        consultation_response = self.update_consultation_settings(request, pk)
        response_data["consultation_settings"] = consultation_response if consultation_response.get("success") else {}

        return Response(response_data, status=status.HTTP_200_OK)

    # Helper methods for each API logic

    def get_referral_data(self, request):
        """
        Retrieve referral-related data.
        """
        try:
            referral = Referral.objects.get(user=request.user)
            serializer = ReferralSerializer(referral)
            return serializer.data
        except Referral.DoesNotExist:
            return None

    def get_invitation_data(self, request):
        """
        Fetch the invitation data related to the user.
        """
        try:
            referral = Referral.objects.get(user=request.user)
            invitation = Invitation.objects.filter(invited_by=referral).first()  # Adjust as necessary
            if invitation:
                serializer = InvitationSerializer(invitation)
                return serializer.data
            else:
                return {"message": "No invitation found for this user."}
        except Referral.DoesNotExist:
            return {"message": "Referral system not set up for this user."}

    def get_consultation_settings(self, request):
        """
        Retrieve consultation settings for doctors.
        """
        if request.user.role != "Doctor":
            return None
        try:
            doctor = request.user.doctor
            consultations = ConsultationSettings.objects.filter(doctor=doctor)
            serializer = ConsultationSettingsSerializer(consultations, many=True)
            return serializer.data
        except Doctor.DoesNotExist:
            return None

    def create_or_get_referral(self, request):
        """
        Retrieve or handle referral-related actions in POST.
        """
        try:
            referral = Referral.objects.get(user=request.user)
            serializer = ReferralSerializer(referral)
            return serializer.data
        except Referral.DoesNotExist:
            return None

    def create_invitation(self, request):
        """
        Create an invitation using the provided data.
        """
        try:
            referral = Referral.objects.get(user=request.user)
            serializer = InvitationSerializer(data=request.data, context={'invited_by': referral})
            if serializer.is_valid():
                invitation = serializer.save()
                referral.users_invited += 1
                referral.save()
                return {"success": True, "data": serializer.data}
            else:
                return {"success": False, "errors": serializer.errors}
        except Referral.DoesNotExist:
            return None

    def create_consultation_settings(self, request):
        """
        Create consultation settings for doctors.
        """
        if request.user.role != "Doctor":
            return {"success": False, "error": "Only doctors can create consultation settings."}

        try:
            doctor = request.user.doctor
            data = request.data.copy()
            data["doctor"] = doctor.id
            serializer = ConsultationSettingsSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return {"success": True, "data": serializer.data}
            else:
                return {"success": False, "errors": serializer.errors}
        except Doctor.DoesNotExist:
            return {"success": False, "error": "Doctor profile not found."}

    def update_consultation_settings(self, request, pk):
        """
        Update consultation settings for doctors.
        """
        if request.user.role != "Doctor":
            return {"success": False, "error": "Only doctors can update consultation settings."}

        try:
            doctor = request.user.doctor
            consultation = ConsultationSettings.objects.get(pk=pk, doctor=doctor)
            serializer = ConsultationSettingsSerializer(consultation, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return {"success": True, "data": serializer.data}
            else:
                return {"success": False, "errors": serializer.errors}
        except ConsultationSettings.DoesNotExist:
            return {"success": False, "error": "Consultation setting not found or does not belong to you."}
        except Doctor.DoesNotExist:
            return {"success": False, "error": "Doctor profile not found."}
