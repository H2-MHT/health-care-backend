from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
# Create your views here.


class SignupView(APIView):
    def post(self, request):
        # Dummy response for sign-up
        data = {
            "message": "Signup successful",
            "status": "success"
        }
        return Response(data, status=status.HTTP_201_CREATED)


class SigninView(APIView):
    def post(self, request):
        # Dummy response for sign-in
        data = {
            "message": "Signin successful",
            "status": "success"
        }
        return Response(data, status=status.HTTP_200_OK)
