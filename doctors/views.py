import logging
from datetime import timedelta
import stripe
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from sendgrid.helpers.mail import Content, Email, Mail, To
from users.models import User
from users.serializers import UserSerializer
from patients.models import Patient
from django.utils.dateparse import parse_time
from django.db.models import Q
from clinics.serializers import ClinicListSerializer
from patients.serializers import PatientSerializer
from utils.whatsapp import (
    send_whatsapp_message_patient,
    send_whatsapp_message_doctor,
    appointment_cancel_notification_patient,
    appointment_cancel_notification_doctor,
    appointment_reschedule_notification_patient,
    appointment_reschedule_notification_doctor,
)
from utils.notifications import send_notification
from .models import (
    AppointmentManagement,
    CancellationPolicy,
    CommunicationPreferences,
    ConsultationSessionAndFee,
    Doctor,
    Invitation,
    NoShowPolicy,
    Referral,
    ReschedulePolicy,
    UserPreference,
    Membership,
    BookedAppointment,
    # Slot,
    DoctorSchedule,
    PatientBookAppointment,
    LicenceCertificate, 
    MediaDigest,
    DoctorWallet,
    Specialization,
)
from reviews.models import Review
from notifications.models import Notification
from .serializers import (
    AppointmentManagementSerializer,
    CancellationPolicySerializer,
    CommunicationPreferencesSerializer,
    ReferralSerializer,
    NoShowPolicySerializer,
    ReschedulePolicySerializer,
    ConsultationSettingsSerializer,
    BookedAppointmentSerializer,
    DoctorScheduleSerializer,
    LicenceCertificateSerializer, 
    MediaDigestSerializer,
    DoctorWalletSerializer,
)
from django.utils.crypto import get_random_string
import pytz
from datetime import datetime, date
from django.contrib.auth.hashers import check_password
import random
from django.conf import settings
import sendgrid
from rest_framework.exceptions import NotFound
from django.contrib.auth.hashers import make_password
from rest_framework.decorators import api_view
from utils.pagination import pagination_view, create_paginated_response
from rest_framework.parsers import MultiPartParser, FormParser, FileUploadParser
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from django.utils import timezone
from django.db.models import F
from decimal import Decimal
import uuid
import re
# Initialize logger
logger = logging.getLogger(__name__)


class DoctorListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        logger.info("User %s is requesting the doctor list.", request.user.email)
        try:
            search_key = request.query_params.get("search_key", "").strip()
            if search_key:
                doctors = User.objects.filter(first_name__istartswith=search_key) | \
                        User.objects.filter(last_name__istartswith=search_key)
            else:
                doctors = User.objects.filter(role="Doctor")
            paginated_data, headers = pagination_view(doctors, request)
            serializer = UserSerializer(paginated_data, many=True)      
            return create_paginated_response("Doctor list retrieved successfully.",serializer.data,headers)
            
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

class PublicDoctorListAPIView(APIView):

    def get(self, request, *args, **kwargs):
        try:
            search_key = request.query_params.get("search_key", "").strip()
            if search_key:
                doctors = User.objects.filter(role="Doctor",first_name__istartswith=search_key) | \
                        User.objects.filter(role="Doctor",last_name__istartswith=search_key)
            else:
                doctors = User.objects.filter(role="Doctor")
            paginated_data, headers = pagination_view(doctors, request)
            serializer = UserSerializer(paginated_data, many=True)      
            return create_paginated_response("Doctor list retrieved successfully.",serializer.data,headers)
            
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

