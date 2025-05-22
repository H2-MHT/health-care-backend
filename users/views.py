from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
import logging
from .serializers import (
    EducationSerializer,
    SkillSerializer,
    NotesSerializer,
    DeviceAccessSerializer,
    UserRoleSerializer,
    AppLanguageSerializer,
    SupportTickeSerializer,
)
from .models import(
    Education,
    User,
    TwoFactorMethod,
    Skill,
    Notes,
    DeviceAccess,
    AppLanguage,
    Ticket,
)
import json
from django.http import QueryDict
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from patients.models import Patient

logger = logging.getLogger(__name__)

class ViewSkills(APIView):
    """
    API to view all available skills.
    """
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            skills = Skill.objects.all()
            serializer = SkillSerializer(skills, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                    {"message": f"An unexpected error occurred: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
class EducationAPIView(APIView):
    """
    API to create, update, retrieve, and delete an Education record for a user.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """Create a new education record"""
        try:

            if isinstance(request.data, QueryDict):
                data = request.data.dict()
            else:
                data = request.data.copy()

            if 'skills' in data and isinstance(data['skills'], str):
                try:
                    data['skills'] = json.loads(data['skills'])
                    if not isinstance(data['skills'], list):
                        data['skills'] = [data['skills']]
                except json.JSONDecodeError:
                        data['skills'] = []

            if 'media' in data:
                del data['media']

            serializer = EducationSerializer(data=data, context={'request': request})

            if serializer.is_valid():
                serializer.save(user=request.user)
                return Response(
                    {"message": "Education record created successfully.", "data": serializer.data},
                    status=status.HTTP_201_CREATED
                )

            return Response(
                {"message": "Invalid data provided.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.exception("Unexpected error creating education record: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    def get(self, request, *args, **kwargs):
        """Retrieve all education records for the authenticated user"""
        try:
            education = Education.objects.filter(user=request.user).order_by("-id")
            serializer = EducationSerializer(education, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("Unexpected error fetching education records: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

class UpdateEducationAPIView(APIView):
    """
    API to update or delete an Education record for a user.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, education_id, *args, **kwargs):
        """Update an existing education record"""
        try:
            education = Education.objects.filter(id=education_id, user=request.user).first()
            if not education:
                return Response(
                    {"message": "Education record not found."},
                    status=status.HTTP_404_NOT_FOUND
                )

            if isinstance(request.data, QueryDict):
                data = request.data.dict()
            else:
                data = request.data.copy()

            if 'skills' in data and isinstance(data['skills'], str):
                try:
                    data['skills'] = json.loads(data['skills'])
                    if not isinstance(data['skills'], list):
                        data['skills'] = [data['skills']]
                except json.JSONDecodeError:
                        data['skills'] = []

            if 'media' in data:
                del data['media']


            serializer = EducationSerializer(education, data=data, context={'request': request}, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {"message": "Education record updated successfully.", "data": serializer.data},
                    status=status.HTTP_200_OK
                )

            return Response(
                {"message": "Invalid data provided.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception("Unexpected error updating education record: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    def delete(self, request, education_id, *args, **kwargs):
        """Delete an education record"""
        try:
            education = Education.objects.filter(id=education_id, user=request.user).first()
            if not education:
                return Response(
                    {"message": "Education record not found."},
                    status=status.HTTP_404_NOT_FOUND
                )

            education.delete()
            return Response(
                {"message": "Education record deleted successfully."},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.exception("Unexpected error deleting education record: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
            

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
            

class NotesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """Retrieve notes created by the logged-in user (Doctor or Patient)."""
        try:
            notes = Notes.objects.filter(user=request.user).order_by("-created_at")
            serializer = NotesSerializer(notes, many=True)
            return Response(
                {"message": "Notes retrieved successfully.", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def post(self, request, *args, **kwargs):
        """Allow the logged-in user (Doctor or Patient) to create their own note."""
        try:
            serializer = NotesSerializer(data=request.data, context={"request": request})
            if serializer.is_valid():
                serializer.save(user=request.user)  # Assign logged-in user as the creator
                return Response(
                    {"message": "Note created successfully.", "data": serializer.data},
                    status=status.HTTP_201_CREATED,
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def put(self, request, *args, **kwargs):
        """Update a user's note by replacing the title and updating note content correctly."""
        try:
            note_id = kwargs.get("pk")
            note = Notes.objects.filter(id=note_id, user=request.user).first()

            if not note:
                return Response({"error": "Note not found or you don't have permission."}, status=status.HTTP_404_NOT_FOUND)

            # Replace title if provided
            if "title" in request.data:
                note.title = request.data["title"]  # Completely replace the existing title

            # Replace note if provided
            if "note" in request.data:
                new_data = request.data["note"]

                if isinstance(new_data, str):  # in string before updating
                    note.note = new_data  # Completely replace existing note content

            note.save()
            serializer = NotesSerializer(note, context={"request": request})

            return Response({"message": "Note updated successfully.", "data": serializer.data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"message": f"An error occurred: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)



    def delete(self, request, *args, **kwargs):
        """Allow users to delete their own notes."""
        try:
            note_id = kwargs.get("pk")
            try:
                note = Notes.objects.get(id=note_id, user=request.user)  # Ensure they own the note
            except Notes.DoesNotExist:
                return Response({"error": "Note not found or you do not have permission to delete it."},
                                status=status.HTTP_404_NOT_FOUND)

            note.delete()
            return Response({"message": "Note deleted successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

class DeviceAccessListCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            if isinstance(request.data, list):
                serializer = DeviceAccessSerializer(data=request.data, many=True)
            else:
                serializer = DeviceAccessSerializer(data=request.data)
            
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def get(self, request):
        """
        Fetch all device access records or filter based on active_sessions status.
        Use query parameter 'active=true' or 'active=false' to filter.
        """
        try:
            active_param = request.query_params.get('active')
            if active_param is not None:
                if active_param.lower() == 'true':
                    devices = DeviceAccess.objects.filter(user=request.user, active_sessions=True)
                elif active_param.lower() == 'false':
                    devices = DeviceAccess.objects.filter(user=request.user, active_sessions=False)
                else:
                    return Response(
                        {"error": "Invalid query parameter. Use 'active=true' or 'active=false'."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                devices = DeviceAccess.objects.filter(user=request.user)  # Get all records
            if not devices.exists():
                return Response({"message": "No device access records found."},
                                status=status.HTTP_404_NOT_FOUND)
            serializer = DeviceAccessSerializer(devices, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request):
        # Get data from request
        data = request.data
        user_id = data.get('user_id')
        device_id = data.get('id')
        active_sessions = data.get('active_sessions')

        if not user_id or not device_id:
            return Response({"error": "user_id and id are required"}, status=status.HTTP_400_BAD_REQUEST)

        if request.user.id != user_id:
            return Response({"error": "You can only update your own device access record"},
                            status=status.HTTP_403_FORBIDDEN)

        if request.user.role not in ['Patient', 'Doctor', 'Clinic']:
            return Response({"error": "You don't have permission to update this record"},
                            status=status.HTTP_403_FORBIDDEN)

        try:
            device_access = DeviceAccess.objects.get(pk=device_id, user_id=user_id)
        except DeviceAccess.DoesNotExist:
            return Response({"error": "Device access record not found or you don't have permission to update it"},
                            status=status.HTTP_404_NOT_FOUND)

        # Update only the `active_sessions` field if provided
        if active_sessions is not None:
            device_access.active_sessions = active_sessions
            device_access.save()
            return Response({"message": "Session status updated successfully", 
                            "data": {"active_sessions": device_access.active_sessions}}, 
                            status=status.HTTP_200_OK)
        return Response({"error": "No valid field provided for update"}, status=status.HTTP_400_BAD_REQUEST)
    
    
class SwitchRoleAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def blacklist_old_tokens(self, user):
        tokens = OutstandingToken.objects.filter(user=user)
        for token in tokens:
            if not BlacklistedToken.objects.filter(token=token).exists():
                BlacklistedToken.objects.create(token=token)

    def generate_new_tokens(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

    def post(self, request):
        user = request.user

        if user.role == 'Doctor' and not user.is_doctor_switched:
            user.role = 'Patient'
            user.is_doctor_switched = True
            user.save()

            # create patient record if it doesn't exist
            Patient.objects.get_or_create(user=user)

        elif user.role == 'Patient' and user.is_doctor_switched:
            user.role = 'Doctor'
            user.is_doctor_switched = False
            user.save()

        else:
            return Response(
                {"detail": "Role switching is not permitted for your user type."},
                status=status.HTTP_403_FORBIDDEN
            )

        self.blacklist_old_tokens(user)
        tokens = self.generate_new_tokens(user)
        serializer = UserRoleSerializer(user)

        return Response({
            "detail": "Role switched successfully.",
            "user": serializer.data,
            "tokens": tokens
        }, status=status.HTTP_200_OK)
        

class UserLanguagePreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AppLanguageSerializer(
            data=request.data,
            context={
                'request': request
                }
            )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    'message': 'Language preference saved successfully',
                    'data': serializer.data
                    }, 
                status=status.HTTP_200_OK
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self, request):
        user = request.user

        try:
            # Get the latest or default language set by the user
            language = AppLanguage.objects.filter(user=user).order_by('-created_at').first()

            if not language:
                return Response({"message": "No language Available."}, status=status.HTTP_200_OK)

            return Response({
                "language_name": language.language_name,
                "code": language.code,
                "created_at": language.created_at,
                "updated_at": language.updated_at
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class SupportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SupportTickeSerializer(data=request.data)
        if serializer.is_valid():
            ticket = serializer.save(user=request.user)
            return Response({
                "message": "Support ticket raised successfully",
                "data": {
                    "id": ticket.id,
                    "title": ticket.title,
                    "description": ticket.description,
                    "ticket_id": ticket.ticket_id,
                    "status": ticket.status,
                    "attachment": ticket.attachment.url if ticket.attachment else None,
                    "admin_comment": ticket.admin_comment,
                    "created_at": ticket.created_at,
                    "updated_at": ticket.updated_at
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self, request, ticket_id=None):
        if ticket_id:
            # Retrieve specific query
            try:
                ticket = Ticket.objects.get(ticket_id=ticket_id, user=request.user)
                serializer = SupportTickeSerializer(ticket)
                return Response({
                    "message": "Support ticket details retrieved successfully",
                    "data": serializer.data
                }, status=status.HTTP_200_OK)
            except Ticket.DoesNotExist:
                return Response({
                    "message": "Ticket not found",
                    "data": {}
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            # Retrieve all queries
            tickets = Ticket.objects.filter(user=request.user).order_by('-created_at')
            serializer = SupportTickeSerializer(tickets, many=True)
            return Response({
                "message": "Support tickets retrieved successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
            
    def patch(self, request, ticket_id):
        try:
            ticket = Ticket.objects.get(ticket_id=ticket_id, user=request.user)
            serializer = SupportTickeSerializer(ticket, data=request.data, partial=True)
            if serializer.is_valid():
                ticket = serializer.save()
                return Response({
                    "message": "Support ticket updated successfully",
                    "data": {
                        "id": ticket.id,
                        "title": ticket.title,
                        "description": ticket.description,
                        "ticket_id": ticket.ticket_id,
                        "status": ticket.status,
                        "attachment": ticket.attachment.url if ticket.attachment else None,
                        "created_at": ticket.created_at,
                        "updated_at": ticket.updated_at
                    }
                }, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Ticket.DoesNotExist:
            return Response({
                "message": "Ticket not found",
                "data": {}
            }, status=status.HTTP_404_NOT_FOUND)
            
    def delete(self, request):
        ticket_id = request.data.get('ticket_id')
        if not ticket_id:
            return Response({"message": "Ticket ID is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            ticket = Ticket.objects.get(ticket_id=ticket_id, user=request.user)
            ticket.delete()
            return Response({"message": "Support ticket deleted successfully"}, status=status.HTTP_200_OK)
        except Ticket.DoesNotExist:
            return Response({"message": "Ticket not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST) 
        
