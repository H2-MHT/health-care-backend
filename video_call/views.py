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
from .models import (
            Agoratoken, 
            Recording, 
            BookedAppointment, 
            Doctor, 
            Patient,
            MeetingRoom
)
from django.core.files.base import ContentFile
from django.db.models import Q
import uuid

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
        print(email1_sanitized, email2_sanitized)

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

class GenerateAgoraToken(APIView):
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
                "token": senderToken,
                "record_token": recorder_token
            }
        )

        Agoratoken.objects.update_or_create(
            user=receiver_user,
            defaults={
                "userID": receiver_user.id,
                "token": receiverToken,
                "record_token": recorder_token
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
    def post(self, request):
        try:
            sender_id = request.data.get("senderID", "")
            receiver_id = request.data.get("receiverID", "")

            if not sender_id:
                return JsonResponse({"error": "Sender ID is required"}, status=400)
            
            if not receiver_id:
                return JsonResponse({"error": "Receiver ID is required"}, status=400)
            
            try:
                sender = User.objects.get(pk=sender_id)
            except User.DoesNotExist:
                return JsonResponse({"error": "Sender user does not exist"}, status=404)
            
            try:
                receiver = User.objects.get(pk=receiver_id)
            except User.DoesNotExist:
                return JsonResponse({"error": "Receiver user does not exist"}, status=404)
            
            try:
                senderToken = Agoratoken.objects.get(user=sender)
            except Agoratoken.DoesNotExist:
                return JsonResponse({"error": "Token has not been generated yet for sender"}, status=404)
            
            try:
                receiverToken = Agoratoken.objects.get(user=receiver)
            except Agoratoken.DoesNotExist:
                return JsonResponse({"error": "Token has not been generated yet for receiver"}, status=404)
            
            channel_name = sender.agora_channel_name
            currentUserFirebaseToken = sender.device_token
            remoteUserFirebaseToken = receiver.device_token
            
            return JsonResponse({
            "message": "Retrieved successfully",
            "app_id": APP_ID,
            "channel": channel_name,
            "recorder_token": senderToken.record_token,
            "currentUser": {"currentUserName": sender.get_full_name(),"uid": sender.id,"senderToken": senderToken.token,"firebase_token": currentUserFirebaseToken},
            "remoteUser": {"remoteUserName": receiver.get_full_name(), "uid": receiver.id,"receiverToken.": receiverToken.token,"firebase_token": remoteUserFirebaseToken}
        })
            
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
                "bucket": AZURE_CONTAINER,
                "secretKey": AZURE_ACCOUNT_KEY,
                "vendor": 5,
                "region": 0,
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
        senderID =request.data.get('senderID')
        receiverID = request.data.get('receiverID')

        if not channel_name or not resource_id or not sid:
            return JsonResponse({"error": "Missing required fields"}, status=400)
        
        try: 
            sender = User.objects.get(pk=senderID)
        except User.DoesNotExist:
            return JsonResponse({"error": "Sender not found"}, status=404)
        
        try: 
            receiver = User.objects.get(pk=receiverID)
        except User.DoesNotExist:
            return JsonResponse({"error": "Receiver not found"}, status=404)

        try:
            response = stop_agora_recording(channel_name, resource_id, sid)
            recording_file = response['serverResponse']['fileList']
            recording = Recording(sender=sender, receiver=receiver, title="Consultation Recording")
            recording.video_file = recording_file
            recording.save()

            return JsonResponse({"message": "Recording stopped successfully", "data": response})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

class RecordingListAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
       try:
            user = request.user
            recordings = Recording.objects.filter(Q(sender=user) | Q(receiver=user))
            
            data = [
                {
                    "id": recording.id,
                    "name": request.user.get_full_name(),
                    "title": recording.title,
                    "file_url": recording.video_file.url if recording.video_file else "",
                    "created_at": recording.created_at,
                }
                for recording in recordings
            ]
            return JsonResponse(
                {
                    "message": "Recording list retrieved successfully",
                    "recording": data
                },
                status=200
            )
       except Exception as e:
           return JsonResponse({"error": str(e)}, status=500)

class CreateMeetingLink(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            data = request.data
            appointment_id = data.get('appointment_id')
            doctor_user_id = data.get('doctor_user_id')
            patient_user_id = data.get('patient_user_id')
            
            if not appointment_id or not doctor_user_id or not patient_user_id:
                return JsonResponse({'message': 'missing required fields'}, status=400)
            
            try:
                user1 = User.objects.get(pk=doctor_user_id)
            except User.DoesNotExist:
                return JsonResponse({'meesage': "Doctor not found"}, status=400)
            
            try:
                user2 = User.objects.get(pk=patient_user_id)
            except User.DoesNotExist:
                return JsonResponse({'meesage': "Patient not found"}, status=400)
            
            try:
                appointment = BookedAppointment.objects.get(pk=appointment_id)
            except BookedAppointment.DoesNotExist:
                return JsonResponse({'meesage': "Appointment not found"}, status=400)
            
            doctor = Doctor.objects.filter(user=user1).first()   
            if not doctor:
                return JsonResponse({'message': "User is not a doctor"}, status=400)
            
            patient = Patient.objects.filter(user=user2).first()   
            if not patient:
                return JsonResponse({'meesage': "User is not a patient"}, status=400)
            
            bookedAppointemnt = MeetingRoom.objects.filter(appointment=appointment).exists()        
            if bookedAppointemnt:
                return JsonResponse({'message':'This appointment already has a meeting link.'}, status=400)
            
            def sanitized_email(email):
                    return email.replace("@", "_").replace(".", "_")
                
            unique_id = uuid.uuid4().hex[:10]
            channel_name = f"meeting_{unique_id}"   
              
            base_url = request.build_absolute_uri('/')[:-1]
            meeting_link = f"meeting?channel={channel_name}"
            
            MeetingRoom.objects.create(
                doctor=doctor,
                patient=patient,
                appointment=appointment,
                link=meeting_link,
                channel_name=channel_name,
                status="Pending"
            ) 
            return JsonResponse({'message': 'Meeting link generated successfully'}, status=200)
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
        
    def patch(self, request):
        try:
            appointment_id = request.data.get('appointment_id')
            try:
                appointment = BookedAppointment.objects.get(pk=appointment_id)
            except BookedAppointment.DoesNotExist:
                return JsonResponse({'meesage': "Appointment not found"}, status=400)
            try:
                meeting = MeetingRoom.objects.get(appointment=appointment)
            except MeetingRoom.DoesNotExist:
                return JsonResponse({'meesage': "Meeting room not found"}, status=400)
            
            meeting.status = 'Expired'
            meeting.save()

            return JsonResponse({'message': "link status updated to expired successfully"}, status=200)
        
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
        
class GenerateMeetingToken(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            data = request.data
            uid = data.get('uid')
            appointment_id = data.get('appointment_id')
            EXPIRE_TIME_IN_SECONDS = 60 * 60 * 2
            
            if not uid:
                return JsonResponse({'message': 'uid is required'}, status=400)
            
            if not appointment_id:
                return JsonResponse({'meessage':'appointment id is required'}, status=400)
            
            try:
                user = User.objects.get(pk=uid) 
            except User.DoesNotExist:
                return JsonResponse({'message': 'user not found'}, status=400)
      
            try:
                appointment = BookedAppointment.objects.get(pk=appointment_id) 
            except BookedAppointment.DoesNotExist:
                return JsonResponse({'message': 'appointment not found'}, status=400)
            
            current_user = request.user
            if current_user.id != appointment.doctor and current_user.id != appointment.patient:
                return JsonResponse({'message': 'You are not part of this appointment'}, status=403)
            
            if current_user.id == appointment.doctor:
                remote_user_id = appointment.patient
            else:
                remote_user_id = appointment.doctor

            try:
                remote_user = User.objects.get(pk=remote_user_id)
            except User.DoesNotExist:
                return JsonResponse({'message': 'Remote user not found'}, status=400)
            
            try:
                meeting = MeetingRoom.objects.get(appointment=appointment) 
            except MeetingRoom.DoesNotExist:
                return JsonResponse({'message': 'link was not generated'}, status=400)
            
            if meeting.status == 'Expired':
                return JsonResponse({'message': 'Link was expired'}, status=400)
            
            channel_name = meeting.channel_name
            expire_timestamp = int(time.time()) + EXPIRE_TIME_IN_SECONDS
            
            meetingToken = RtcTokenBuilder.buildTokenWithUid(
                APP_ID, APP_CERTIFICATE, channel_name, int(current_user.id), 1, expire_timestamp)
            
            return JsonResponse(
                {   
                    "mesage": "Token generated successfully",
                    "current_user_id": current_user.id,
                    "currentUserName": current_user.get_full_name(),
                    "remote_user_id": remote_user.id,
                    "remoteUserName": remote_user.get_full_name(),
                    "channel_name": channel_name,
                    "token": meetingToken,
                    "app_id": APP_ID
                }
                )
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)         
            