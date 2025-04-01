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
from rest_framework.permissions import IsAuthenticated
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

    def send_notification(self, device_token, title, body, caller, senderUserId, receiverUserId):
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
                    "action": "ring",
                    "senderUserId": senderUserId,
                    "receiverUserId":receiverUserId
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
            senderUserId = data.get("senderUserId")
            receiverUserId = data.get("receiverUserId")

            if not device_token or not caller:
                return JsonResponse({"success": False, "error": "deviceToken and caller are required"}, status=400)

            title = "Incoming Video Call"
            body = f"{caller} is calling you."

            response_id = firebase_service.send_notification(device_token, title, body, caller, senderUserId, receiverUserId)

            return JsonResponse({
                "success": True,
                "message": "Notification sent successfully",
                "title": received_title,
                "body": description,
                "message_id": response_id,
                "senderUserId": senderUserId,
                "receiverUserId":receiverUserId
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON format"}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

APP_ID = os.getenv("APP_ID")
APP_CERTIFICATE = os.getenv("APP_CERTIFICATE")
EXPIRE_TIME_IN_SECONDS = 3600*10 
class CreateAgoraChatUserAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        
        senderID = request.data.get("senderID")
        receiverID = request.data.get("receiverID")  

        if not senderID or not receiverID:
            return JsonResponse({"error": "Both user IDs are required"}, status=400)

        try:
            sender = User.objects.get(pk=senderID)
        except User.DoesNotExist:
            return JsonResponse({"error": "Sender user does not exist"}, status=404)
    
        try:
           receiver = User.objects.get(pk=receiverID)
        except User.DoesNotExist:
            return JsonResponse({"error": "Receiver user does not exist"}, status=404)

        currentUserFirebaseToken = sender.device_token
        remoteUserFirebaseToken = receiver.device_token
        
        sender_email = sender.email
        receiver_email = receiver.email
        
        def sanitize_email(email):
          return email.replace("@", "_").replace(".", "_")

        email1_sanitized = sanitize_email(sender_email)
        email2_sanitized = sanitize_email(receiver_email)

        channel_name = f"chat_{min(email1_sanitized, email2_sanitized)}_{max(email1_sanitized, email2_sanitized)}"

        expire_timestamp = int(time.time()) + EXPIRE_TIME_IN_SECONDS

        token = RtcTokenBuilder.buildTokenWithUid(
            APP_ID, APP_CERTIFICATE, channel_name, 0, 1, expire_timestamp
        )

        sender.agora_channel_name = channel_name
        receiver.agora_channel_name = channel_name
        sender.save()
        receiver.save()

        return JsonResponse({
            "app_id": APP_ID,
            "channel": channel_name,
            "token": token,
            "currentUser": {"currentUserName": sender.get_full_name(),"uid": sender.id, "firebase_token": currentUserFirebaseToken},
            "remoteUser": {"remoteUserName": receiver.get_full_name(), "uid": receiver.id,"firebase_token": remoteUserFirebaseToken}
        })

class AgoraUserReceiverIDAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            receiverUserId = request.data.get('receiverUserId')
            agoraReceiverUserUid = request.data.get('agoraReceiverUserUid')
            
            if not receiverUserId or not agoraReceiverUserUid:
                return JsonResponse({"error": "Receiver user id and agora receiver user id are required"}, status=400)
            
            try: 
                user = User.objects.get(pk=receiverUserId)
            except User.DoesNotExist:
                return JsonResponse({"error": "Receiver user does not exist"}, status=404)
            
            user.agoraReceiverUserUid = agoraReceiverUserUid
            user.save()
            return JsonResponse({"message": "Agora receiver user id saved successfully"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
        
    def get(self, request):
        try:
            receiverUserId = request.query_params.get('receiverUserId')
            
            if not receiverUserId:
                return JsonResponse({"error": "Receiver user id is required"}, status=400)
            try:
                 user = User.objects.get(pk=receiverUserId)
            except User.DoesNotExist:
                return JsonResponse({"error": "Receiver user does not exist"}, status=400)
            
            return JsonResponse({"agoraReceiverUserUid": user.agoraReceiverUserUid})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
        
        