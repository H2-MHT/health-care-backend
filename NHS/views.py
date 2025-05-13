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
        # Get query parameters (category, resource)
        category = request.query_params.get('category', None)
        resource = request.query_params.get('resource', None)
        
        # Base URL for NHS API (Symptoms)
        base_url = settings.NHS_SYMPTOM_BASE_URL  # Example: "https://int.api.service.nhs.uk/nhs-website-content/symptoms/"

        if category:
            # Build the URL dynamically based on the category and resource
            url = f"{base_url}{category}/"
            
            # If a specific resource (slug) is provided, add it to the URL
            if resource:
                url += f"{resource}/"
        else:
            url = base_url  # Default to base URL if no category

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
                # Not successful, return the error message with status code
                return Response({"detail": "Error fetching data from NHS API.", "status_code": response.status_code}, status=response.status_code)
        
        except requests.exceptions.RequestException as e:
            # Handle any request errors
            return Response({"detail": f"Request error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class NHSSymptomAPIView(APIView):
    def get(self, request):
        # Get query parameter 'name' (e.g., 'Anal pain', 'Blood in semen')
        name = request.query_params.get('name', None)
        
        # Base URL for NHS API (Symptoms)
        base_url = settings.NHS_SYMPTOM_BASE_URL  # Example: "https://int.api.service.nhs.uk/nhs-website-content/symptoms/"
        url = base_url  # Default base URL

        if name:
            # If a specific name is provided, search in the symptoms list
            url += f"?name={name}"
        
        # API headers with your provided API key
        headers = {
            "Content-Type": "application/json",
            "apikey": settings.NHS_API_KEY
        }

        try:
            # GET request to the NHS API
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                name_lower = name.lower() if name else ""

                # Filtering symptoms with matching criteria
                matching_symptoms = []
                for item in data.get("significantLink", []):
                    symptom_name = item.get("name", "").lower()
                    alternate_names = [
                        alt.lower() for alt in item.get("mainEntityOfPage", {}).get("alternateName", [])
                    ]

                    if name_lower in symptom_name:
                        item['match_type'] = "name"
                        matching_symptoms.append(item)
                    elif any(name_lower in alt for alt in alternate_names):
                        item['match_type'] = "alternateName"
                        matching_symptoms.append(item)

                # Extracting treatment options (if available)
                for symptom in matching_symptoms:
                    treatment_url = symptom.get("url")
                    if treatment_url:
                        treatment_response = requests.get(treatment_url, headers=headers)
                        if treatment_response.status_code == 200:
                            treatment_data = treatment_response.json()
                            symptom['treatment_options'] = self.extract_treatment_options(treatment_data)
                
                # Response with matching symptoms and their treatments
                return Response({"symptoms": matching_symptoms}, status=status.HTTP_200_OK)
            
            else:
                # If response is not successful, return the error message
                return Response({"detail": "Error fetching data from NHS API.", "status_code": response.status_code}, status=response.status_code)
        
        except requests.exceptions.RequestException as e:
            # Handle any request errors
            return Response({"detail": f"Request error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def extract_treatment_options(self, data):
        """
        Extracts treatment options from the symptom data.
        This function can be customized based on how treatments are structured in the API response.
        """
        treatment_options = []

        # Example: Looking for treatment options in the response (modify as per API structure)
        for section in data.get("contentSubTypes", []):
            if section.get("@type") == "Treatment":
                treatment_details = {
                    "title": section.get("name"),
                    "description": section.get("description", ""),
                    "url": section.get("url")
                }
                treatment_options.append(treatment_details)
        
        return treatment_options