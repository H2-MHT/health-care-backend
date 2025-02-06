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
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from sendgrid.helpers.mail import Mail, Email, To, Content

from .models import (
    Referral,
    AppointmentManagement,
    Doctor,
    ConsultationSettings,
    UserPreference,
    ReschedulePolicy,
    CancellationPolicy,
    NoShowPolicy,
    CommunicationPreferences,
    TwoFactorAuthentication,
)
from .serializers import(
    ReferralSerializer,
    AppointmentManagementSerializer,
    ReschedulePolicySerializer,
    ConsultationSettingsSerializer,
    CancellationPolicySerializer,
    NoShowPolicySerializer,
    CommunicationPreferencesSerializer,
)
from django.utils.crypto import get_random_string
import pytz
from datetime import datetime
from django.contrib.auth.hashers import check_password
import random
from django.conf import settings
import sendgrid

from django.utils.translation import gettext
from rest_framework.exceptions import NotFound
from django.contrib.auth.hashers import make_password

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
    """Generate and return a user's referral code, registration link, and update referral points."""

    def generate_referral_code(self):
        """Generate a unique referral code (7 characters)."""
        return get_random_string(length=7).upper()

    def get(self, request):
        try:
            # Get or create referral object for the current user
            referral, created = Referral.objects.get_or_create(user=request.user)

            if created:
                referral.personal_code = self.generate_referral_code()
                referral.save()

            # Check if any invited user has completed their first appointment
            invitations = Invitation.objects.filter(invited_by=referral, first_appointment=True)

            for invitation in invitations:
                if invitation.invited_user:  # Ensure invited user exists
                    referral.referral_points += 10
                    invitation.first_appointment = False
                    referral.save()
                    invitation.save()

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
        user = request.user
        if not hasattr(user, 'doctor'):
            return Response({"error": "You are not a registered doctor."}, status=status.HTTP_403_FORBIDDEN)
        consultation_settings = ConsultationSettings.objects.filter(doctor=user.doctor)
        serializer = ConsultationSettingsSerializer(consultation_settings, many=True)
        return Response({"message": "Consultation settings retrieved successfully", "data": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        user = request.user
        try:
            doctor = Doctor.objects.get(user=user)
        except Doctor.DoesNotExist:
            return Response({"error": "You are not a registered doctor."}, status=status.HTTP_403_FORBIDDEN)
        try:
            consultation_settings = ConsultationSettings.objects.filter(doctor=doctor).first()
            if consultation_settings:
                serializer = ConsultationSettingsSerializer(consultation_settings, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return Response({"message": "Consultation settings updated successfully", "data": serializer.data}, status=status.HTTP_200_OK)
            else:
                request.data['doctor'] = doctor.id
                serializer = ConsultationSettingsSerializer(data=request.data)
                if serializer.is_valid():
                    serializer.save()
                    return Response({"message": "Consultation settings created successfully", "data": serializer.data}, status=status.HTTP_201_CREATED)
            return Response({"error": "Invalid data", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
        except Exception as e:
            return Response({"error": "Something went wrong", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Function to get current time in a given timezone
def get_time_in_timezone(timezone):
    """Get the current time in the specified timezone."""
    tz = pytz.timezone(timezone)
    return datetime.now(tz).isoformat()

class UserPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get or create user preference
        preference, _ = UserPreference.objects.get_or_create(user=request.user)

        # Convert stored language string to a list
        user_languages = preference.language.split(",") if preference.language else ["en"]

        # Get timezone
        user_timezone = "UTC" if preference.use_system_timezone else preference.timezone

        # Get current time in user’s timezone
        current_time = get_time_in_timezone(user_timezone)

        return Response({
            "message": "Data fetched successfully.",
            "user_preference": {
                "timezone": user_timezone,
                "languages": user_languages,
                "use_system_timezone": preference.use_system_timezone,
                "use_system_language": preference.use_system_language,
                "current_time": current_time
            }
        })

    def post(self, request):
        # Get or create user preference
        preference, _ = UserPreference.objects.get_or_create(user=request.user)

        timezone = request.data.get("timezone")
        languages = request.data.get("languages")  # list
        use_system_timezone = request.data.get("use_system_timezone")
        use_system_language = request.data.get("use_system_language")

        # Update preference
        if timezone is not None:
            preference.timezone = timezone
        if languages is not None:
            if isinstance(languages, list):
                preference.language = ",".join(languages)
        if use_system_timezone is not None:
            preference.use_system_timezone = use_system_timezone
        if use_system_language is not None:
            preference.use_system_language = use_system_language

        # Save changes
        preference.save()
        return Response({
            "message": "Data updated successfully.",
            "user_preference": {
                "timezone": preference.timezone,
                "languages": languages if languages else preference.language.split(","),
                "use_system_timezone": preference.use_system_timezone,
                "use_system_language": preference.use_system_language
            }
        })
        

class ReschedulePolicyView(APIView):
    """API to create or update a Reschedule Policy for each day."""
    
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Update an existing data or create a new one."""
        data = request.data
        user = request.user
        reschedule_day = data.get('reschedule_days')
        valid_days = [choice[0] for choice in ReschedulePolicy.DAYS_CHOICES]
        if reschedule_day not in valid_days:
            return Response(
                {"error": "Invalid day format. Use 'Mon', 'Tue', etc."},
                status=status.HTTP_400_BAD_REQUEST
            )
        existing_policy = ReschedulePolicy.objects.filter(user=user, reschedule_days=reschedule_day).first()
        if existing_policy:
            # Updat data for existing entry
            existing_policy.allow_reschedule = data.get('allow_reschedule', existing_policy.allow_reschedule)
            existing_policy.max_reschedules = data.get('max_reschedules', existing_policy.max_reschedules)
            existing_policy.reschedule_time_range = data.get('reschedule_time_range', existing_policy.reschedule_time_range)
            existing_policy.save()
            return Response(
                {
                    "message": f"Reschedule policy for {reschedule_day} updated successfully.",
                    "data": ReschedulePolicySerializer(existing_policy).data
                },
                status=status.HTTP_200_OK
            )
        else:
            policy = ReschedulePolicy.objects.create(
                user=user,
                allow_reschedule=data.get('allow_reschedule', True),
                max_reschedules=data.get('max_reschedules'),
                reschedule_days=reschedule_day,
                reschedule_time_range=data.get('reschedule_time_range'),
            )
            return Response(
                {
                    "message": f"Reschedule policy for {reschedule_day} created successfully.",
                    "data": ReschedulePolicySerializer(policy).data
                },
                status=status.HTTP_201_CREATED
            )

    def get(self, request):
        """Fetch all reschedule policies for the logged-in user."""
        user = request.user
        policies = ReschedulePolicy.objects.filter(user=user)
        serializer = ReschedulePolicySerializer(policies, many=True)
        return Response(
            {
                "message": "Reschedule policies fetched successfully.",
                "data": serializer.data
            },
            status=status.HTTP_200_OK
        )

    
    
    
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
        existing_policy = CancellationPolicy.objects.filter(doctor=request.user).first()
        if existing_policy:
            # If policy exists, update it without creating new one
            serializer = CancellationPolicySerializer(
                existing_policy, data=request.data, context={'request': request}, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {"message": "Cancellation policy updated successfully.", "data": serializer.data},
                    status=status.HTTP_200_OK
                )
            return Response(
                {"detail": "Invalid data.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create a new policy if not exists
        serializer = CancellationPolicySerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(doctor=request.user)
            return Response(
                {"message": "Cancellation policy created successfully.", "data": serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(
            {"detail": "Invalid data.", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


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
        if NoShowPolicy.objects.filter(user=request.user).exists():
            return Response({"detail": "You already have an existing NoShowPolicy."}, status=status.HTTP_400_BAD_REQUEST)
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
    
    
class CommunicationPreferencesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """Retrieve the current user's communication preferences"""
        preferences, created = CommunicationPreferences.objects.get_or_create(user=request.user)
        serializer = CommunicationPreferencesSerializer(preferences)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        """Update the current user's communication preferences"""
        preferences, created = CommunicationPreferences.objects.get_or_create(user=request.user)
        serializer = CommunicationPreferencesSerializer(preferences, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SelectMethodsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Retrieve all selected 2FA methods for the current user."""
        user = request.user
        print(f"Authenticated user: {user.username}, ID: {user.id}")

        # Get all stored 2FA methods for the user
        two_factor_methods = TwoFactorAuthentication.objects.filter(user=user)
        methods = [method.method for method in two_factor_methods]

        print(f"Methods for {user.username}: {methods}")

        return Response({"methods": methods}, status=status.HTTP_200_OK)

    def post(self, request):
        """Add new 2FA methods."""
        user = request.user
        selected_methods = request.data.get("methods", ["email"])  # Default: email

        # Ensure input is a list
        if not isinstance(selected_methods, list):
            return Response({"error": "Methods should be a list"}, status=status.HTTP_400_BAD_REQUEST)

        # Convert list to a set for efficiency
        selected_methods_set = set(selected_methods)

        # Get all existing methods in DB for the user
        existing_methods_set = set(TwoFactorAuthentication.objects.filter(user=user).values_list('method', flat=True))

        # Find methods to add (new selections not already in DB)
        methods_to_add = selected_methods_set - existing_methods_set

        # Add new methods
        TwoFactorAuthentication.objects.bulk_create([
            TwoFactorAuthentication(user=user, method=method) for method in methods_to_add
        ])

        return Response({"message": "Authentication methods updated successfully"}, status=status.HTTP_200_OK)

    def delete(self, request):
        """Delete a specific 2FA method."""
        user = request.user
        method_to_delete = request.data.get("method")

        if not method_to_delete:
            return Response({"error": "No method provided to delete"}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure the method is valid
        if method_to_delete not in ['email', 'sms', 'whatsapp']:
            return Response({"error": "Invalid method"}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the user has the method
        two_factor_record = TwoFactorAuthentication.objects.filter(user=user, method=method_to_delete).first()

        if not two_factor_record:
            return Response({"error": "This method is not linked to the user"}, status=status.HTTP_400_BAD_REQUEST)

        # Delete the specific method
        two_factor_record.delete()

        return Response({"message": f"Method '{method_to_delete}' deleted successfully"}, status=status.HTTP_200_OK)
def send_otp(user, methods):
    otp = str(random.randint(100000, 999999))
    user.otp = otp
    user.save()

    # Send OTP via SendGrid email
    if "email" in methods:
        sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        # From email
        from_email = Email("akash.prajapati@techqware.com")
        # user's email
        to_email = To(user.email)  # Get email from logged-in user
        subject = "Password Change OTP"
        content = Content("text/plain", f"Your OTP for password change is: {otp}")
        mail = Mail(from_email, to_email, subject, content)
        try:
            response = sg.send(mail)
            print(f"Email sent to {user.email} with status code {response.status_code}")
        except Exception as e:
            print(f"Error sending email: {e}")
    return otp

class RequestPasswordChangeAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user = request.user  # Extract the current logged-in user
        print(user, "-----------------------------------")
        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")
        confirm_new_password = request.data.get("confirm_new_password")
        selected_methods = request.data.get("methods", ["email"])  # Default email
        if not check_password(current_password, user.password):
            return Response({"error": "Incorrect current password"}, status=status.HTTP_400_BAD_REQUEST)
        if new_password != confirm_new_password:
            return Response({"error": "New passwords do not match"}, status=status.HTTP_400_BAD_REQUEST)

        # Password validation minimum 8 characters
        if len(new_password) < 8:
            return Response({"error": "Password must be at least 8 characters long"}, status=status.HTTP_400_BAD_REQUEST)

        # Send OTP to the selected methods (currently only email)
        send_otp(user, selected_methods)
        return Response({"message": "OTP sent successfully to selected methods"}, status=status.HTTP_200_OK)
    
    
class VerifyOTPAndChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        entered_otp = request.data.get("otp")
        new_password = request.data.get("new_password")

        # Verify OTP
        if user.otp != entered_otp:
            return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

        # Update the password
        user.password = make_password(new_password)
        user.otp = None  # Clear OTP after successful verification
        user.save()

        return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)
