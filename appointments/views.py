from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status, permissions
from appointments.models import Appointment, Call, Chat
from datetime import datetime
import json
from django.views.decorators.csrf import csrf_exempt
from .serializers import RescheduleAppointmentSerializer, CallSerializer, ChatSerializer, AppointmentSerializer

from rest_framework.response import Response

class RescheduleAppointmentView(APIView):
    def patch(self, request, pk):
        try:
            appointment = Appointment.objects.get(pk=pk)

            if request.user.role != "Doctor":
                return Response({"error": "You must be logged in as a doctor to reschedule appointments."}, status=status.HTTP_403_FORBIDDEN)

            if appointment.doctor.user != request.user:
                return Response({"error": "You are not the doctor for this appointment."}, status=status.HTTP_403_FORBIDDEN)

            serializer = RescheduleAppointmentSerializer(data=request.data)
            if serializer.is_valid():
                new_date_time = serializer.validated_data['new_date_time']
                appointment.date_time = new_date_time
                appointment.status = "Confirmed"
                appointment.save()

                # Format day and time for response
                updated_day = new_date_time.strftime("%Y-%m-%d")
                updated_time = new_date_time.strftime("%I:%M %p")

                patient_name = f"{appointment.patient.user.first_name} {appointment.patient.user.last_name}"

                return Response({
                    "message": "Appointment rescheduled successfully.",
                    "patient_name": patient_name,
                    "updated_day": updated_day,
                    "updated_time": updated_time
                }, status=status.HTTP_200_OK)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Appointment.DoesNotExist:
            return Response({"error": "Appointment not found."}, status=status.HTTP_404_NOT_FOUND)

@csrf_exempt
def update_appointment_status(request):
    if request.method == "PATCH":
        try:
            # Parse JSON data from the request body
            data = json.loads(request.body)
            patient_id = data.get("patient_id")
            appointment_id = data.get("appointment_id")
            new_status = data.get("status")
            new_date = data.get("date")  # Expected format: YYYY-MM-DD
            new_time = data.get("time")  # Expected format: HH:MM (24-hour format)

            # Validate input
            if not patient_id or not appointment_id or not new_status:
                return JsonResponse({
                    "error": "Patient ID, Appointment ID, and Status are required."
                }, status=400)

            # Validate date and time if provided
            if new_date:
                try:
                    new_date = datetime.strptime(new_date, "%Y-%m-%d").date()
                except ValueError:
                    return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

            if new_time:
                try:
                    new_time = datetime.strptime(new_time, "%I:%M %p").time()
                except ValueError:
                    return JsonResponse({"error": "Invalid time format. Use hh:mm AM/PM."}, status=400)

            # Fetch the appointment for the given patient
            appointment = Appointment.objects.filter(id=appointment_id, patient_id=patient_id).first()
            if not appointment:
                return JsonResponse({"error": "No appointment found for this patient."}, status=404)

            # Handle cancellation separately
            if new_status == "Cancelled":
                appointment.status = new_status
                appointment.date = new_date if new_date else appointment.date
                appointment.time = new_time if new_time else appointment.time
                appointment.save()
                return JsonResponse({
                    "message": "Appointment successfully cancelled.",
                    "appointment_id": appointment.id,
                    "new_status": appointment.status,
                    "new_date": appointment.date,
                    "new_time": appointment.time.strftime("%I:%M %p")
                }, status=200)

            # Restrict other status updates to "Pending" -> ["Confirmed"]
            if appointment.status != "Pending" or new_status != "Confirmed":
                return JsonResponse({
                    "error": "Status can only be updated from 'Pending' to 'Confirmed'."
                }, status=400)

            # Update the status, date, and time
            appointment.status = new_status
            appointment.date = new_date if new_date else appointment.date
            appointment.time = new_time if new_time else appointment.time
            appointment.save()

            return JsonResponse({
                "message": "Appointment status updated successfully.",
                "appointment_id": appointment.id,
                "new_status": appointment.status,
                "new_date": appointment.date,
                "new_time": appointment.time
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data."}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Invalid request method. Use PATCH."}, status=405)


class AppointmentAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    """
    GET:
    - Fetch all appointments.
    - Returns: List of Appointment objects.
      Response Structure:
        [
          {
            "id": int,
            "patient": int,
            "doctor": int,
            "clinic": int,
            "date_time": datetime,
            "status": string,
            "records": string,
            "notes": string
          }
        ]

    POST:
    - Create a new appointment.
    - Required params: patient, doctor, clinic, date_time, status.
    - Returns: Created Appointment object.
      Response Structure:
        {
          "id": int,
          "patient": int,
          "doctor": int,
          "clinic": int,
          "date_time": datetime,
          "status": string,
          "records": string,
          "notes": string
        }
    """

    def get(self, request):
        appointments = Appointment.objects.all()
        serializer = AppointmentSerializer(appointments, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = AppointmentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChatAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    """
    GET:
    - Fetch all chats.
    - Returns: List of Chat objects.
      Response Structure:
        [
          {
            "id": int,
            "appointment": int,
            "participants": [int],
            "created_at": datetime,
            "messages": [...],
            "calls": [...]
          }
        ]

    POST:
    - Create a new chat.
    - Required params: appointment, participants.
    - Returns: Created Chat object.
      Response Structure:
        {
          "id": int,
          "appointment": int,
          "participants": [int],
          "created_at": datetime,
          "messages": [...],
          "calls": [...]
        }
    """

    def get(self, request):
        chats = Chat.objects.all()
        serializer = ChatSerializer(chats, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ChatSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CallAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    """
    GET:
    - Fetch all calls for a specific chat.
    - Required params: chat_id.
    - Returns: List of Call objects.
      Response Structure:
        [
          {
            "id": int,
            "chat": int,
            "caller": int,
            "callee": int,
            "started_at": datetime,
            "ended_at": datetime,
            "call_duration": duration,
            "recording": string
          }
        ]
    """

    def get(self, request, chat_id):
        calls = Call.objects.filter(chat_id=chat_id)
        serializer = CallSerializer(calls, many=True)
        return Response(serializer.data)
