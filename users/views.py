from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
import logging
from .serializers import EducationSerializer, SkillSerializer, NotesSerializer
from .models import Education, User, TwoFactorMethod, Skill, Notes
import json
from django.http import QueryDict
from utils.search import search
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
            return Response({"message": "Note deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

class SearchAPIView(APIView):
    def get(self, request):
        try:
            query = request.query_params.get("q", "").strip()
            search_role = request.query_params.get("search_role","").strip()
            if not query or not search_role:
                return Response({"message":"No data found"},status=status.HTTP_404_NOT_FOUND)
            user_role = getattr(request.user, "role", None) or request.query_params.get(request.user, "role")   # calling search function from utils
            results = search(query, user_role, search_role)
            return Response(results)
        except Exception as e:
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

