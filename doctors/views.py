from django.forms import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from users.models import User
from .serializers import DoctorNotesSerializer
from .models import DoctorNotes, Invitation
from users.serializers import UserSerializer
from .models import (
    Referral,
    AppointmentManagement,
    Doctor,
    ConsultationSettings,
    UserPreference,
    ReschedulePolicy,
    CancellationPolicy,
    NoShowPolicy,
)
from .serializers import(
    ReferralSerializer,
    AppointmentManagementSerializer,
    ReschedulePolicySerializer,
    ConsultationSettingsSerializer,
    UserPreferenceSerializer,
    CancellationPolicySerializer,
    NoShowPolicySerializer,
    
)
from django.utils.crypto import get_random_string
import pytz
from datetime import datetime
from django.utils import translation
from django.utils.translation import gettext
from django.utils import translation
from rest_framework.exceptions import NotFound

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

        if not request.user.is_authenticated:
            return Response({'error': 'You must be logged in to use a referral code.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            # Check if the referral code exists
            referral = Referral.objects.get(personal_code=referral_code)

            # Ensure the referral code is not being used by the same user (logged-in user)
            if referral.user == request.user:
                return Response({'error': 'You cannot use your own referral code.'}, status=status.HTTP_400_BAD_REQUEST)

            # Check if this referral code has already been used by the current user
            if Invitation.objects.filter(invited_by=referral, invited_user=request.user).exists():
                return Response({'error': 'You have already used this referral code.'}, status=status.HTTP_400_BAD_REQUEST)

            # Create an invitation for the new user (invited by user A)
            invitation = Invitation.objects.create(
                invited_by=referral,
                invited_user=request.user,
            )

            # Update the inviter's invited users count
            referral.invited_users_count = Invitation.objects.filter(invited_by=referral).count()
            referral.referral_use = True
            referral.save()

            return Response({'message': 'Referral code applied successfully.'}, status=status.HTTP_200_OK)

        except Referral.DoesNotExist:
            return Response({'error': 'Invalid referral code.'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
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

        
        
class ConsultationSettingsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # Fetch the current logged-in user
        user = request.user
        
        # Ensure the user is a doctor
        if not hasattr(user, 'doctor'):
            return Response({"error": "You are not a registered doctor."}, status=status.HTTP_403_FORBIDDEN)

        # Get all ConsultationSettings records for the logged-in doctor
        consultation_settings = ConsultationSettings.objects.filter(doctor=user.doctor)

        # Serialize the data
        serializer = ConsultationSettingsSerializer(consultation_settings, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request, *args, **kwargs):
        # Check if the logged-in user is a doctor
        user = request.user
        try:
            doctor = Doctor.objects.get(user=user)
        except Doctor.DoesNotExist:
            return Response({"error": "You are not a registered doctor."}, status=status.HTTP_403_FORBIDDEN)

        # Add the logged-in doctor to the data
        request.data['doctor'] = doctor.id

        serializer = ConsultationSettingsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



# Function to get current time in a given timezone
def get_time_in_timezone(timezone_str):
    try:
        timezone = pytz.timezone(timezone_str)
        return datetime.now(timezone).strftime('%Y-%m-%d %H:%M:%S')
    except pytz.UnknownTimeZoneError:
        return "Invalid timezone"

class UserPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get or create user preference
        preference, _ = UserPreference.objects.get_or_create(user=request.user)

        # Get timezone from user preference (default to UTC if not set)
        user_timezone = preference.timezone if preference.timezone else 'UTC'

        # Get current time in user’s timezone
        current_time = get_time_in_timezone(user_timezone)

        # Serialize user preference data
        serializer = UserPreferenceSerializer(preference)

        # Return response with current time
        return Response({
            'user_preference': serializer.data,
            'current_time': current_time,
            'timezone': user_timezone
        })

    def post(self, request):
        # Get or create user preference
        preference, _ = UserPreference.objects.get_or_create(user=request.user)

        # Update user preference with new data
        serializer = UserPreferenceSerializer(preference, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


class UserPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get or create user preference
        preference, _ = UserPreference.objects.get_or_create(user=request.user)

        # Get timezone and language from user preference
        if preference.use_system_timezone:
            user_timezone = 'UTC'
        else:
            user_timezone = preference.timezone

        if preference.use_system_language:
            user_language = 'en'
        else:
            user_language = preference.language

        # Set the language dynamically based on user preference
        if isinstance(user_language, str):
            translation.activate(user_language)

        # Get current time in user’s timezone
        current_time = get_time_in_timezone(user_timezone)

        # Serialize user preference data
        serializer = UserPreferenceSerializer(preference)

        # Return response with current time
        return Response({
            'user_preference': serializer.data,
            'current_time': current_time,
            'timezone': user_timezone,
            'language': user_language,
            'message': gettext("Time fetched successfully.")  # Example of a translatable message
        })

    def post(self, request):
        # Get or create user preference
        preference, _ = UserPreference.objects.get_or_create(user=request.user)

        # Get the data from the request to update the timezone and language
        timezone = request.data.get('timezone')
        language = request.data.get('language')
        use_system_timezone = request.data.get('use_system_timezone')
        use_system_language = request.data.get('use_system_language')

        # Update the user preference with new data
        if timezone is not None:
            preference.timezone = timezone
        if language is not None:
            preference.language = language
        if use_system_timezone is not None:
            preference.use_system_timezone = use_system_timezone
        if use_system_language is not None:
            preference.use_system_language = use_system_language

        # Save updated preference
        preference.save()

        # Set the language dynamically if it has been updated
        if language and isinstance(language, str):
            translation.activate(language)

        # Serialize user preference data
        serializer = UserPreferenceSerializer(preference)

        return Response({
            'message': gettext("Preference updated successfully."),
            'data': serializer.data
        })
        
        

class AllowRescheduleView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Get or create the ReschedulePolicy for the user
        policy, created = ReschedulePolicy.objects.get_or_create(user=request.user)

        # Get the "allow_reschedule" value from the request body
        allow_reschedule = request.data.get("allow_reschedule", False)

        # Set the "allow_reschedule" value from the request body
        policy.allow_reschedule = allow_reschedule
        policy.save()

        # Return success response
        return Response({"message": "Rescheduling setting updated."}, status=status.HTTP_200_OK)
    
    
class UpdateReschedulePolicyView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, user):
        try:
            return ReschedulePolicy.objects.get(user=user)
        except ReschedulePolicy.DoesNotExist:
            return None

    def post(self, request):
        # Get the user's reschedule policy
        policy = self.get_object(request.user)

        if policy is None:
            return Response({"error": "Policy does not exist."}, status=status.HTTP_404_NOT_FOUND)

        # Check if rescheduling is allowed for the user
        if not policy.allow_reschedule:
            return Response({"error": "You are not allowed to update the reschedule policy."}, status=status.HTTP_403_FORBIDDEN)

        # Proceed to update the reschedule policy
        serializer = ReschedulePolicySerializer(policy, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
class CancellationPolicyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            policy = CancellationPolicy.objects.get(doctor=request.user)
        except CancellationPolicy.DoesNotExist:
            raise NotFound("Cancellation policy not found.")

        serializer = CancellationPolicySerializer(policy)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = CancellationPolicySerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, *args, **kwargs):
        try:
            policy = CancellationPolicy.objects.get(doctor=request.user)
        except CancellationPolicy.DoesNotExist:
            raise NotFound("Cancellation policy not found.")
        
        serializer = CancellationPolicySerializer(policy, data=request.data, context={'request': request}, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        try:
            policy = CancellationPolicy.objects.get(doctor=request.user)
        except CancellationPolicy.DoesNotExist:
            raise NotFound("Cancellation policy not found.")
        
        policy.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NoShowPolicyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)
        policies = NoShowPolicy.objects.filter(user=request.user)
        serializer = NoShowPolicySerializer(policies, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)
        data = request.data.copy()
        data['user'] = request.user.id

        serializer = NoShowPolicySerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)
        policy = get_object_or_404(NoShowPolicy, user=request.user)

        serializer = NoShowPolicySerializer(policy, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)