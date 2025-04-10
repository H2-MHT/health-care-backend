import os
import json
import time
import random
import requests
import base64
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
from .models import Agoratoken

# Agora credentials
APP_ID = settings.APP_ID
APP_CERTIFICATE = settings.APP_CERTIFICATE
AGORA_CUSTOMER_ID = "15a98e4c4e994fbca731b9e0730d9485"
AGORA_CUSTOMER_SECRET = "2b1d092a24b948219a11feea23ab0fcb"

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

AZURE_ACCOUNT_NAME = os.getenv("AZURE_ACCOUNT_NAME")
AZURE_ACCOUNT_KEY = os.getenv("AZURE_ACCOUNT_KEY")
AZURE_CONTAINER = os.getenv("AZURE_CONTAINER")

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

        senderToken = RtcTokenBuilder.buildTokenWithUid(
            APP_ID, APP_CERTIFICATE, channel_name, int(senderID), 1, expire_timestamp
        )
        
        receiverToken = RtcTokenBuilder.buildTokenWithUid(
            APP_ID, APP_CERTIFICATE, channel_name, int(receiverID), 1, expire_timestamp
        )
        
        recorder_token = RtcTokenBuilder.buildTokenWithUid(
            APP_ID, APP_CERTIFICATE, channel_name, 0, 1, expire_timestamp
        )

        sender.agora_channel_name = channel_name
        receiver.agora_channel_name = channel_name
        sender.save()
        receiver.save()
        
        try: 
            sender_user = User.objects.get(pk=senderID)
        except User.DoesNotExist:
            return JsonResponse({"error": "Sender user does not exist"}, status=404)
        
        try:
            receiver_user = User.objects.get(pk=receiverID)
        except User.DoesNotExist:
            return JsonResponse({"error": "Receiver user does not exist"}, status=404)
        
        Agoratoken.objects.update_or_create(
            user=sender_user,
            defaults={
                "userID": sender_user.id,
                "receiver_token": senderToken
            }
        )

        Agoratoken.objects.update_or_create(
            user=receiver_user,
            defaults={
                "userID": receiver_user.id,
                "token": receiverToken
            }
        )
        
        return JsonResponse({
            "app_id": APP_ID,
            "channel": channel_name,
            "recorder_token": recorder_token,
            "currentUser": {"currentUserName": sender.get_full_name(),"uid": sender.id,"senderToken": senderToken,"firebase_token": currentUserFirebaseToken},
            "remoteUser": {"remoteUserName": receiver.get_full_name(), "uid": receiver.id,"receiverToken": receiverToken,"firebase_token": remoteUserFirebaseToken}
        })

class AgoraTokenView(APIView):
    def get(self, request):
        try:
            user_id = request.query_params.get("user_id", "")
            if not user_id:
                return JsonResponse({"error": "User ID is required"}, status=400)
            
            try:
                user = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return JsonResponse({"error": "User does not exist"}, status=404)
            
            try:
                agoratoken = Agoratoken.objects.get(user=user)
            except Agoratoken.DoesNotExist:
                return JsonResponse({"error": "Token has not been generated yet"}, status=404)
            
            data = {
                    "app_id": APP_ID,
                    "user_id": user_id,
                    "name": user.get_full_name(),
                    "token": agoratoken.token,
                    "channel_name": user.agora_channel_name            
                }
            
            return JsonResponse(
                {
                    "message": "Retrieved successfully",
                    "data": data
                }
            )
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
            
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
  
        
def get_agora_token(channel_name):
    url = f"https://api.agora.io/v1/apps/{APP_ID}/cloud_recording/acquire"

    # Encode Customer ID and Secret in Base64
    credentials = f"{AGORA_CUSTOMER_ID}:{AGORA_CUSTOMER_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {encoded_credentials}",
    }

    payload = {
        "cname": channel_name,
        "uid": "0",
        "clientRequest": {},
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()


def start_agora_recording(channel_name, resource_id, recorder_token):
    url = f"https://api.agora.io/v1/apps/{APP_ID}/cloud_recording/resourceid/{resource_id}/mode/mix/start"

    # Encode Customer ID and Secret in Base64
    credentials = f"{AGORA_CUSTOMER_ID}:{AGORA_CUSTOMER_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {encoded_credentials}",
    }
 
    payload = {
        "cname": channel_name,
        "uid": "0",
        
        "clientRequest": {
            "token": recorder_token,
            "recordingConfig": {
                "maxIdleTime": 30,
                "streamTypes": 2,
                "channelType": 1,
                "videoStreamType": 0,
                "transcodingConfig": {
                    "width": 1280,
                    "height": 720,
                    "fps": 15,
                    "bitrate": 600,
                    "maxResolutionUid": "1",
                    "mixedVideoLayout": 1
                }
            },
            
            "storageConfig": {
                "accessKey": AZURE_ACCOUNT_NAME,
                "region": 0,
                "bucket": AZURE_CONTAINER,
                "secretKey": AZURE_ACCOUNT_KEY,
                "vendor": 4,
                "fileNamePrefix": ["recordings"]
            }
        }
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()

def stop_agora_recording(channel_name, resource_id, sid):
    url = f"https://api.agora.io/v1/apps/{APP_ID}/cloud_recording/resourceid/{resource_id}/sid/{sid}/mode/mix/stop"

    # Encode Customer ID and Secret in Base64
    credentials = f"{AGORA_CUSTOMER_ID}:{AGORA_CUSTOMER_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {encoded_credentials}",
    }

    payload = {
        "cname": channel_name,
        "uid": "0",
        "clientRequest": {}
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()

class StartRecordingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        channel_name = request.data.get("channel_name")
        recorder_token = request.data.get("recorder_token")
        if not channel_name:
            return JsonResponse({"error": "Channel name is required"}, status=400)

        try:
            recording_data = get_agora_token(channel_name)
            resource_id = recording_data["resourceId"]
            start_record = start_agora_recording(channel_name, resource_id, recorder_token)
            sid = start_record["sid"]

            return JsonResponse({
                "resource_id": resource_id,
                "sid": sid,
                "message": "Recording started successfully"
            })

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
        
class StopRecordingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        channel_name = request.data.get("channel_name")
        resource_id = request.data.get("resource_id")
        sid = request.data.get("sid")

        if not channel_name or not resource_id or not sid:
            return JsonResponse({"error": "Missing required fields"}, status=400)

        try:
            response = stop_agora_recording(channel_name, resource_id, sid)
            return JsonResponse({"message": "Recording stopped successfully", "data": response})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
