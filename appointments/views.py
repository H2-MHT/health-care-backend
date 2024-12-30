from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status
from appointments.models import Appointment
from datetime import datetime
import json
from django.views.decorators.csrf import csrf_exempt
from .serializers import RescheduleAppointmentSerializer

from rest_framework.response import Response

class RescheduleAppointmentView(APIView):
    def patch(self, request, pk):
        try:
            # Retrieve the appointment by primary key (pk)
            appointment = Appointment.objects.get(pk=pk)

            # Check if the user is a doctor
            if request.user.role != "Doctor":
                return Response({"error": "You must be logged in as a doctor to reschedule appointments."}, status=status.HTTP_403_FORBIDDEN)

            # Check if the authenticated doctor is the one assigned to the appointment
            if appointment.doctor.user != request.user:
                return Response({"error": "You are not the doctor for this appointment."}, status=status.HTTP_403_FORBIDDEN)

            # Proceed if the doctor is authorized to reschedule
            serializer = RescheduleAppointmentSerializer(data=request.data)
            if serializer.is_valid():
                # Update the appointment's date and time
                new_date_time = serializer.validated_data['new_date_time']
                appointment.date_time = new_date_time
                appointment.status = "Pending"  # Set status as pending after rescheduling
                appointment.save()

                # Format the updated date and time
                updated_day = new_date_time.strftime("%A, %d %B %Y")
                updated_time = new_date_time.strftime("%H:%M %p")

                # Get the patient's full name
                patient_user = appointment.patient.user  # Access the related User model for the patient
                patient_name = f"{patient_user.first_name} {patient_user.last_name}"

                # Return the response with patient name, updated time, and updated day
                return Response({
                    "message": "Appointment rescheduled successfully.",
                    "patient_name": patient_name,
                    "updated_day": updated_day,
                    "updated_time": updated_time
                }, status=status.HTTP_200_OK)

            # If the serializer is not valid, return the errors
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

            # Validate input
            if not patient_id or not appointment_id or not new_status:
                return JsonResponse({"error": "Patient ID, Appointment ID, and Status are required."}, status=400)

            # Fetch the appointment for the given patient
            appointment = Appointment.objects.filter(id=appointment_id, patient_id=patient_id).first()
            if not appointment:
                return JsonResponse({"error": "No appointment found for this patient."}, status=404)

            # Restrict status update to "Pending" -> ["Confirmed", "Cancelled"]
            if appointment.status != "Pending" or new_status not in ["Confirmed", "Cancelled"]:
                return JsonResponse({"error": "Status can only be updated from 'Pending' to 'Confirmed' or 'Cancelled'."}, status=400)

            # Update the status
            appointment.status = new_status
            appointment.save()

            return JsonResponse({
                "message": "Appointment status updated successfully.",
                "appointment_id": appointment.id,
                "new_status": appointment.status
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON data."}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Invalid request method. Use PATCH."}, status=405)
