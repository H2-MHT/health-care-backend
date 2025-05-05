from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests

class NHSAPIResourceAPIView(APIView):
    def get(self, request):
        # Get the query parameter for the category (conditions, medicines, etc.)
        category = request.query_params.get('category', None)
        resource = request.query_params.get('resource', None)  # Specific resource like condition slug
        
        # Base URL for NHS API
        base_url = settings.NHS_BASE_URL

        if category:
            # Build the URL dynamically based on the category and resource
            url = f"{base_url}{category}/"
            
            # If a specific resource (slug) is provided, add it to the URL
            if resource:
                url += f"{resource}/"
        else:
            return Response({"detail": "Category is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        # API headers with your provided API key
        headers = {
            "Content-Type": "application/json",
            "apikey": settings.NHS_API_KEY
        }

        try:
            # GET request to the NHS API
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                # Return the data from the NHS API
                return Response(response.json(), status=status.HTTP_200_OK)
            else:
                # not successful, return the error message
                return Response({"detail": "Error fetching data from NHS API."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        except requests.exceptions.RequestException as e:
            # Handle any request errors
            return Response({"detail": f"Request error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        