class PublicDoctorDetailAPIView(APIView):
    def get(self, request):
        try:
            user_id = request.query_params.get('user_doctor_id')   
            if not user_id:
                return Response({"message": "User ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                doctor = Doctor.objects.get(user_id=user_id)
            except Doctor.DoesNotExist:
                return Response({"message": "Doctor not found"}, status=status.HTTP_404_NOT_FOUND)
            
            return Response({"message": "Doctor details retrieved successfully.", 
                            "data": {
                                "user_id": doctor.user_id,
                                "name": doctor.user.get_full_name(),
                                "email": doctor.user.email,
                                "phone_number": doctor.user.phone_number,
                                "residence": doctor.user.residence,
                                "city": doctor.user.city,
                                "country": doctor.user.country,
                                "languages": list(doctor.user.languages.values("id", "title")),
                                "specialty": doctor.specialty,
                                "qualifications": doctor.qualifications,
                                "experience": doctor.experience_years,
                                "rating": doctor.user.rating
                            }})
        
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
class AppointmentManagementAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, doctor_id):
        """Fetch appointment schedule (day, start time, and end time) for a specific doctor"""
        try:
            # Get all appointments for the given doctor
            appointments = AppointmentManagement.objects.filter(doctor_id=doctor_id)

            if not appointments.exists():
                return Response({"message": "No appointments found for this doctor"}, status=status.HTTP_404_NOT_FOUND)

            serializer = AppointmentManagementSerializer(appointments, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    def post(self, request):
        """Create a new appointment and generate slots"""
        try:
            logger.info(f"User is attempting to create an appointment with data: {request.data}")

            serializer = AppointmentManagementSerializer(data=request.data)
            if serializer.is_valid():
                doctor_id = request.data.get("doctor")  # Extract doctor ID from request data
                if not doctor_id:
                    return Response({"message": "Doctor ID is required"}, status=status.HTTP_400_BAD_REQUEST)

                doctor = Doctor.objects.get(id=doctor_id)  # Fetch the doctor instance

                appointment = serializer.save(doctor=doctor)

                # Generate slots immediately after saving appointment preferences
                appointment_type = request.data.get("appointment_type")
                user_id = request.data.get("user_id")
                self.generate_slots(appointment, appointment_type, user_id)

                logger.info(
                    f"User {request.user} successfully created an appointment with ID {serializer.instance.id}.")
                return Response(
                    {"message": "Appointment preference created successfully, slots generated.",
                     "data": serializer.data},
                    status=status.HTTP_201_CREATED
                )

            logger.warning(f"User {request.user} provided invalid data: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Doctor.DoesNotExist:
            return Response({"message": "Doctor not found"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.exception(f"Error creating appointment for user {request.user}: {str(e)}")
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def generate_slots(self, appointment, appointment_type, user_id):
        try:
            # Fetch consultation settings for the doctor
            settings = ConsultationSessionAndFee.objects.filter(doctor=appointment.doctor).first()
            if not settings:
                return

            # Check if the doctor has defined separate session lengths for planned and urgent slots
            session_length = None
            slot_type = appointment_type
            
            if slot_type == "Planned":
                session_length = settings.planned_session_length
                if(session_length == ""):
                    return Response({'message': 'please submit your planned session'})
            
            if slot_type == "Urgent":
                session_length = settings.urgent_session_length
                if(session_length == ""):
                    return Response({'message': 'please submit your urgent session'})

            # if settings.planned_session_length and settings.urgent_session_length:
            #     # Determine slot type dynamically if both session lengths exist
            #     session_length = settings.planned_session_length if appointment.appointment_type == "Planned" else settings.urgent_session_length
            #     slot_type = "Planned" if appointment.appointment_type == "Planned" else "Urgent"
            # elif settings.planned_session_length:
            #     session_length = settings.planned_session_length
            #     slot_type = "Planned"
            # elif settings.urgent_session_length:
            #     session_length = settings.urgent_session_length
            #     slot_type = "Urgent"
            # else:
            #     print("No valid session length found!")
            #     return


            buffer_time = settings.buffer_time

            if session_length is None:
                return

            if not isinstance(session_length, timedelta):
                session_length = timedelta(minutes=session_length)

            if not isinstance(buffer_time, timedelta):
                buffer_time = timedelta(minutes=buffer_time)

            start_time = parse_time(appointment.start_time.strftime("%H:%M:%S"))
            end_time = parse_time(appointment.end_time.strftime("%H:%M:%S"))

            slots = []
            current_time = start_time

            while current_time < end_time:
                next_time = (datetime.combine(datetime.today(), current_time) + session_length).time()
                buffer_next_time = (datetime.combine(datetime.today(), next_time) + buffer_time).time()

                if next_time > end_time:
                    break

                slot_str = f"{current_time.strftime('%H:%M')} - {next_time.strftime('%H:%M')}"
                slots.append(slot_str)

                current_time = buffer_next_time

            if not slots:
                print("No slots generated!")

            # slots_to_create = [
            #
            #     Slot(
            #         doctor=appointment.doctor,
            #         day=appointment.days,
            #         start_time=datetime.strptime(slot.split(" - ")[0], "%H:%M").time(),
            #         end_time=datetime.strptime(slot.split(" - ")[1], "%H:%M").time(),
            #         slot_type=slot_type
            #     )
            #     for slot in slots
            # ]
            formatted_slots = [
                {
                    "slot": f"{datetime.strptime(slot.split(' - ')[0], '%H:%M').strftime('%H:%M')} - {datetime.strptime(slot.split(' - ')[1], '%H:%M').strftime('%H:%M')}"
                }
                for slot in slots
            ]
            
            new_schedule = {
                appointment.days: {
                    slot_type:formatted_slots
                }
            }

            self.update_schedule(appointment.doctor.id, new_schedule, user_id)
            # slot_data = [
            #     {"time_slot": slot.time_slot, "status": "Booked" if slot.is_booked else "Available"}
            #     for slot in slots
            # ]
            #
            # response_data = {
            #     "doctor_id": appointment.doctor.id,
            #     "doctor_name": f"{appointment.doctor.first_name} {appointment.doctor.last_name}",
            #     appointment.days: [
            #         {
            #             "Planned":{
            #                 "slots": slot_data
            #             },
            #             "Urgent":{
            #                 "slots": slot_data
            #             }
            #
            #         }
            #     ],
            # }
            # # Bulk Create
            # Slot.objects.bulk_create(slots_to_create, ignore_conflicts=True)
            # print(f"{len(slots)} slots saved successfully.")

        except Exception as e:
            print(f"Error generating slots: {str(e)}")

    # def update_schedule(self, doctor_id, new_schedule):
    #     try:
    #         # Fetch existing schedule
    #         doctor = DoctorSchedule.objects.get_or_create(doctor_id=doctor_id)
    #         existing_schedule = doctor.schedule  # Get existing JSON
    #
    #
    #         # Merge the new schedule with the existing one
    #         for day, categories in new_schedule.items():
    #             if day in existing_schedule:  # If the day exists, update categories
    #                 for category, slots in categories.items():
    #                     if category in existing_schedule[day]:
    #                         existing_schedule[day][category].extend(slots)  # Append new slots
    #                     else:
    #                         existing_schedule[day][category] = slots  # Add new category
    #             else:
    #                 existing_schedule[day] = categories  # Add new day
    #
    #         # Save updated schedule
    #         doctor.schedule = existing_schedule
    #         doctor.save()
    #         print("Schedule updated successfully.")
    #
    #
    #     except Exception as e:
    #         print(f"Doctor Not Found: {str(e)}")

    def update_schedule(self, doctor_id, new_schedule, user_id):
        try:
            # Fetch the Doctor instance
            # doctor_instance = Doctor.objects.get(id=doctor_id)
            user_instance = User.objects.get(id=user_id)

            # Get or create the DoctorSchedule instance
            # doctor_schedule, created = DoctorSchedule.objects.get_or_create(doctor=doctor_instance, defaults={"schedule": {}})

            doctor_schedule, created = DoctorSchedule.objects.get_or_create(user=user_instance, defaults={"schedule": {}})

            # Get existing schedule (ensure it's a valid dictionary)
            existing_schedule = doctor_schedule.schedule or {}

            # Merge the new schedule with the existing one
            for day, categories in new_schedule.items():
                if day in existing_schedule:
                    for category, slots in categories.items():
                        if category in existing_schedule[day]:
                            existing_schedule[day][category].extend(slots)  # Append new slots
                        else:
                            existing_schedule[day][category] = slots  # Add new category
                else:
                    existing_schedule[day] = categories  # Add new day

            # Save updated schedule
            # doctor_schedule.schedule = existing_schedule
            doctor_schedule.schedule = existing_schedule
            doctor_schedule.save()

        except Exception as e:
            print(f"Error: {str(e)}")
            
    
    def put(self, request):
        """Update an existing appointment using pk from the request body"""
        try:
            pk = request.data.get("pk")
            if not pk:
                return Response({"message": "ID (pk) is required for updating."}, status=status.HTTP_400_BAD_REQUEST)

            appointment = get_object_or_404(AppointmentManagement, id=pk, user=request.user)

            serializer = AppointmentManagementSerializer(appointment, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                logger.info(f"Appointment with ID {pk} updated successfully by user {request.user}.")
                return Response(
                    {"message": "Appointment preference updated successfully.", "data": serializer.data},
                    status=status.HTTP_200_OK
                )

            logger.warning(f"Invalid data for updating appointment ID {pk}: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error while updating appointment: {str(e)}", exc_info=True)
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        try:
            day_to_delete = request.query_params.get("day")
            doctor_id = request.query_params.get("doctor_id")
            if not day_to_delete:
                return Response({"message": "Please provide a valid day to delete slots."}, status=status.HTTP_400_BAD_REQUEST)

            appointments = AppointmentManagement.objects.filter(doctor_id=doctor_id, days=day_to_delete)

            if not appointments.exists():
                return Response({"message": f"No appointments found for {day_to_delete}."}, status=status.HTTP_404_NOT_FOUND)

            doctor = Doctor.objects.filter(pk=doctor_id).first()
            user = User.objects.filter(doctor=doctor).first()
            if not doctor:
                return Response({"message":"Doctor Not Found"}, status=status.HTTP_404_NOT_FOUND)
            try:
                schedule_obj = DoctorSchedule.objects.get(user=user)
            except schedule_obj.DoesNotExist:
                return Response({"message":" Doctor Schedule not found"}, status=status.HTTP_404_NOT_FOUND)

            # Delete the appointments
            appointments.delete()

            schedule = schedule_obj.schedule
            # print(schedule)
            if day_to_delete in schedule:
                del schedule[day_to_delete]
                schedule_obj.save()

            return Response({"message": f"All slots for {day_to_delete} have been deleted successfully."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class DeleteAppointmentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        appointment_id = request.query_params.get('appointment_id')
        if not appointment_id:
            return Response({"message": "Please provide a valid appointment ID to delete."}, status=status.HTTP_400_BAD_REQUEST)
        
        managed_appointment = AppointmentManagement.objects.filter(pk=appointment_id).first()
        if not managed_appointment:
            return Response({"message": "Appointment not found"}, status=status.HTTP_404_NOT_FOUND)

        doctor = managed_appointment.doctor
        days_list = managed_appointment.days.split(',') 
        appointment_type = managed_appointment.appointment_type  
        start_time = managed_appointment.start_time.strftime('%H:%M')
        end_time = managed_appointment.end_time.strftime('%H:%M')

        start_time_obj = datetime.strptime(start_time, "%H:%M").time()
        end_time_obj = datetime.strptime(end_time, "%H:%M").time()

        doctor_schedule = DoctorSchedule.objects.filter(user=doctor.user).first()
        if not doctor_schedule:
            managed_appointment.delete()
            return Response({"message": "Appointment deleted successfully, but no schedule found for the doctor."}, status=status.HTTP_200_OK)
      
        booked_appointments = BookedAppointment.objects.filter(
            doctor=doctor.user.id,
            appointment_type=appointment_type,
            status__in=["Pending", "Confirmed"],
        ).values_list("date", flat=True)

        weekdays_map = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
        
        today = date.today()
        protected_days = []
        
        for day in days_list:
            if day in weekdays_map:
                target_weekday = weekdays_map[day]
                days_ahead = (target_weekday - today.weekday()) % 7
                target_date = today + timedelta(days=days_ahead)

                if target_date in booked_appointments:
                    protected_days.append(target_date)

        if protected_days:
            return Response({"message": "Your appointment is booked for the same day, you can't delete." }, 
                               status=status.HTTP_400_BAD_REQUEST)

        schedule_data = doctor_schedule.schedule
        
        for day in days_list:
            if day in schedule_data and appointment_type in schedule_data[day]: 
                new_slots = []
                for slot in schedule_data[day][appointment_type]: 
                    slot_start_time_str = slot["slot"].split(" - ")[0] 
                    slot_start_time_obj = datetime.strptime(slot_start_time_str, "%H:%M").time()
                    
                    if not (start_time_obj <= slot_start_time_obj < end_time_obj):
                        new_slots.append(slot)

                schedule_data[day][appointment_type] = new_slots 

        doctor_schedule.schedule = schedule_data
        doctor_schedule.save()

        managed_appointment.delete()
        
        return Response({"message": f"{appointment_type} appointment and its slots deleted successfully"}, status=status.HTTP_200_OK)


# class AllDaySlotsAPIView(APIView):
#     """
#     API to get available slots for a doctor.
#     - If `date` is provided, returns slots for that date with booking status.
#     - If `date` is not provided, returns all available slots for all days.
#     """
#     permission_classes = [IsAuthenticated]

#     DAY_ID_MAP = {
#     "Monday": 1, "Mon": 1,
#     "Tuesday": 2, "Tue": 2,
#     "Wednesday": 3, "Wed": 3,
#     "Thursday": 4, "Thu": 4,
#     "Friday": 5, "Fri": 5,
#     "Saturday": 6, "Sat": 6,
#     "Sunday": 7, "Sun": 7
#     }

#     def get(self, request):
#         try:
#             doctor_id = request.query_params.get("doctor_id")
#             selected_date_str = request.query_params.get("date")
#             slot_type = request.query_params.get("slot_type")

#             if not doctor_id:
#                 return Response({"message": "Doctor ID is required", "data": {}}, status=400)

#             doctor = Doctor.objects.filter(user__id=doctor_id, user__role="Doctor").first()
#             if not doctor:
#                 return Response({"message": "Invalid doctor ID", "data": {}}, status=404)

#             if selected_date_str:
#                 # Fetch slots for a specific date
#                 try:
#                     selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
#                 except ValueError:
#                     return Response({"message": "Invalid date format. Use YYYY-MM-DD", "data": {}}, status=400)

#                 full_day_name = calendar.day_name[selected_date.weekday()]
#                 short_day_name = full_day_name[:3]  # "Sunday" → "Sun"

#                 slots = Slot.objects.filter(doctor=doctor, day=short_day_name, slot_type=slot_type )

#                 slot_data = [
#                     {"time_slot": slot.time_slot, "status": "Booked" if slot.is_booked else "Available"}
#                     for slot in slots
#                 ]

#                 response_data = {
#                     "doctor_id": doctor.user.id,
#                     "doctor_name": f"{doctor.user.first_name} {doctor.user.last_name}",
#                     "available_slots": [
#                         {
#                             "day_id": self.DAY_ID_MAP.get(full_day_name, 0),
#                             "day": full_day_name,
#                             "slots": slot_data
#                         }
#                     ],
#                 }

#                 return Response({"message": "Appointment preferences retrieved successfully.", "data": response_data}, status=200)

#             else:
#                 # Fetch all slots grouped by day
#                 available_slots = Slot.objects.filter(doctor=doctor)

#                 slots_by_day = defaultdict(list)
#                 for slot in available_slots:
#                     slots_by_day[slot.day].append({
#                         "time_slot": slot.time_slot,
#                         "status": "Booked" if slot.is_booked else "Available"
#                     })

#                 formatted_slots = [
#                     {
#                         "day_id": self.DAY_ID_MAP.get(day, 0),
#                         "day": day,
#                         "slots": slots
#                     }
#                     for day, slots in slots_by_day.items()
#                 ]

#                 response_data = {
#                     "doctor_id": doctor.user.id,
#                     "doctor_name": f"{doctor.user.first_name} {doctor.user.last_name}",
#                     "available_slots": formatted_slots,
#                 }

#                 return Response({"message": "Appointment preferences retrieved successfully.", "data": response_data}, status=200)

#         except Exception as e:
#             return Response({"message": f"An error occurred: {str(e)}"}, status=500)


# with buffered time and one month slots time 
# class AvailableSlotsAPIView(APIView):
#     """
#     API to get available slots for a selected doctor, filtered by 'Planned' or 'Urgent' using query parameters.
#     """
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         doctor_id = request.query_params.get("doctor_id")
#         slot_type = request.query_params.get("slot_type", "").strip()  # Get slot type from query params

#         # Validate required parameters
#         if not doctor_id:
#             return Response({"message": "Doctor ID is required", "data": {}}, status=400)

#         # Validate doctor existence
#         doctor = Doctor.objects.filter(user__id=doctor_id, user__role="Doctor").first()
#         if not doctor:
#             return Response({"message": "Invalid doctor ID", "data": {}}, status=404)

#         # Ensure slot_type is either "Planned" or "Urgent"
#         if slot_type and slot_type.lower() not in ["planned", "urgent"]:
#             return Response({"message": "Invalid slot type. Use 'Planned' or 'Urgent'.", "data": {}}, status=400)

#         # Apply filter if slot_type is provided
#         slot_filter = {"doctor": doctor}
#         if slot_type:
#             slot_filter["slot_type__iexact"] = slot_type  # Case-insensitive filtering

#         # Fetch available slots
#         slots = Slot.objects.filter(**slot_filter).only("time_slot")

#         # Prepare response data
#         response_data = {
#             "doctor_id": doctor.user.id,
#             "doctor_name": f"{doctor.user.first_name} {doctor.user.last_name}",
#             "specialty": getattr(doctor, "specialty", ""),
#             "slot_type": slot_type or "All",  # Default to "All" if not provided
#             "available_slots": [slot.time_slot for slot in slots],
#         }

#         return Response(
#             {
#                 "message": f"Available slots for type '{slot_type or 'All'}'",
#                 "data": response_data,
#             },
#             status=200,
#         )

class GetSlotsAPIView(APIView):
    def get(self, request):
        try:
            user_id = request.query_params.get('doctor_user_id')
            if not user_id:
                return Response({'message':'Doctor id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            user = User.objects.filter(pk=user_id).first()
            if not user:
                return Response({'message': 'Doctor not found'})
            
            slots = DoctorSchedule.objects.filter(user=user)
            if not slots.exists():
                return Response({'message': 'slot does not exist', 'data': []}, status=status.HTTP_200_OK)
            
            serialized_slots = DoctorScheduleSerializer(slots, many=True).data

            return Response({'data': serialized_slots}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class BookAppointmentAPIView(APIView):
    """
    Allows patients to book an available appointment slot only if the doctor has availability.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            doctor_user_id = request.data.get("doctor_user_id")
            patient_user_id = request.data.get("patient_user_id")
            slot = request.data.get("slot")  # format: "10:00 - 10:30"
            appointment_type = request.data.get("appointment_type")
            date = request.data.get("date")  # (DD-MM-YYYY)

            # Convert date to correct format
            date_obj = datetime.strptime(date, "%d-%m-%Y").date()
            appointment_day = date_obj.strftime("%a")
            
    
            slot_start_str = slot.split("-")[0].strip()
            slot_start_time = datetime.strptime(slot_start_str, "%H:%M").time()
            
    
            appointment_datetime = datetime.combine(date_obj, slot_start_time)
            appointment_datetime = timezone.make_aware(appointment_datetime)
            now = timezone.now()
            within_24_hours = appointment_datetime - now <= timedelta(hours=24)

            doctor = User.objects.filter(pk=doctor_user_id).first()
            if not doctor:
                return Response({"error": "Invalid doctor ID"}, status=404)
            
            patient = User.objects.filter(pk=patient_user_id).first()
            if not patient:
                return Response({'error':'Invalid patient ID'}, status=404)
             # doctor_user_obj = User.objects.get(id=doctor.user_id)
            # Ensure doctor has set availability for this day
            # availability = AppointmentManagement.objects.filter(
            #     user=doctor_user_obj,
            #     appointment_type=appointment_type,
            #     days__icontains=appointment_day
            # ).first()
            # Convert slot start and end time
            # slot_start, slot_end = slot.split(" - ")
            # slot_start = datetime.strptime(slot_start, "%H:%M").time()
            # slot_end = datetime.strptime(slot_end, "%H:%M").time()

            # # Ensure slot falls within the doctor's available hours
            # if not (availability.start_time <= slot_start and availability.end_time >= slot_end):
            #     return Response({"error": "Selected slot is outside doctor's available hours"}, status=400)

            # Ensure slot is not already booked
            is_booked = BookedAppointment.objects.filter(
                doctor=doctor_user_id, slot=slot, date=date_obj, status__in = ['Pending', 'Confirmed']
            ).exists()

            if is_booked:
                return Response({"error": "Selected slot is already booked"}, status=400)

            appointment = BookedAppointment.objects.create(
                doctor=doctor_user_id,
                patient=patient_user_id,
                appointment_type=appointment_type,
                slot=slot,
                status="Pending",
                date=date_obj,
                payment_status="Pending", 
            )
            
            # WhatsApp Notification Message
            message = (
                f"Hello {patient.first_name},\n"
                f"Your appointment has been successfully booked.\n"
                f"Date: {date}\n"
                f"Time: {slot}\n"
                f"Doctor: {doctor.first_name} {doctor.last_name}\n"
                f"Location: Online/Clinic\n"
                f"Thank you for choosing our service!"
            )
            
            
            doctor = User.objects.get(id=appointment.doctor)  # get doctor as a User object
            doctor_name = f"{doctor.first_name} {doctor.last_name}"  # access first_name
            # print(doctor_name, "----------DOCTOR NAME----------")

            patient = User.objects.get(id=appointment.patient)  # get patient as a User object
            patient_name = f"{patient.first_name} {patient.last_name}"
            # print(patient_name, "----------PATIENT NAME----------")
            
            # Send WhatsApp Notification to patient
            send_whatsapp_message_patient(
                to=patient.phone_number,
                patient_name=patient_name,
                date=appointment.date.strftime("%Y-%m-%d"),
                slot=slot,
                doctor_name=doctor_name,
                appointment_type=appointment.appointment_type
            )
            
            # Send WhatsApp Notification to doctor
            send_whatsapp_message_doctor(
                to=doctor.phone_number,
                patient_name=patient_name,
                date=appointment.date.strftime("%Y-%m-%d"),
                slot=slot,
                doctor_name=doctor_name,
                appointment_type=appointment.appointment_type
            )
            
             # Send **In-App Notifications**
            send_notification(
                user_id=doctor.id,
                message=f"You have a new appointment with {patient_name} on {date} at {slot}."
            )

            send_notification(
                user_id=patient.id,
                message=f"Your appointment with Dr. {doctor_name} is scheduled on {date} at {slot}."
            )
            # Update appointment status to "Pending"
            appointment.status = "Pending"
            appointment.save()
            
            message_text = "Appointment booked successfully"
            if within_24_hours:
                message_text += (
                    " (Note: You are booking the appointment within 24 hours. "
                    "If you cancel, 10% amount will be deducted.)"
                )
            
            return Response({
                "message_text": message_text,
                "data": {
                    "appointment_id": appointment.id,
                    "appointment_type": appointment.appointment_type,
                    "date": date,
                    "payment_status": appointment.payment_status,
                }
            }, status=201)

        except Exception as e:
            return Response({"error": str(e)}, status=400)

        
    def book_patient_appointment(self, doctor_id, patient_id, date, time_slot, appointment_type):
        try:
            doctor_instance = Doctor.objects.get(id=doctor_id)
            patient_instance = Patient.objects.get(id=patient_id)

            # Validate appointment type
            if appointment_type not in ["Planned", "Urgent"]:
                return {"success": False, "message": "Invalid appointment type. Choose 'Planned' or 'Urgent'."}

            # Get or create the doctor's appointment record
            doctor_schedule, created = PatientBookAppointment.objects.get_or_create(
                doctor=doctor_instance,
                defaults={"schedule": {}}
            )

            # Load existing schedule
            existing_schedule = doctor_schedule.schedule or {}

            # Ensure the date exists in the schedule
            if date not in existing_schedule:
                existing_schedule[date] = {}

            # Ensure the appointment type category exists
            if appointment_type not in existing_schedule[date]:
                existing_schedule[date][appointment_type] = {"appointments": []}

            # Check if the slot is already booked
            for appointment in existing_schedule[date][appointment_type]["appointments"]:
                if appointment["slot"] == time_slot:
                    return {"success": False, "message": "This time slot is already booked."}

            # Add the appointment under the correct type (Planned/Urgent)
            existing_schedule[date][appointment_type]["appointments"].append({
                "patient_id": patient_instance.id,
                "slot": time_slot
            })

            # Save the updated schedule
            doctor_schedule.schedule = existing_schedule
            doctor_schedule.save()  

            return {"success": True, "message": "Appointment booked successfully.", 'appointment': doctor_schedule.appointment}

        except Doctor.DoesNotExist:
            return {"success": False, "message": "Doctor not found."}
        except Patient.DoesNotExist:
            return {"success": False, "message": "Patient not found."}
        except Exception as e:
            return {"success": False, "message": str(e)}
        
    def get(self, request):
        try:
            doctor_user_id = request.query_params.get('doctor_user_id')
            date = request.query_params.get('date')
            if not doctor_user_id or not date:
                return Response({'message':'Doctor id and Date is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            date_obj = datetime.strptime(date, "%d-%m-%Y").date()
            doctor = User.objects.filter(pk=doctor_user_id).first()
        
            if not doctor:
                return Response({'message':'doctor not found'}, status=status.HTTP_404_NOT_FOUND)
            
            appiontments = BookedAppointment.objects.filter(doctor=doctor_user_id, date=date_obj)
            
            if not appiontments.exists():
                return Response({'message':'No appintment found', 'data':[]}, status=status.HTTP_200_OK)
            
            bookedAppiontment = []
            for appintment in appiontments:
                bookedAppiontment.append(
                    {
                        'slot': appintment.slot,
                        'status': appintment.status
                    }
                )
            return Response({'message':'Retrieved successfully','data':bookedAppiontment}, status=status.HTTP_200_OK)
                
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    def put(self, request):
        try:
            if request.user.role not in ['Doctor', 'Patient']:
                return Response({'message': 'Only Doctor or Patient can update the appointment'}, status=status.HTTP_403_FORBIDDEN)

            appointment_id = request.data.get('appointment_id')
            appointment_status = request.data.get('status')

            if not appointment_id or not appointment_status:
                return Response({'message': 'Appointment ID and status are required'}, status=status.HTTP_400_BAD_REQUEST)

            appointment_status = appointment_status.capitalize()
            if appointment_status not in ['Confirmed', 'Cancelled']:
                return Response({'message': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                appointment = BookedAppointment.objects.get(pk=appointment_id)
            except BookedAppointment.DoesNotExist:
                return Response({"message": "Appointment not found"}, status=status.HTTP_404_NOT_FOUND)

            if request.user.id != appointment.doctor and request.user.id != appointment.patient:
                return Response({'message': 'Only associated doctor or patient can update this appointment'},
                                status=status.HTTP_403_FORBIDDEN)

            appointment.status = appointment_status
            appointment.save()

            serializer = BookedAppointmentSerializer(appointment)
            return Response({'message': 'Appointment updated successfully', 'data': serializer.data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        
        
class PatientAppointmentAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            patient_user_id = request.query_params.get('patient_user_id')
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            if not patient_user_id:
                return Response({'message':'Patient id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            if int(patient_user_id) != request.user.id:
                return Response({'message':'You are not authorized to access this resource'}, status=status.HTTP_403_FORBIDDEN)
            
            if not start_date or not end_date:
                return Response({'message':'Start and end date is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            patient = User.objects.filter(pk=patient_user_id).first()
            if not patient:
                return Response({'message':'Patient not found'}, status=status.HTTP_404_NOT_FOUND)
            
            start__date = datetime.strptime(start_date, "%d-%m-%Y").date()
            end__date = datetime.strptime(end_date, "%d-%m-%Y").date()
            
            appiontmtents = BookedAppointment.objects.filter(date__gte=start__date, date__lte=end__date, patient=patient_user_id)
            if not appiontmtents.exists():
                return Response({'message':'No appintment found', 'data':[]}, status=status.HTTP_200_OK)
            
            serializer = BookedAppointmentSerializer(appiontmtents, many=True)
            return Response({'message':'Retrieved successfully','data':serializer.data}, status=status.HTTP_200_OK)
                
        except Exception as e:
            return Response({'error':str(e)},status=status.HTTP_400_BAD_REQUEST)

class DoctorAppointmentAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            doctor_user_id = request.query_params.get('doctor_user_id')
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            
            if not doctor_user_id:
                return Response({'message':'Doctor id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not start_date or not end_date:
                return Response({'message':'Start and end date is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            if int(doctor_user_id) != request.user.id:
                return Response({'message':'You are not authorized to access this data'}, status=status.HTTP_403_FORBIDDEN)         
            
            doctor = User.objects.filter(pk=doctor_user_id).first()
            if not doctor:
                return Response({'message':'Doctor not found'}, status=status.HTTP_404_NOT_FOUND)
            
            start__date = datetime.strptime(start_date, "%d-%m-%Y").date()
            end__date = datetime.strptime(end_date, "%d-%m-%Y").date()
            
            appiontmtents = BookedAppointment.objects.filter(date__gte=start__date, date__lte=end__date, doctor=doctor_user_id)
            if not appiontmtents.exists():
                return Response({'message':'No appintment found', 'data':[]}, status=status.HTTP_200_OK)
            
            serializer = BookedAppointmentSerializer(appiontmtents, many=True)
            return Response({'message':'Retrieved successfully','data':serializer.data}, status=status.HTTP_200_OK)
                
        except Exception as e:
            return Response({'error':str(e)},status=status.HTTP_400_BAD_REQUEST)

class CompletedAppointmentListView(APIView):
    permission_classes = [IsAuthenticated]    
    def get(self, request):
        try:
            user = request.user
            
            if not hasattr(user, "doctor"):
                return Response({"message": "only doctor can perform this action"}, status=status.HTTP_403_FORBIDDEN)
            
            appointments = BookedAppointment.objects.filter(doctor=user.id, status="Completed")
            
            data = {
            "message": "Appointment list retrieved successfully",
            "data": [
                {
                    "appointment_id": appointment.id,
                    "appointment_type": appointment.appointment_type,
                    "date": appointment.date,
                    "status": appointment.status,
                    "slot": appointment.slot,
                    "patient": {
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "email": user.email,
                        "profile_picture": user.profile_picture.url if user.profile_picture else None,
                    }
                }
                for appointment in appointments
            ]}
            
            return Response(data, status=200)
                
        except Exception as e:
            return Response({"message": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
            



# class MyAppointmentsAPIView(APIView):
#     """
#     Allows patients to view their booked appointments.
#     """
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         try:
#             user = request.user
#             if user.role != "Patient":
#                 return Response({"error": "Only patients can view their appointments"}, status=403)

#             appointments = BookedAppointment.objects.filter(patient=user).order_by("slot")
#             data = [{
#                 "appointment_id": appt.id,
#                 "doctor_name": f"{appt.doctor.first_name} {appt.doctor.last_name}",
#                 "appointment_type": appt.appointment_type,
#                 "slot": appt.slot,
#                 "status": appt.status
#             } for appt in appointments]

#             return Response({"message": "Appointments retrieved successfully", "appointments": data})

#         except Exception as e:
#             return Response({"error": str(e)}, status=400)


# Reschedule Appointment API
class RescheduleAppointmentAPIView(APIView):
    """
    Allows patient and doctor to reschedule their appointment.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        try:
            appointment_id = request.data.get("appointment_id")
            new_slot = request.data.get("new_slot")
            new_date = request.data.get("date")  # Ensure date format matches

            if not appointment_id or not new_slot or not new_date:
                return Response({"error": "Missing required fields."}, status=400)

            date_obj = datetime.strptime(new_date, "%d-%m-%Y").date()

            appointment = BookedAppointment.objects.filter(
                Q(patient=request.user.id) | Q(doctor=request.user.id), id=appointment_id 
            ).first()

            if not appointment:
                return Response({"error": "Appointment not found."}, status=404)

            if appointment.status in ["Cancelled", "Completed"]:
                return Response({"error": f"Cannot reschedule a {appointment.status.lower()} appointment."}, status=400)

            is_booked = BookedAppointment.objects.filter(
                doctor=appointment.doctor, slot=new_slot, date=date_obj
            ).exists()

            if is_booked:
                return Response({"error": "Selected slot is already booked"}, status=400)

            patient = User.objects.get(id=appointment.patient)
            patient_name = patient.get_full_name()
            doctor = User.objects.get(id=appointment.doctor)
            doctor_name = doctor.get_full_name()
            old_slot = appointment.slot
            old_date = appointment.date.strftime("%d-%m-%Y")

            appointment.slot = new_slot
            appointment.date = date_obj
            appointment.status = "Rescheduled"
            appointment.rescheduled_by = request.user
            appointment.save()

            # Send WhatsApp Notifications
            appointment_reschedule_notification_patient(
                to=request.user.phone_number,
                old_date=old_date,
                old_slot=old_slot,
                new_date=new_date,
                new_slot=new_slot,
                doctor_name=doctor_name,
                patient_name=patient_name
            )

            appointment_reschedule_notification_doctor(
                to=doctor.phone_number,
                old_date=old_date,
                old_slot=old_slot,
                new_date=new_date,
                new_slot=new_slot,
                doctor_name=doctor_name,
                patient_name=patient_name
            )

            return Response({
                "message": "Appointment rescheduled successfully",
                "data": {
                    "appointment_id": appointment.id,
                    "patient": patient_name,
                    "doctor": doctor_name,
                    "old_date": old_date,
                    "new_date": new_date,
                    "old_slot": old_slot,
                    "new_slot": new_slot,
                    "status": "Rescheduled",
                    "rescheduled_by": request.user.role
                }
            }, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Cancel Appointment API
class CancelAppointmentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        appointment_id = request.data.get("appointment_id")

        if not appointment_id:
            return Response({"error": "Appointment ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Retrieve the appointment
            appointment = BookedAppointment.objects.filter(id=appointment_id).first()
            if not appointment:
                return Response({"error": "Appointment not found."}, status=status.HTTP_404_NOT_FOUND)

            # Ensure the appointment is pending before canceling
            if appointment.status != "Pending":
                return Response({"error": "Only pending appointments can be cancelled."}, status=status.HTTP_400_BAD_REQUEST)

            # Extract patient and doctor details
            patient = appointment.patient
            doctor = appointment.doctor

            doctor = User.objects.get(id=appointment.doctor)  # Fetch doctor as a User object
            doctor_name = f"{doctor.first_name} {doctor.last_name}"  # Now you can access first_name
            # print(doctor_name, "----------DOCTOR NAME----------")

            patient = User.objects.get(id=appointment.patient)  # Fetch patient as a User object
            patient_name = f"{patient.first_name} {patient.last_name}"
            # print(patient_name, "----------PATIENT NAME----------")
            # Format date and slot
            appointment_date = appointment.date.strftime("%Y-%m-%d")
            slot = appointment.slot

            # Cancel the appointment
            appointment.status = "Cancelled"
            appointment.save()

            # Send WhatsApp Notification to Patient
            appointment_cancel_notification_patient(
                to=patient.phone_number,
                date=appointment_date,
                slot=slot,
                patient_name=patient_name,
                doctor_name=doctor_name
            )

            # Send WhatsApp Notification to Doctor
            appointment_cancel_notification_doctor(
                to=doctor.phone_number,
                date=appointment_date,
                slot=slot,
                patient_name=patient_name,
                doctor_name=doctor_name
            )

            return Response({
                "message": "Appointment cancelled successfully.",
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Appointment Reminder API
class AppointmentReminderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        Fetch upcoming appointment reminders for the authenticated patient.
        """
        today = datetime.now()
        reminder_time = today + timedelta(days=1)

        reminders = BookedAppointment.objects.filter(patient=request.user, created_at__lte=reminder_time).exclude(status="Cancelled")
        serializer = BookedAppointmentSerializer(reminders, many=True)

        return Response({"reminders": serializer.data}, status=status.HTTP_200_OK)


class AppointmentSummaryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, appointment_id):
        """Retrieve appointment summary"""
        try:
            # Get the booked appointment
            appointment = get_object_or_404(BookedAppointment, id=appointment_id, patient=request.user.id)
            # Get the doctor's specialty (category)
            doctor = get_object_or_404(Doctor, user=appointment.doctor)
            # Get consultation fee from ConsultationSettings
            consultation_settings = ConsultationSessionAndFee.objects.filter(doctor=doctor).first()
            subtotal = consultation_settings.planned_fees or consultation_settings.urgent_fees
            # Build response
            response_data = {
                "category": doctor.specialty,  # General medicine (example)
                "date": appointment.date.strftime("%d %b, %Y"),  # Format date
                "time": appointment.slot,  # Slot time (e.g., "11:00AM")
                "subtotal": f"${subtotal:.2f}" if subtotal else "$0.00",
                "discount": "$0.00",
                "total": f"${subtotal:.2f}" if subtotal else "$0.00",
            }

            return Response(response_data, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=400)


# Payment Confirmation API
class PaymentConfirmationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Allows a patient to confirm their payment status.
        """
        appointment_id = request.data.get("appointment_id")
        payment_status = request.data.get("payment_status")

        try:
            appointment = BookedAppointment.objects.get(id=appointment_id, patient=request.user)

            if payment_status not in ["Pending", "Completed"]:
                return Response({"error": "Invalid payment status"}, status=status.HTTP_400_BAD_REQUEST)

            appointment.payment_status = payment_status
            appointment.save()

            return Response({"message": "Payment status updated successfully"}, status=status.HTTP_200_OK)
        except BookedAppointment.DoesNotExist:
            return Response({"error": "Appointment not found"}, status=status.HTTP_404_NOT_FOUND)


class CreateStripeCheckoutSession(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """
        Creates a Stripe Checkout Session for the appointment payment.
        """
        try:
            appointment_id = request.data.get("appointment_id")
            patient_user_id = request.data.get("patient_user_id")
            doctor_user_id = request.data.get("doctor_user_id")

            # Get the appointment object
            appointment = get_object_or_404(BookedAppointment, id=appointment_id, patient=patient_user_id)

            if appointment.payment_status == "Completed":
                return Response({"error": "Appointment is already paid"}, status=status.HTTP_400_BAD_REQUEST)

            # Ensure doctor is a valid instance of Doctor
            # if isinstance(appointment.doctor, Doctor):
            #     doctor = appointment.doctor
            # else:
            #     doctor = Doctor.objects.filter(user__email=appointment.doctor).first()
            #     if not doctor:
            #         return Response({"error": "Doctor not found"}, status=status.HTTP_400_BAD_REQUEST)
            # user = User.objects.filter(pk=doctor_user_id)
            
            # doctor = Doctor.objects.filter(user=user).first()
            
            doctor = Doctor.objects.filter(user_id=doctor_user_id).first()

            if not doctor:
                return Response({"error": "Doctor not found"}, status=status.HTTP_400_BAD_REQUEST)

            # Fetch the doctor's consultation settings
            consultation_settings = ConsultationSessionAndFee.objects.filter(doctor=doctor).first()
            if not consultation_settings:
                return Response({"error": "Consultation settings not found for the doctor"}, status=status.HTTP_400_BAD_REQUEST)

            # Determine fee based on appointment type
            if appointment.appointment_type == "urgent":
                amount = int(consultation_settings.urgent_fees * 100) if consultation_settings.urgent_fees else 0
            else:
                amount = int(consultation_settings.planned_fees * 100) if consultation_settings.planned_fees else 0

            try:
                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=["card"],
                    line_items=[{
                        "price_data": {
                            "currency": "usd",
                            "product_data": {
                                "name": f"Appointment with Dr. {doctor.user.first_name} {doctor.user.last_name}"
                            },
                            "unit_amount": amount
                        },
                        "quantity": 1
                    }],
                    mode="payment",
                    success_url=f"https://h2.doctor/Patient/allDoctorlist?session_id={{CHECKOUT_SESSION_ID}}&status=success",
                    cancel_url="https://h2.doctor/Patient/allDoctorlist?status=cancel",
                    metadata={"appointment_id": appointment.id}
                )

                # Save session ID
                appointment.stripe_session_id = checkout_session.id
                appointment.amount = amount/100
                appointment.save()

                return Response({"session_url": checkout_session.url}, status=status.HTTP_200_OK)

            except stripe.error.StripeError as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as ex:
            return Response({
                "error": str(ex)
            }, status=status.HTTP_400_BAD_REQUEST)


class UpdatePaymentStatus(APIView):
    """
    Updates the payment status after a user returns from Stripe payment.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """
        Handles the payment success or cancellation.
        """
        session_id = request.GET.get("session_id")
        status_param = request.GET.get("status")

        if not session_id:
            return Response({"error": "Session ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch appointment based on Stripe session ID
        appointment = get_object_or_404(BookedAppointment, stripe_session_id=session_id)

        if status_param == "success":
            appointment.payment_status = "Completed"
        elif status_param == "cancelled":
            appointment.payment_status = "Cancelled"
        else:
            appointment.payment_status = "Failed"

        appointment.save()

        return Response({"message": f"Payment {status_param}!", "status": appointment.payment_status}, status=status.HTTP_200_OK)

class PaymentSuccessView(APIView):
    def get(self, request):
        session_id = request.GET.get("session_id")

        if not session_id:
            return Response("Session ID is missing", status=400)

        try:
            session = stripe.checkout.Session.retrieve(session_id)

            # Get appointment ID from metadata
            appointment_id = session.metadata.get("appointment_id")

            if not appointment_id:
                return Response("No appointment linked to this payment", status=400)

            # Update payment status
            appointment = BookedAppointment.objects.get(id=appointment_id)
            appointment.payment_status = "Completed"
            appointment.save()

            return Response("Payment was successful!", status=200)

        except stripe.error.StripeError as e:
            return Response(str(e), status=500)

        except Exception as e:
            return Response(str(e), status=500)


class GenerateReferralCodeView(APIView):
    """Generate and return a user's referral code, registration link, and update referral points."""

    def generate_referral_code(self):
        """Generate a unique referral code (7 characters)."""
        return get_random_string(length=7).upper()

    def get(self, request):
        try:
            logger.info(
                "User %s is retrieving or generating referral code.", request.user.email
            )

            # Get or create referral object for the current user
            referral, created = Referral.objects.get_or_create(user=request.user)

            if created:
                referral.personal_code = self.generate_referral_code()
                referral.save()
                logger.info(
                    "Generated new referral code for user: %s", request.user.email
                )

            # Return referral data
            serializer = ReferralSerializer(referral, context={'request': request})
            return Response(
                {
                    "message": "Referral data retrieved successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except Referral.DoesNotExist:
            logger.warning("Referral code not found for user: %s", request.user.email)
            return Response(
                {"error": "Referral code not found."}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(
                "Error retrieving referral code for user %s: %s",
                request.user.email,
                str(e),
            )
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InviteUserView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        referral_code = request.data.get("referral_code")

        if not referral_code:
            return Response(
                {"error": "Referral code is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            referral = Referral.objects.get(personal_code=referral_code)

            if referral.user == request.user:
                return Response(
                    {"error": "You cannot use your own referral code."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if Invitation.objects.filter(invited_user=request.user).exists():
                return Response(
                    {"error": "You have already used a referral code."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            with transaction.atomic():
                generated_code = str(uuid.uuid4())[:8]

                invitation = Invitation.objects.create(
                    invited_by=referral,
                    invited_user=request.user,
                    invitation_code=generated_code,
                    first_appointment=False
                                                    )
                referral.invited_users_count = Invitation.objects.filter(
                    invited_by=referral
                ).count()
                referral.referral_points += 5
                referral.save()

                logger.info(
                    "Referral code %s successfully used by user %s",
                    referral_code,
                    request.user.email
                )

            return Response(
                {"message": "Referral code applied successfully."},
                status=status.HTTP_200_OK
            )

        except Referral.DoesNotExist:
            return Response(
                {"error": "Invalid referral code."},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.exception(
                "Unexpected error applying referral code for user %s: %s",
                request.user.email,
                str(e)
            )
            return Response(
                {"error": "Something went wrong while applying referral code."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
@api_view(["POST"])
def redeem_invitation(request, invitation_code):
    """Redeem the invitation and increase the inviters stats."""
    try:
        logger.info(
            "User %s attempting to redeem invitation code: %s",
            request.user.email,
            invitation_code,
        )
        invitation = Invitation.objects.get(invitation_code=invitation_code)

        if invitation.redeemed:
            logger.warning(
                "User %s attempted to redeem already used invitation code: %s",
                request.user.email,
                invitation_code,
            )
            return Response(
                {"error": "This invitation has already been redeemed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            invitation.redeem()  # Redeem the invitation
            logger.info(
                "Invitation code %s redeemed successfully by user %s",
                invitation_code,
                request.user.email,
            )

        return Response(
            {"message": "Invitation redeemed successfully!"}, status=status.HTTP_200_OK
        )
    except Invitation.DoesNotExist:
        logger.error(
            "Invalid invitation code attempt: %s by user %s",
            invitation_code,
            request.user.email,
        )
        return Response(
            {"error": "Invalid invitation code."}, status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.exception(
            "Error redeeming invitation code %s for user %s: %s",
            invitation_code,
            request.user.email,
            str(e),
        )
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


def get_time_in_timezone(timezone):
    """Get the current time in the specified timezone."""
    try:
        tz = pytz.timezone(timezone)
        return datetime.now(tz).isoformat()
    except Exception as e:
        logger.error(f"Invalid timezone format: {timezone} - {str(e)}")
        return None


class ConsultationSettingsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            user = request.user
            if not hasattr(user, "doctor"):
                return Response(
                    {"error": "You are not a registered doctor."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            consultation_settings = ConsultationSessionAndFee.objects.filter(doctor=user.doctor)
            serializer = ConsultationSettingsSerializer(consultation_settings, many=True)
            return Response(
                {
                    "message": "Consultation settings retrieved successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def post(self, request, *args, **kwargs):
        user = request.user
        try:
            doctor = Doctor.objects.get(user=user)
        except Doctor.DoesNotExist:
            return Response(
                {"error": "You are not a registered doctor."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            with transaction.atomic():
                # Check if a similar setting already exists
                existing_setting = ConsultationSessionAndFee.objects.filter(
                    doctor=doctor
                ).first()

                if existing_setting:
                    # Update the existing setting
                    serializer = ConsultationSettingsSerializer(
                        existing_setting, data=request.data, partial=True
                    )
                    message = "Consultation settings updated successfully"
                else:
                    # Create a new setting for the doctor
                    request.data["doctor"] = doctor.id
                    serializer = ConsultationSettingsSerializer(data=request.data)
                    message = "Consultation settings created successfully"

                if serializer.is_valid():
                    consultation = serializer.save()

                    # Manually update Doctor model with hourly rates
                    if consultation:
                        planned_hourly = (
                            (consultation.planned_fees / consultation.planned_session_length) * 60
                            if consultation.planned_fees and consultation.planned_session_length
                            else 0
                        )
                        urgent_hourly = (
                            (consultation.urgent_fees / consultation.urgent_session_length) * 60
                            if consultation.urgent_fees and consultation.urgent_session_length
                            else 0
                        )

                        doctor.planned_hourly_rate = round(planned_hourly, 2)
                        doctor.urgent_hourly_rate = round(urgent_hourly, 2)
                        doctor.save()

                    return Response(
                        {"message": message, "data": serializer.data},
                        status=status.HTTP_200_OK if existing_setting else status.HTTP_201_CREATED,
                    )

                return Response(
                    {"error": "Invalid data", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            logger.error(f"Error in ConsultationSettingsAPIView: {str(e)}")
            return Response(
                {"error": "Something went wrong", "details": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class UserPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            preference, _ = UserPreference.objects.get_or_create(user=request.user)
            user_languages = (
                preference.language.split(",") if preference.language else ["en"]
            )
            user_timezone = "UTC" if preference.use_system_timezone else preference.timezone
            current_time = get_time_in_timezone(user_timezone) or "Invalid timezone"
            return Response(
                {
                    "message": "Data fetched successfully.",
                    "user_preference": {
                        "timezone": user_timezone,
                        "languages": user_languages,
                        "use_system_timezone": preference.use_system_timezone,
                        "use_system_language": preference.use_system_language,
                        "current_time": current_time,
                    },
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def post(self, request):
        try:
            preference, _ = UserPreference.objects.get_or_create(user=request.user)
            timezone = request.data.get("timezone")
            languages = request.data.get("languages")
            use_system_timezone = request.data.get("use_system_timezone")
            use_system_language = request.data.get("use_system_language")

            # Validate timezone
            if timezone and timezone not in pytz.all_timezones:
                return Response(
                    {"error": "Invalid timezone provided."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if languages and not isinstance(languages, list):
                return Response(
                    {"error": "Languages must be a list."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with transaction.atomic():
                if timezone is not None:
                    preference.timezone = timezone
                if languages is not None:
                    preference.language = ",".join(languages)
                if use_system_timezone is not None:
                    preference.use_system_timezone = use_system_timezone
                if use_system_language is not None:
                    preference.use_system_language = use_system_language

                preference.save()

            return Response(
                {
                    "message": "Data updated successfully.",
                    "user_preference": {
                        "timezone": preference.timezone,
                        "languages": (
                            languages if languages else preference.language.split(",")
                        ),
                        "use_system_timezone": preference.use_system_timezone,
                        "use_system_language": preference.use_system_language,
                    },
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ReschedulePolicyView(APIView):
    """API to create or update a Reschedule Policy for each day."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Update an existing data or create a new one."""
        try:
            data = request.data
            user = request.user
            reschedule_day = data.get("reschedule_days")
            valid_days = [choice[0] for choice in ReschedulePolicy.DAYS_CHOICES]

            if reschedule_day not in valid_days:
                logger.warning(
                    f"Invalid day format attempted by {user}. Input: {reschedule_day}"
                )
                return Response(
                    {"error": "Invalid day format. Use 'Mon', 'Tue', etc."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            existing_policy = ReschedulePolicy.objects.filter(
                user=user, reschedule_days=reschedule_day
            ).first()

            if existing_policy:
                logger.info(
                    f"Updating existing reschedule policy for {reschedule_day} by user {user}"
                )
                existing_policy.allow_reschedule = data.get(
                    "allow_reschedule", existing_policy.allow_reschedule
                )
                existing_policy.max_reschedules = data.get(
                    "max_reschedules", existing_policy.max_reschedules
                )
                existing_policy.reschedule_time_range = data.get(
                    "reschedule_time_range", existing_policy.reschedule_time_range
                )
                existing_policy.save()
                return Response(
                    {
                        "message": f"Reschedule policy for {reschedule_day} updated successfully.",
                        "data": ReschedulePolicySerializer(existing_policy).data,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                logger.info(
                    f"Creating new reschedule policy for {reschedule_day} by user {user}"
                )
                policy = ReschedulePolicy.objects.create(
                    user=user,
                    allow_reschedule=data.get("allow_reschedule", True),
                    max_reschedules=data.get("max_reschedules"),
                    reschedule_days=reschedule_day,
                    reschedule_time_range=data.get("reschedule_time_range"),
                )
                return Response(
                    {
                        "message": f"Reschedule policy for {reschedule_day} created successfully.",
                        "data": ReschedulePolicySerializer(policy).data,
                    },
                    status=status.HTTP_201_CREATED,
                )
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
    def get(self, request):
        """Fetch all reschedule policies for the logged-in user."""
        try:
            user = request.user
            logger.info(f"Fetching reschedule policies for user {user}")
            policies = ReschedulePolicy.objects.filter(user=user)
            serializer = ReschedulePolicySerializer(policies, many=True)
            return Response(
                {
                    "message": "Reschedule policies fetched successfully.",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class CancellationPolicyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            policy = CancellationPolicy.objects.get(doctor=request.user)
            logger.info(f"Fetching cancellation policy for user {request.user}")
        except CancellationPolicy.DoesNotExist:
            logger.warning(f"Cancellation policy not found for user {request.user}")
            raise NotFound("Cancellation policy not found.")

        serializer = CancellationPolicySerializer(policy)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        try:
            existing_policy = CancellationPolicy.objects.filter(doctor=request.user).first()
            if existing_policy:
                logger.info(
                    f"Updating existing cancellation policy for user {request.user}"
                )
                serializer = CancellationPolicySerializer(
                    existing_policy,
                    data=request.data,
                    context={"request": request},
                    partial=True,
                )
                if serializer.is_valid():
                    serializer.save()
                    return Response(
                        {
                            "message": "Cancellation policy updated successfully.",
                            "data": serializer.data,
                        },
                        status=status.HTTP_200_OK,
                    )
                logger.error(
                    f"Invalid data for updating cancellation policy by user {request.user}: {serializer.errors}"
                )
                return Response(
                    {"detail": "Invalid data.", "errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            logger.info(f"Creating new cancellation policy for user {request.user}")
            serializer = CancellationPolicySerializer(
                data=request.data, context={"request": request}
            )
            if serializer.is_valid():
                serializer.save(doctor=request.user)
                return Response(
                    {
                        "message": "Cancellation policy created successfully.",
                        "data": serializer.data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            logger.error(
                f"Invalid data for creating cancellation policy by user {request.user}: {serializer.errors}"
            )
            return Response(
                {"detail": "Invalid data.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class NoShowPolicyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                logger.warning("Unauthorized access attempt to NoShowPolicy GET endpoint")
                return Response(
                    {"detail": "Authentication credentials were not provided."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            logger.info(f"Fetching NoShowPolicy for user {request.user}")
            policies = NoShowPolicy.objects.filter(user=request.user)
            serializer = NoShowPolicySerializer(policies, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def post(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                logger.warning("Unauthorized access attempt to NoShowPolicy POST endpoint")
                return Response(
                    {"detail": "Authentication credentials were not provided."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            if NoShowPolicy.objects.filter(user=request.user).exists():
                logger.warning(
                    f"User {request.user} attempted to create a duplicate NoShowPolicy"
                )
                return Response(
                    {"detail": "You already have an existing NoShowPolicy."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            data = request.data.copy()
            data["user"] = request.user.id
            serializer = NoShowPolicySerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                logger.info(f"NoShowPolicy created successfully for user {request.user}")
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            logger.error(
                f"Invalid data for NoShowPolicy creation by user {request.user}: {serializer.errors}"
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


    def put(self, request, *args, **kwargs):
        try:
            if not request.user.is_authenticated:
                logger.warning("Unauthorized access attempt to NoShowPolicy PUT endpoint")
                return Response(
                    {"detail": "Authentication credentials were not provided."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            policy = get_object_or_404(NoShowPolicy, user=request.user)
            serializer = NoShowPolicySerializer(policy, data=request.data, partial=True)

            if serializer.is_valid():
                serializer.save()
                logger.info(f"NoShowPolicy updated successfully for user {request.user}")
                return Response(serializer.data)

            logger.error(
                f"Invalid data for NoShowPolicy update by user {request.user}: {serializer.errors}"
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class CommunicationPreferencesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            """Retrieve the current user's communication preferences"""
            preferences, created = CommunicationPreferences.objects.get_or_create(
                user=request.user
            )
            serializer = CommunicationPreferencesSerializer(preferences)
            logger.info(f"Fetched communication preferences for user {request.user}")
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def put(self, request, *args, **kwargs):
        try:
            """Update the current user's communication preferences"""
            preferences, created = CommunicationPreferences.objects.get_or_create(
                user=request.user
            )
            serializer = CommunicationPreferencesSerializer(
                preferences, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                logger.info(f"Updated communication preferences for user {request.user}")
                return Response(serializer.data, status=status.HTTP_200_OK)
            logger.error(
                f"Invalid data for updating communication preferences by user {request.user}: {serializer.errors}"
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


def send_otp(user):
    otp = str(random.randint(100000, 999999))
    user.otp = otp
    user.save()

    sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
    from_email = Email("akash.prajapati@techqware.com")  # Update with your sender email
    to_email = To(user.email)
    subject = "Your OTP for Password Change"
    content = Content("text/plain", f"Your OTP for password change is: {otp}")
    mail = Mail(from_email, to_email, subject, content)

    try:
        response = sg.send(mail)
        logger.info(f"Email sent to {user.email} with status code {response.status_code}")
    except Exception as e:
        logger.error(f"Error sending email: {e}")

    return otp


class RequestPasswordChangeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            current_password = request.data.get("current_password")
            new_password = request.data.get("new_password")
            if not check_password(current_password, user.password):
                return Response({"error": "Incorrect current password"}, status=status.HTTP_400_BAD_REQUEST)
            # Store new password in the database instead of session
            user.temp_password = new_password
            user.save()
            # Send OTP via email
            send_otp(user)
            return Response({"message": "OTP sent successfully to your email"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

class VerifyOTPAndChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            entered_otp = request.data.get("otp")
            if user.otp != entered_otp:
                return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)
            # Retrieve new password from the database
            new_password = user.temp_password
            if not new_password:
                return Response({"error": "No new password found. Please restart the process."}, status=status.HTTP_400_BAD_REQUEST)
            # Update the user's password
            user.password = make_password(new_password)
            user.otp = ""  # Clear OTP
            user.temp_password = ""  # Clear temp password
            user.save()
            return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

class MembershipAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Retrieve current user's membership plan (Requires authentication)"""
        try:
            membership = Membership.objects.get(user=request.user)
            return Response({"membership_type": membership.membership_type})
        except Membership.DoesNotExist:
            return Response({"message": "No membership found"}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request):
        try:
            """Select a membership plan (Requires authentication)"""
            membership_type = request.data.get("membership_type")
            if membership_type not in ["basic", "premium"]:
                return Response(
                    {"error": "Invalid membership type. Choose 'basic' or 'premium'."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Create or update the user's membership
            membership, created = Membership.objects.update_or_create(
                user=request.user, defaults={"membership_type": membership_type}
            )
            return Response(
                {"message": f"Successfully subscribed to {membership.membership_type} membership!"},
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            logger.exception("Unexpected error fetching user profile: %s", str(e))
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class LicenceCertificateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        try:
            serializer = LicenceCertificateSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(user=request.user)
                return Response({
                    "message": "Document uploaded successfully",
                    "data": serializer.data
                    }, status=status.HTTP_201_CREATED)
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        try:
            licence_certificates = LicenceCertificate.objects.filter(user=request.user, is_delete=False)
            serializer = LicenceCertificateSerializer(licence_certificates, many=True)
            return Response({"data": serializer.data}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class DeleteDocumentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        try:
            attachment_id = request.data.get("attachment_id")
            if not attachment_id:
                return Response({"error": "Please provide attachment id"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                licence_certificate = LicenceCertificate.objects.get(pk=attachment_id, user=request.user, is_delete=False)

            except LicenceCertificate.DoesNotExist:
                return Response({"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND)
            
            
            if licence_certificate.status != "Pending":
                return Response({"error": "Only pending documents can be deleted"}, status=status.HTTP_400_BAD_REQUEST)
            
            licence_certificate.is_delete = True
            licence_certificate.save()
            return Response({"message": "Document deleted successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MediaDigestAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, FileUploadParser]

    def post(self, request, *args, **kwargs):
        try:
            serializer = MediaDigestSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(user_doctor=request.user)
                return Response({
                    "msg": "Media_digest successfully added!",
                    "data": serializer.data
                }, status=status.HTTP_201_CREATED)
            return Response({
                "msg": "Validation failed.",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "msg": "Something went wrong.",
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        try:
            media_digest_documents = MediaDigest.objects.filter(user_doctor=request.user)
            serializer = MediaDigestSerializer(media_digest_documents, many=True)
            return Response({
                "msg": "Media_digest fetched successfully!",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                "msg": "Something went wrong while fetching data.",
                "error": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class RefundAppointmentPaymentAPIView(APIView):
    def post(self, request):

        appointment_id = request.data.get("appointment_id")
        cancelled_by = request.data.get("cancelled_by")

        appointment = get_object_or_404(BookedAppointment, id=appointment_id)
        now = timezone.now() 

        slot_start = appointment.slot.split("-")[0].strip()
        appointment_time = datetime.strptime(slot_start, "%H:%M").time()
        appointment_datetime = timezone.make_aware(datetime.combine(appointment.date, appointment_time)) 

        time_until_appointment = appointment_datetime - now
        
        if time_until_appointment < timedelta(hours=12):
            return Response({"error": "Cancellation not allowed within 12 hours of appointment."}, status=400)
        
        session = stripe.checkout.Session.retrieve(appointment.stripe_session_id)
        payment_intent = session.payment_intent

        if cancelled_by == "doctor":
            try:
                stripe.Refund.create(
                    payment_intent=payment_intent,
                )
            except Exception as e:
                return Response({"error": f"Stripe refund failed: {str(e)}"}, status=500)
            
            appointment.status = "Cancelled"
            appointment.payment_status = "Refunded"
            appointment.save()
            send_refund_email(appointment, cancelled_by, appointment.amount)
            return Response({"message": "Doctor cancelled. Full refund issued."}, status=200)

        elif cancelled_by == "patient":
            if time_until_appointment <= timedelta(hours=24):
                # Deduct 10%, refund 90%, add 10% to doctor wallet
                refund_amount = int(appointment.amount * Decimal("0.9"))
                doctor_earning = int(appointment.amount * Decimal("0.1"))               
                
                doctor = User.objects.filter(pk=appointment.doctor).first()
                
                wallet, created = DoctorWallet.objects.get_or_create(
                doctor=doctor,
                defaults={"balance": doctor_earning}
                )
                if not created:
                    DoctorWallet.objects.filter(doctor=doctor).update(
                        balance=F('balance') + doctor_earning
                    )
                
                try:
                    stripe.Refund.create(
                        payment_intent=payment_intent, 
                        amount=int(appointment.amount_paid * 0.9 * 100), 
                    ) 
                except Exception as e:
                    return Response({"error": f"Stripe partial refund failed: {str(e)}"}, status=500) 

                appointment.status = "Cancelled"
                appointment.payment_status = "Refunded"
                appointment.save()
                send_refund_email(appointment, cancelled_by, refund_amount)
                return Response({
                    "message": "Cancelled within 24 hours. 10% deducted, 90% refunded.",
                    "refunded_amount": refund_amount,
                    "doctor_earning": doctor_earning
                }, status=200)

            else:
                
                try:
                    stripe.Refund.create(
                        payment_intent=payment_intent, 
                    )
                except Exception as e:
                    return Response({"error": f"Stripe refund failed: {str(e)}"}, status=500)
                
                appointment.status = "Cancelled"
                appointment.payment_status = "Refunded"
                appointment.save()
                
                send_refund_email(appointment, cancelled_by, appointment.amount)
                
                return Response({
                    "message": "Cancelled more than 24 hours before appointment. Full refund issued."
                }, status=200)

        else:
            return Response({"error": "Invalid value for 'cancelled_by'."}, status=400)
  
  
  
def send_refund_email(appointment, cancelled_by, refund_amount):
    content = f"""
    Hello,
    
    A refund has been processed.
    
    Details:
    - Appointment ID: {appointment.id}
    - Cancelled By: {cancelled_by.title()}
    - Slot: {appointment.slot}
    - Date: {appointment.date}
    - refund: {refund_amount}

    Regards,
    My Health System
    """
    message = Mail(
        from_email=settings.SENDGRID_FROM_EMAIL,
        to_emails='refund@my-health.today',
        subject='Refund Processed Notification',
        plain_text_content=content
    )

    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
    except Exception as e:
        print(f"Failed to send refund email: {str(e)}")


class ClinicsAssociatedToDoctorsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            user = request.user

            # Ensure user is a Doctor
            if user.role != "Doctor":
                return Response({
                    "data": None,
                    "message": "Only doctors can access their clinic info.",
                    "status": "error"
                }, status=status.HTTP_403_FORBIDDEN)

            # Retrieve the associated clinic via work_place
            clinic = getattr(user, "work_place", None)
            if not clinic:
                return Response({
                    "data": None,
                    "message": "No clinic associated with this doctor.",
                    "status": "error"
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = ClinicListSerializer(clinic)

            return Response({
                "data": {
                    "message": "Clinic information retrieved successfully.",
                    "clinic": serializer.data
                },
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "message": str(e),
                "status": "error"
            }, status=status.HTTP_400_BAD_REQUEST)

        
class PatientsAssociatedToDoctorAPIView(APIView):
    permission_classes = [IsAuthenticated]


    def get(self, request, *args, **kwargs):
        try:
            doctor = request.user

            # Ensure only doctors can access
            if doctor.role != "Doctor":
                return Response({
                    "data": None,
                    "message": "Only doctors can access their associated patient info.",
                    "status": "error"
                }, status=status.HTTP_403_FORBIDDEN)

            # Fetch patient IDs who booked appointments with this doctor
            patient_ids = BookedAppointment.objects.filter(
                doctor=doctor.id
            ).values_list("patient", flat=True).distinct()

            patients = User.objects.filter(id__in=patient_ids)
            serialized_patients = PatientSerializer(patients, many=True)

            return Response({
                "data": {
                    "message": "Associated patients retrieved successfully.",
                    "patients": serialized_patients.data
                },
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                "message": str(e),
                "status": "error"
            }, status=status.HTTP_400_BAD_REQUEST)

class DoctorWalletAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            doctor = request.user
            completed_appointments = BookedAppointment.objects.filter(
                doctor=doctor.id,
                payment_status='Completed'
            )

            total_earned = sum(app.amount for app in completed_appointments)
            wallet, _ = DoctorWallet.objects.get_or_create(doctor=doctor)
            wallet.balance = Decimal(total_earned)
            wallet.save()

            serializer = DoctorWalletSerializer(wallet)
            return Response({
                "message": "Doctor wallet fetched and updated successfully!",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        except DoctorWallet.DoesNotExist:
            return Response({"error": "Wallet not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                "error": "Something went wrong while fetching/updating data.",
                "detail": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class AddSpecializationAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            if request.user.role != 'Doctor':
                return Response({"error": "Only doctors can add specializations."}, status=403)
            
            specialization = request.data.get('specialization')  
            if not specialization:
                return Response({"error": "Please provide a specialization."}, status=400)
            
            if Specialization.objects.filter(name__iexact=specialization).exists():
                return Response({"message": "This specialization already exists"}, status=400)

            Specialization.objects.create(
                name=specialization.capitalize(),
                is_approved = False  
            )
            send_specialization_approval_email(specialization)        
            return Response({'message': 'Specialization added successfully'}, status=201)
        
        except Exception as e:
            return Response({"error": str(e)}, status=500)

def send_specialization_approval_email(specialization):    
    subject = f"New Specialization Request: {specialization}"

    message = f"""
    A doctor has submitted a new specialization request: {specialization}

    Please log in to the admin panel to review and take action.

    Thanks,  
    My Health Team
        """

    try:
        sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        email = Mail(
            from_email=settings.SENDGRID_FROM_EMAIL,
            to_emails='approvals@my-health.today',
            subject=subject,
            plain_text_content=message
        )
        sg.send(email)
    except Exception as e:
        print("Error sending approval email:", e)

class DoctorInfoAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            userID = request.query_params.get('doctor_user_id') 
            if not userID:
                return Response({'message':'doctor id is requeired'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:  
                user = User.objects.get(pk=userID)
            except User.DoesNotExist:
                return Response({'message': 'Doctor does not exist'}, status=status.HTTP_400_BAD_REQUEST)
            
            try: 
                doctor = Doctor.objects.get(user=user)
            except Doctor.DoesNotExist:
                return Response({'message': 'User is not a doctor'}, status=status.HTTP_400_BAD_REQUEST)
            
            license_data = LicenceCertificate.objects.filter(user=user).first()
            
            if not license_data:
                doctor_license_data = "not found"
            else:
                doctor_license_data = {
                    "description": license_data.description,
                    "attatchment": license_data.attachment.url,
                    "status": license_data.status,
                    "rejection_reason": license_data.rejection_reason
                }
                
            media_data = MediaDigest.objects.filter(user_doctor=user).first()
            
            if not media_data:
                media_digest = "not found"
            else:
                media_digest = {
                    "title": media_data.title,
                    "description": media_data.description,
                    "attatchment": media_data.attachment_file.url,        
                }
            reviews = Review.objects.filter(doctor=doctor)
            
            if not reviews:
                doctor_review = "review not found"
            else:
                doctor_review = [
                    {
                       "patient":{
                           "id": review.patient.user.id,
                           "name": review.patient.user.get_full_name()
                       },
                        "doctor":{
                           "id": review.doctor.user.id,
                           "name": review.doctor.user.get_full_name()
                       },
                        "title": review.title,
                        "content": review.content,
                        "rating": review.rating,
                        "recommend": review.recommend
                    }
                    for review in reviews
                ]
                
            data = {
                "id": user.id,
                "name": user.get_full_name(),
                "email": user.email,
                "contact": user.phone_number,
                "city": user.city,
                "country": user.country,
                "expertise": user.expertise,
                "professional_stat": user.professional_stat,
                "profile": user.profile_picture.url,
                "qualification": doctor.qualifications,
                "speciality": doctor.specialty,
                "experience_years": doctor.experience_years,
                "license": doctor_license_data,
                "media_digest": media_digest,
                "reviews": doctor_review          
            }
            
            return Response({
                "message": "Retrieved successfully",
                "data": data
            })
         
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
                