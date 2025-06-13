from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime, timedelta
import requests
import base64

FITBIT_AUTH_URL = "https://www.fitbit.com/oauth2/authorize"
FITBIT_TOKEN_URL = "https://api.fitbit.com/oauth2/token"

@api_view(['GET'])
def fitbit_login(request):
    client_id = settings.FITBIT_CLIENT_ID
    redirect_uri = settings.FITBIT_REDIRECT_URI
    scopes = "activity heartrate sleep profile"
    print(redirect_uri)

    encoded_redirect_uri = redirect_uri.replace(":", "%3A").replace("/", "%2F")
    print(encoded_redirect_uri)

    auth_url = (
        f"https://www.fitbit.com/oauth2/authorize?"
        f"response_type=code"
        f"&client_id={client_id}"
        f"&redirect_uri={encoded_redirect_uri}"
        f"&scope={scopes.replace(' ', '%20')}"
    )

    return Response({"auth_url": auth_url}, status=status.HTTP_200_OK)


@api_view(['GET'])
def fitbit_callback(request):
    code = request.query_params.get("code")
    if not code:
        return Response({"error": "Authorization code not received"}, status=status.HTTP_400_BAD_REQUEST)
    
    client_credentials = f"{settings.FITBIT_CLIENT_ID}:{settings.FITBIT_CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(client_credentials.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": settings.FITBIT_REDIRECT_URI,
    }
    
    response = requests.post(FITBIT_TOKEN_URL, headers=headers, data=data)
    if response.status_code == 200:
        token_data = response.json()
        return Response({"access_token": token_data.get("access_token")}, status=status.HTTP_200_OK)
    
    return Response({"error": "Failed to fetch access token"}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def fitbit_data(request):
    """Fetches Fitbit data for the authenticated user"""
    access_token = request.headers.get("Authorization")
    endpoint = request.query_params.get("endpoint")

    if not access_token:
        return Response({"error": "Authorization token missing"}, status=status.HTTP_401_UNAUTHORIZED)
    
    if not endpoint:
        return Response({"error": "Endpoint missing"}, status=status.HTTP_400_BAD_REQUEST)
    
    base_url = "https://api.fitbit.com/1/user/-/"
    final_url = base_url + endpoint

    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(final_url, headers=headers)

    if response.status_code == 200:
        return Response(response.json(), status=status.HTTP_200_OK)
    
    return Response({"error": "Failed to fetch Fitbit data"}, status=status.HTTP_400_BAD_REQUEST)
