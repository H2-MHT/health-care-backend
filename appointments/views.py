from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework import status
from appointments.models import Appointment
from datetime import datetime
import json
from django.views.decorators.csrf import csrf_exempt


@api_view(['PATCH'])
def reschedule_appointment(request, appointment_id):
    try:
        # get the appointment
        appointment = Appointment.objects.get(id=appointment_id)
    except Appointment.DoesNotExist:
        return JsonResponse({"error": "Appointment not found."}, status=status.HTTP_404_NOT_FOUND)

    # Check if the appointment is confirmed
    if appointment.status != 'Confirmed':
        return JsonResponse({"error": "Only confirmed appointments can be rescheduled."}, status=status.HTTP_400_BAD_REQUEST)

    # Check if the user is the assigned doctor for the appointment
    if appointment.doctor.user != request.user:
        return JsonResponse({"error": "You are not authorized to reschedule this appointment."}, status=status.HTTP_403_FORBIDDEN)

    # Get the new date and time from the request
    new_date = request.data.get('date')
    new_time = request.data.get('time')

    if not new_date or not new_time:
        return JsonResponse({"error": "Date and time must be provided."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Parse the new date and time into a datetime object
        new_datetime_str = f"{new_date} {new_time.split('-')[0]}"
        new_date_time = datetime.strptime(new_datetime_str, "%Y-%m-%d %H:%M")
    except ValueError:
        return JsonResponse({"error": "Invalid date or time format."}, status=status.HTTP_400_BAD_REQUEST)

    # Update the appointment's date_time
    appointment.date_time = new_date_time
    appointment.save()

    response_data = {
        "message": "Appointment rescheduled successfully.",
        "appointment_details": {
            "doctor_name": f"{appointment.doctor.user.first_name} {appointment.doctor.user.last_name}",
            "patient_name": f"{appointment.patient.user.first_name} {appointment.patient.user.last_name}",
            "new_appointment_date": appointment.date_time.strftime("%Y-%m-%d"),
            "new_appointment_time": appointment.date_time.strftime("%I:%M %p")
        }
    }

    return JsonResponse(response_data, status=status.HTTP_200_OK)


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
