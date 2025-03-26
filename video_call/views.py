import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import firebase_admin
from firebase_admin import credentials, messaging

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
