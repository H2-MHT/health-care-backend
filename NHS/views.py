from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests

# Medicine Guide API
class NHSAPIResourceAPIView(APIView):
    def get(self, request):
        # Get the query parameter for the category (conditions, medicines, etc.)
        category = request.query_params.get('category', None)
        resource = request.query_params.get('resource', None)  # Specific resource like condition slug
        
        # Base URL for NHS API
        base_url = settings.NHS_BASE_URL

        if category:
            # Build the URL dynamically based on the category and resource
            url = f"{base_url}/{category}/"
            
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
        
class NHSSymptomAPIView(APIView):
    def get(self, request):
        # Get query parameter 'name' (e.g., 'Anal pain', 'Blood in semen')
        name = request.query_params.get('name', None)
        
        
        # Base URLs for NHS API
        symptom_base_url = settings.NHS_SYMPTOM_BASE_URL
        condition_base_url = settings.NHS_CONDITION_BASE_URL

        
        # API headers with your provided API key
        headers = {
            "Content-Type": "application/json",
            "apikey": settings.NHS_API_KEY
        }

        matching_symptoms = []

        if name:
            # First, search in the symptoms API
            symptom_url = f"{symptom_base_url}?name={name}"
            matching_symptoms = self.fetch_symptom_data(symptom_url, name, headers)

            # If no matching symptoms found, search in the conditions API
            if not matching_symptoms:
                condition_url = f"{condition_base_url}{name.lower().replace(' ', '-')}/"
                matching_symptoms = self.fetch_condition_data(condition_url, headers)

        return Response({"symptoms": matching_symptoms}, status=status.HTTP_200_OK)

    def fetch_symptom_data(self, url, name, headers):
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            name_lower = name.lower()

            return [
                {
                    "name": item.get("name"),
                    "match_type": "name" if name_lower in item.get("name", "").lower() else "alternateName",
                    "treatment_options": self.fetch_treatment_data(item.get("url"), headers)
                }
                for item in data.get("significantLink", [])
                if name_lower in item.get("name", "").lower() or any(name_lower in alt.lower() for alt in item.get("mainEntityOfPage", {}).get("alternateName", []))
            ]

        return []

    def fetch_condition_data(self, url, headers):
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return [{
                "name": data.get("name"),
                "treatment_options": self.fetch_treatment_data(url, headers)
            }]

        return []

    def fetch_treatment_data(self, base_url, headers):
        if not base_url:
            return []

        urls = [
            base_url,
            f"{base_url}#causes",
            f"{base_url}#self-care",
            f"{base_url}#non-urgent-medical-help",
            f"{base_url}#urgent-medical-help",
            f"{base_url}#overview"
        ]

        treatment_data = []

        for url in urls:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                treatment_data.append({
                    "url": url,
                    "data": response.json()
                })

        return treatment_data

# The above code defines a Django view that interacts with the NHS API to fetch information about symptoms and their treatment options.
# It includes error handling for request exceptions and API response status codes.
# The `NHSSymptomAPIView` class handles GET requests to search for symptoms based on a name query parameter.
# It first checks the symptoms API and, if no results are found, checks the conditions API.
# The `fetch_symptom_data`, `fetch_condition_data`, and `fetch_treatment_data` methods are used to retrieve and process the data from the API.