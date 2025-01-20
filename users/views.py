from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import EducationSerializer


class EducationAPIView(APIView):
    """
    API endpoint to create a new Education entry.

    POST:
        Creates a new education record with associated skills and media.

        Request Payload (JSON):
        {
            "school": "string",                     # Name of the school (required)
            "degree": "string",                     # Degree obtained (optional)
            "field_of_study": "string",             # Field of study (optional)
            "start_date": "YYYY-MM-DD",             # Start date of education (required)
            "end_date": "YYYY-MM-DD",               # End date of education (optional)
            "grade": "string",                      # Grade or GPA (optional)
            "activities_and_societies": "string",   # Activities and societies (optional)
            "description": "string",                # Description or notes (optional)
            "skills": [                             # List of skills (optional)
                {"name": "string"}
            ],
            "media": [                              # List of media files (optional)
                {
                    "file": "string (file URL or path)",
                    "description": "string"
                }
            ]
        }

        Response (JSON):
        Success (201 Created):
        {
            "id": "integer",                         # ID of the created Education entry
            "school": "string",
            "degree": "string",
            "field_of_study": "string",
            "start_date": "YYYY-MM-DD",
            "end_date": "YYYY-MM-DD",
            "grade": "string",
            "activities_and_societies": "string",
            "description": "string",
            "skills": [
                {"id": "integer", "name": "string"}
            ],
            "media": [
                {"id": "integer", "file": "string", "description": "string"}
            ]
        }

        Error (400 Bad Request):
        {
            "error": "Validation errors for the provided data."
        }
    """

    def post(self, request):
        serializer = EducationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
