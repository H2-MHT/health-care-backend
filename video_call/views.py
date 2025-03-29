import os
import json
import time
import random
from django.views import View
from users.models import User
from django.http import JsonResponse
from rest_framework.views import APIView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
import firebase_admin
from firebase_admin import credentials, messaging
from agora_token_builder import RtcTokenBuilder

APP_ID = settings.APP_ID
APP_CERTIFICATE = settings.APP_CERTIFICATE

class FirebaseMessagingService:
    def __init__(self):
        try:
            key_path = "serviceAccountKey1.json" 
            if not os.path.exists(key_path):
                raise FileNotFoundError("Firebase key file not found.")

            if not firebase_admin._apps:
                cred = credentials.Certificate(key_path)
                firebase_admin.initialize_app(cred)

        except Exception as e:
            raise Exception(f"Error initializing Firebase: {e}") 

    def send_notification(self, device_token, title, body, caller):
        try:
            message = messaging.Message(
                token=device_token,
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data={
                    "type": "incoming_call",
                    "caller": caller,
                    "action": "ring"
                }
            )
            response = messaging.send(message) 
            return response 
        except Exception as e:
            return str(e)

firebase_service = FirebaseMessagingService()

@method_decorator(csrf_exempt, name='dispatch')
class SendNotificationView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            device_token = data.get("deviceToken")
            caller = data.get("caller")
            received_title = data.get('title')
            description = data.get('body')

            if not device_token or not caller:
                return JsonResponse({"success": False, "error": "deviceToken and caller are required"}, status=400)

            title = "Incoming Video Call"
            body = f"{caller} is calling you."

            response_id = firebase_service.send_notification(device_token, title, body, caller)

            return JsonResponse({
                "success": True,
                "message": "Notification sent successfully",
                "title": received_title,
                "body": description,
                "message_id": response_id
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON format"}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

APP_ID = os.getenv("APP_ID")
APP_CERTIFICATE = os.getenv("APP_CERTIFICATE")
EXPIRE_TIME_IN_SECONDS = 3600*10 
class CreateAgoraChatUserAPIView(APIView):
    def post(self, request):
        
        email1 = request.data.get("email1")
        email2 = request.data.get("email2")  

        if not email1 or not email2:
            return JsonResponse({"error": "Both user emails are required"}, status=400)

        user1 = User.objects.filter(email=email1).first()
        user2 = User.objects.filter(email=email2).first()

        if not user1 or not user2:
            return JsonResponse({"error": "Users not found"}, status=404)

        firebase_token1 = user1.device_token
        firebase_token2 = user2.device_token
        
        def sanitize_email(email):
          return email.replace("@", "_").replace(".", "_")

        email1_sanitized = sanitize_email(email1)
        email2_sanitized = sanitize_email(email2)

        channel_name = f"chat_{min(email1_sanitized, email2_sanitized)}_{max(email1_sanitized, email2_sanitized)}"
        print('channel name', channel_name)

        uid1 = random.randint(1000, 9999)
        uid2 = random.randint(1000, 9999)

        expire_timestamp = int(time.time()) + EXPIRE_TIME_IN_SECONDS

        token1 = RtcTokenBuilder.buildTokenWithUid(
            APP_ID, APP_CERTIFICATE, channel_name, uid1, 1, expire_timestamp
        )
        token2 = RtcTokenBuilder.buildTokenWithUid(
            APP_ID, APP_CERTIFICATE, channel_name, uid2, 1, expire_timestamp
        )

        user1.agora_channel_name = channel_name
        user2.agora_channel_name = channel_name
        user1.save()
        user2.save()

        return JsonResponse({
            "app_id": APP_ID,
            "channel": channel_name,
            "user1": {"email": email1, "uid": uid1, "token": token1, "firebase_token": firebase_token1},
            "user2": {"email": email2, "uid": uid2, "token": token2, "firebase_token": firebase_token2}
        })