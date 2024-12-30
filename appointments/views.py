from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework import status
from appointments.models import Appointment
from datetime import datetime

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
