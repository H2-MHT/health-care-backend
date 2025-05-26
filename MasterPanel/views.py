from django.shortcuts import render, get_object_or_404

# Create your views here.
from django.db.models import Sum, Case, When, F, DecimalField
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from django.http import (
    HttpResponse,
    Http404,
    FileResponse
)
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_200_OK
from rest_framework.views import APIView
from doctors.models import (
    Doctor,
    BookedAppointment,
)
from clinics.models import Clinic
from patients.models import Patient
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from .serializers import PatientListSerializer, DoctorSerializer, PatientDetailSerializer
from payments.serializers import AccountDetailSerializer, TransactionSerializer
from doctors.serializers import LicenceCertificateSerializer
from django.db.models import Q
from users.models import User
from payments.models import Transaction, AccountDetail, Payment
from rest_framework import status
from doctors.models import LicenceCertificate
from sendgrid.helpers.mail import Mail, From, To
from consultations.models import ConsultationReport
from reviews.models import (
    Review, 
    Report, 
    Reply
)
from reviews.serializers import (
    ReportSerializer,
    ReviewSerializer,
    ReplySerializer
)
from doctors.models import Specialization
from .serializers import SpecializationSerializer
from django.conf import settings
import stripe
import os 
from django.apps import apps
from django.utils.timezone import make_aware
from datetime import datetime
import csv
import io
from rest_framework.parsers import MultiPartParser
from io import StringIO, BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.pagesizes import landscape
from reportlab.platypus import (
    SimpleDocTemplate, 
    Table, 
    TableStyle, 
    Paragraph, 
    Spacer,
)
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from datetime import date
from utils.pagination import(
    pagination_view,
    create_paginated_response,
)
from django.utils.crypto import get_random_string
from rest_framework.permissions import IsAuthenticated
import sendgrid
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, To
import logging
from datetime import time
from django.utils import timezone
from django.db.models.functions import ExtractMonth, ExtractYear
from django.db.models import Count, Sum
import calendar
from calendar import monthrange
from decimal import Decimal
from users.models import Ticket
from users.serializers import AdminSupportTicketSerializer
from django.utils.timezone import now
from django.contrib.auth import get_user_model
import secrets
import string
from django.urls import reverse

User = get_user_model()

stripe.api_key = settings.STRIPE_SECRET_KEY

logger = logging.getLogger(__name__)


class IsSuperAdminOrAdmin(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role.lower() in ["superadmin", "admin", "super-admin", "Super Admin"]
        )


class IsNotBlocked(BasePermission):
    """
    Prevent access to any API if the user is blocked.
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_active  # Only active users can access



class TotalPatientAndDoctorsView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]

    def get(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        role = request.query_params.get('role')
        
        total_doctors = User.objects.filter(is_verified=True,role="Doctor").count()
        total_patients = User.objects.filter(is_verified=True,role="Patient").count()
        total_clinics = User.objects.filter(is_verified=True,role="Clinic").count()
        
        
            
        if not start_date or not end_date or not role:
            data = {
                "total_doctors": total_doctors,
                "total_patients": total_patients,
                "total_clinics": total_clinics,
            }
            return Response({'message': 'Retrieved successfully','data':data}, status=status.HTTP_200_OK)
            
        else:
            if role not in ["Doctor", "Patient", "Clinic"]:
                return Response({'message': 'Role must be Doctor, Patient or Clinic'}, status=status.HTTP_400_BAD_REQUEST)
            
            converted_start_date = datetime.strptime(start_date, '%d-%m-%Y').date()
            converted_end_date = datetime.strptime(end_date, '%d-%m-%Y').date()
            start_datetime = timezone.make_aware(datetime.combine(converted_start_date, time.min))
            end_datetime = timezone.make_aware(datetime.combine(converted_end_date, time.max))
            
            doctors = User.objects.filter(is_verified=True, created_at__range=(start_datetime, end_datetime), role="Doctor").count()     
            patients = User.objects.filter(is_verified=True, created_at__range=(start_datetime, end_datetime), role="Patient").count()        
            clinics = User.objects.filter(is_verified=True, created_at__range=(start_datetime, end_datetime), role="Clinic").count()
            
            # month wise count of patients or doctors
            target_year = converted_start_date.year
            start_of_year = timezone.make_aware(datetime.combine(date(target_year, 1, 1), time.min))
            end_of_year = timezone.make_aware(datetime.combine(date(target_year, 12, 31), time.max))
            
            monthly_patient_counts = (
            User.objects.filter(
                is_verified=True,
                created_at__range=(start_of_year, end_of_year),
                role=role
            )
            .annotate(month=ExtractMonth('created_at'), year=ExtractYear('created_at'))
            .values('month', 'year')
            .annotate(count=Count('id'))
            .order_by('month')
            )
            count_dict = {entry['month']: entry['count'] for entry in monthly_patient_counts}

            monthly_data = [
                {
                    'month': calendar.month_name[month],
                    'count': count_dict.get(month, 0)
                }
                for month in range(1, 13)
            ]
            
            total_appointmetns = BookedAppointment.objects.filter(status__in=["Completed", "Confirmed", "Pending"]).count()
            current_month_appointments = BookedAppointment.objects.filter(status__in=["Completed", "Confirmed", "Pending"], date__range=(start_datetime, end_datetime)).count()
                    
            data = {
                'total': {
                    'total_doctors': total_doctors,
                    'total_patients': total_patients,
                    'total_clinics': total_clinics,
                    'total_appointments': total_appointmetns
                },
                'current':{
                        'filtered_doctors': doctors,
                        'filtered_patients': patients,
                        'filtered_clinics': clinics,
                        'filtered_appointments': current_month_appointments
                },
                f"monthly_data": monthly_data
            }
            return Response({'message': 'Retrieved successfully','data': data}, status=status.HTTP_200_OK)
            
class PatientListCreateAPIView(APIView):
    """
    API to list and create patients.
    Supports searching and filtering.
    """
    permission_classes = [IsSuperAdminOrAdmin]
    
    def get(self, request):
        # Search and filter
        query = request.GET.get("query", None)  # Search by name/email
        chronic_conditions = request.GET.get("chronic_conditions", None)
        fav_doc = request.GET.get("fav_doc", None)
        blocked = request.GET.get("blocked", None)

        patients = Patient.objects.all()

        if query:
            patients = patients.filter(
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(user__email__icontains=query)
            )

        if chronic_conditions:
            patients = patients.filter(chronic_conditions__icontains=chronic_conditions)

        if fav_doc:
            patients = patients.filter(fav_doc__id=fav_doc)

        if blocked is not None:
            patients = patients.filter(user__is_active=(blocked.lower() != "true"))

        serializer = PatientSerializer(patients, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Create a new patient."""
        serializer = PatientSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PatientRetrieveUpdateDeleteAPIView(APIView):
    """
    API to retrieve, update, or delete a single patient.
    """
    permission_classes = [IsSuperAdminOrAdmin]
    
    def get(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        serializer = PatientSerializer(patient)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        serializer = PatientSerializer(patient, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        patient.delete()
        return Response({"message": "Patient deleted successfully"}, status=status.HTTP_200_OK)


class PatientBlockUnblockAPIView(APIView):

    def post(self, request, pk):
        user = get_object_or_404(User, id=pk)

        if user.role == "SuperAdmin":
            return Response({"message": "Cannot block a Super Admin"}, status=status.HTTP_403_FORBIDDEN)

        user.is_active = not user.is_active  # Toggle block/unblock
        user.save()
        status_msg = "blocked" if not user.is_active else "unblocked"
        return Response({"message": f"User {status_msg} successfully"}, status=status.HTTP_200_OK)
    
    
    
    
# Doctor Managementes
class DoctorManagementView(APIView):
    """
    API for managing doctors: View, Add, Edit, Delete, Search, Apply Filters, Block/Unblock.
    Only Super Admins can access this API.
    """
    permission_classes = [IsSuperAdminOrAdmin]

    def get(self, request):
        """List doctors with optional search & filters"""
        doctors = User.objects.filter(role="Doctor")
        
        # Apply search/filter if query params exist
        search_query = request.query_params.get("search")
        if search_query:
            doctors = doctors.filter(first_name__icontains=search_query) | doctors.filter(last_name__icontains=search_query) | doctors.filter(email__icontains=search_query)

        serializer = DoctorSerializer(doctors, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Add a new doctor"""
        serializer = DoctorSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(role="Doctor")  # Ensure role is Doctor
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, doctor_id):
        """Edit doctor details"""
        try:
            doctor = User.objects.get(id=doctor_id, role="Doctor")
            serializer = DoctorSerializer(doctor, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"message": "Doctor not found"}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, doctor_id):
        """Delete a doctor"""
        try:
            doctor = User.objects.get(id=doctor_id, role="Doctor")
            doctor.delete()
            return Response({"message": "Doctor deleted successfully"}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"message": "Doctor not found"}, status=status.HTTP_404_NOT_FOUND)

class DoctorBlockUnblockView(APIView):
    """
    API to block/unblock a doctor.
    Only accessible by Super Admin.
    """
    permission_classes = [IsSuperAdminOrAdmin]

    def post(self, request, doctor_id):
        """Toggle block/unblock status of a doctor"""
        try:
            doctor = User.objects.get(id=doctor_id, role="Doctor")
            doctor.is_active = not doctor.is_active
            doctor.save()
            status_message = "unblocked" if doctor.is_active else "blocked"
            return Response({"message": f"Doctor {status_message} successfully"}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"message": "Doctor not found"}, status=status.HTTP_404_NOT_FOUND)


class UserListAPIView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]

    def get(self, request):
        try:
            role = request.query_params.get("role")
            search_key = request.query_params.get("search_key", "").strip()

            if not role:
                return Response({"message": "Role is required"}, status=status.HTTP_400_BAD_REQUEST)

            role = role.capitalize()
            data = []

            if role == "Doctor":
                doctors_data = Doctor.objects.filter(user__role="Doctor", user__is_deleted=False)

                if search_key:
                    doctors_data = doctors_data.filter(
                        Q(user__first_name__istartswith=search_key) |
                        Q(user__last_name__istartswith=search_key)
                    )

                doctors, headers = pagination_view(doctors_data, request)
                
                data = [
                    {
                        "id": doctor.user.id,  # Pass user_id
                        "doctor_id": doctor.id,  # Pass doctor_id
                        "uid": doctor.user.uid,  # Pass user uid
                        "name": doctor.user.get_full_name(),
                        "gender": doctor.user.gender,
                        "dob": doctor.user.dob,
                        "email": doctor.user.email,
                        "profile_picture": doctor.user.profile_picture.url if doctor.user.profile_picture else None,
                        "speciality": doctor.specialty,
                        "city": doctor.user.city,
                        "country": doctor.user.country,
                        "phone_number": doctor.user.phone_number,
                        "currency": doctor.user.currency,
                        "expertise": doctor.user.expertise,
                        "experience_years": doctor.experience_years,
                        "professional_stat": doctor.user.professional_stat,
                        "bio": doctor.user.bio,
                        "is_active": doctor.user.is_active,
                        "planned_hourly_rate": doctor.planned_hourly_rate,
                        "urgent_hourly_rate": doctor.urgent_hourly_rate,
                        "total_appointments": BookedAppointment.objects.filter(doctor=doctor.user.id).count(),
                        "completed_appointments": BookedAppointment.objects.filter(doctor=doctor.user.id, status="Completed").count(),
                        "total_patients": BookedAppointment.objects.filter(doctor=doctor.user.id, status="Completed").values('patient').distinct().count(),
                        "today's_appointments": BookedAppointment.objects.filter(date=date.today(), doctor=doctor.user.id).count(),
                        "stripe_link": doctor.stripe_link if doctor.stripe_link else None,
                    }
                    for doctor in doctors
                ]

            elif role == "Patient":
                patients_data = User.objects.filter(role="Patient", is_deleted=False)

                if search_key:
                    patients_data = patients_data.filter(
                        Q(first_name__istartswith=search_key) |
                        Q(last_name__istartswith=search_key)
                    )
                patients, headers = pagination_view(patients_data, request)
                
                data = [
                    {
                        "id": patient.id,  # Pass user_id
                        "uid": patient.uid,  # Pass user uid
                        "name": patient.get_full_name(),
                        "email": patient.email,
                        "gender": patient.gender,
                        "dob": patient.dob,
                        "profile_picture": patient.profile_picture.url if patient.profile_picture else None,
                        "country": patient.country,
                        "city": patient.city,
                        "currency": patient.currency,
                        "bio": patient.bio,
                        "phone_number": patient.phone_number,
                        "is_active": patient.is_active,
                        "total_appointments": BookedAppointment.objects.filter(patient=patient.id).count(),
                        "completed_appointments": BookedAppointment.objects.filter(patient=patient.id, status="Completed").count(),
                    }
                    for patient in patients
                ]

            elif role == "Clinic":
                clinics_data = Clinic.objects.filter(user__role="Clinic", user__is_deleted=False)

                if search_key:
                    clinics_data = clinics_data.filter(
                        Q(user__first_name__istartswith=search_key) |
                        Q(user__last_name__istartswith=search_key)
                    )
                clinics, headers = pagination_view(clinics_data, request)
                
                data = [
                    {
                        "id": clinic.id,
                        "clinic_user_id": clinic.user.id,  # Pass user_id
                        "uid": clinic.user.uid,  # Pass user uid
                        "name": clinic.public_name if clinic.public_name else clinic.user.get_full_name(),
                        "email": clinic.user.email,
                        "profile_picture": clinic.clinic_logo.url if clinic.clinic_logo else None,
                        "country": clinic.user.country,
                        "city": clinic.user.city,
                        "bio": clinic.user.bio,
                        "currency": clinic.user.currency,
                        "phone_number": clinic.user.phone_number,
                        "website": clinic.website,
                        "address": clinic.address,
                        "is_active": clinic.user.is_active,
                    }
                    for clinic in clinics
                ]
            
            else:
                return Response({"message": "Invalid role specified"}, status=status.HTTP_400_BAD_REQUEST)
            
            return create_paginated_response(f"{role} list retrieved successfully.", data, headers)
        
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DetailOfUser(APIView):
    permission_classes = [IsSuperAdminOrAdmin]
    def post(self, request, pk):
        role = request.data.get("role")
        user = get_object_or_404(User, id=pk, role=role, is_deleted=False)
        serializer = PatientDetailSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class BlockUser(APIView):
    permission_classes = [IsSuperAdminOrAdmin]

    def put(self, request, id):
        try:
            # Ensure the user exists
            role = request.query_params.get("role")
            user = get_object_or_404(User, pk=id, role=role)

            is_active = request.data.get("is_active")

            if is_active is None:
                return Response({"error": "is_active field is required"}, status=status.HTTP_400_BAD_REQUEST)

            if not isinstance(is_active, bool):
                return Response({"error": "is_active must be a boolean (true or false)"},
                                status=status.HTTP_400_BAD_REQUEST)


            user.is_active = is_active
            user.save()

            status_message = "User has been blocked." if not user.is_active else "User is now active."
            return Response({"message": status_message, "is_active": user.is_active}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



class DeleteUser(APIView):
    permission_classes = [IsSuperAdminOrAdmin]

    def put(self, request, pk):
        try:
            # Ensure the user exists and is a Patient
            role = request.query_params.get("role")
            user = get_object_or_404(User, pk=pk, role=role)


            is_deleted = request.data.get("is_deleted")

            if is_deleted is None:
                return Response({"error": "is_deleted field is required"}, status=status.HTTP_400_BAD_REQUEST)

            if not isinstance(is_deleted, bool):
                return Response({"error": "is_deleted must be a boolean (true or false)"}, status=status.HTTP_400_BAD_REQUEST)


            user.is_deleted = is_deleted
            user.save()

            status_message = "Patient has been marked as deleted." if is_deleted else "Patient is now active."
            return Response({"message": status_message, "is_deleted": user.is_deleted}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class DoctorWithdrawAPIView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]
    def get(self, request, *args, **kwargs):
        try:
            if request.user.role == 'SuperAdmin':
                doctor_id = request.query_params.get('doctor_id')
                if not doctor_id:
                    transactions = Transaction.objects.all()
                else:
                    try:
                        user = User.objects.get(id=doctor_id)
                        doctor = Doctor.objects.filter(user=user).first()
                        if not doctor:
                            return Response({"error": "Requested user is not a doctor"}, status=status.HTTP_404_NOT_FOUND)
                        
                        transactions = Transaction.objects.filter(account__user=user)
                    except User.DoesNotExist:
                        return Response({"error": "Doctor not found with requested id."}, status=status.HTTP_404_NOT_FOUND)

                # Calculate total wallet amount: Deposit (+), Withdrawal (-)
                # Wallet calculation only on success transactions
                total_wallet_amount = transactions.filter(status='success').aggregate(
                    total=Sum(
                        Case(
                            When(transaction_type="Deposit", then=F('amount')),
                            When(transaction_type="Withdrawal", then=F('amount') * -1),
                            default=0,
                            output_field=DecimalField()
                        )
                    )
                )['total'] or 0

                # if amount is negative, set it to 0
                if total_wallet_amount < 0:
                    total_wallet_amount = 0

                paginated_transactions, headers = pagination_view(transactions, request)
                transaction_serializer = TransactionSerializer(paginated_transactions, many=True)
                
                response= create_paginated_response(
                    "Account details fetched successfully.",
                    transaction_serializer.data,
                    headers
                )
                response.data['total_wallet_amount'] = str(total_wallet_amount)
                return response
            else:
                return Response({"error": "You are not authorized to access this data"}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

    def put (self, request, *args, **kwargs):
        try:
            if request.user.role != 'SuperAdmin':
                return Response({"error": "Only SuperAdmin can approve or reject requests."}, status=status.HTTP_400_BAD_REQUEST)
            
            transaction_id = request.data.get("transaction_id")
            new_status = request.data.get("status", "").strip()
            rejection_reason = request.data.get("rejection_reason", "").strip()

            if not transaction_id:
                return Response({"error": "Transaction ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            

            if new_status not in ["success", "failed"]:
                return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)
            
            transaction = Transaction.objects.filter(id=transaction_id).first()
         
            if not transaction:
                return Response({"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND)
            
            if new_status == "failed" and not rejection_reason:
                return Response({"error": "Rejection reason is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            if new_status == "failed":
                transaction.rejection_reason = rejection_reason
            else:
                transaction.rejection_reason = ""

            transaction.status = new_status
            transaction.save(update_fields=['status', 'rejection_reason'])


            return Response(
            {
                "message": f"Transaction {new_status} successfully.",
                "transaction_id": transaction.id,
                "new_status": transaction.status,
                "rejection_reason": transaction.rejection_reason
            },status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        
class VerifyDocumentAPIView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]
    def get(self, request, *args, **kwargs):
        try:
            if request.user.role != 'SuperAdmin':
                return Response(
                    {"error": "Only SuperAdmin can verify documents."}, 
                    status=status.HTTP_403_FORBIDDEN
                )

            user_id = request.query_params.get("user_id")

            if user_id:
                licence_certificate = LicenceCertificate.objects.filter(user_id=user_id, is_delete=False)
            else:
                licence_certificate = LicenceCertificate.objects.all()

            licence_certificate_serializer = LicenceCertificateSerializer(licence_certificate, many=True)

            return Response(
                {
                    "message": "Licence Certificate Document(s) Fetched Successfully",
                    "licence_certificate": licence_certificate_serializer.data
                }, 
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        

    def patch(self, request, *args, **kwargs):
        try:
            if request.user.role != 'SuperAdmin':
                return Response({"error": "Only SuperAdmin can approve or reject document."}, status=status.HTTP_403_FORBIDDEN)
            
            licence_certificate_id = request.data.get("licence_certificate_id")
            if not licence_certificate_id:
                return Response({"error": "Licence Certificate ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            user_id = request.data.get("user_id")
            if not user_id:
                return Response({"error": "User ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                licence_certificate = LicenceCertificate.objects.get(id=licence_certificate_id)
            except LicenceCertificate.DoesNotExist:
                return Response({"error": "Licence Certificate not found"}, status=status.HTTP_404_NOT_FOUND)
            
            if licence_certificate.user_id != user_id:
                return Response({"error": "User ID does not match with Licence Certificate"}, status=status.HTTP_400_BAD_REQUEST)

            status_value = request.data.get("status")
            rejection_reason = request.data.get("rejection_reason", "").strip()

            if not status_value:
                return Response({"error": "Status is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            if status_value == "Rejected" and not rejection_reason:
                return Response({"error": "Rejection reason is required when rejecting a document"}, status=status.HTTP_400_BAD_REQUEST)

            licence_certificate.status = status_value 

            if status_value == "Rejected":
                licence_certificate.rejection_reason = rejection_reason
            else:
                licence_certificate.rejection_reason = ""

            licence_certificate.save()

            response_data = {
                "message": "Document verification updated successfully",
                "licence_certificate_id": licence_certificate.id,
                "status": licence_certificate.status,  # Use correct DB field
                "rejection_reason": licence_certificate.rejection_reason
            }

            return Response({"message": "Licence Certificate updated successfully", "data": response_data}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class ReviewReportAPIView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]
    
    def get(self, request, *args, **kwargs):
        try:
            user_id = request.query_params.get("user_id")

            if user_id:
                user = User.objects.get(pk=user_id)
                report_queryset = Report.objects.filter(reported_by=user).order_by("-created_at")
            else:
                report_queryset = Report.objects.all().order_by("-created_at")

            paginated_reports, headers = pagination_view(report_queryset, request)
            report_serializer = ReportSerializer(paginated_reports, many=True)

            return create_paginated_response(
                "Report Fetched Successfully",
                report_serializer.data,
                headers
            )
        
        except User.DoesNotExist:
            return Response(
                {"error": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
                
    def patch(self, request, *args, **kwargs):
        try:
            report_id = request.data.get("report_id")
            if not report_id:
                return Response({"error": "Report ID is required"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                report = Report.objects.get(id=report_id)
            except Report.DoesNotExist:
                return Response({"error": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
            
            status_value = request.data.get("status")

            if status_value not in ["Valid", "Invalid"]:
                return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)
            
            report.status = status_value
            report.save()

            if status_value == "Valid":
                reviews = Review.objects.filter(report=report)  
                reviews.update(is_deleted=True)
            elif status_value == "Invalid":
                reviews = Review.objects.filter(report=report)
                reviews.update(is_deleted=False)

            response_data = {
                "message": "Report status updated successfully",
                "report_id": report.id,
                "status": report.status
            }

            return Response(response_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        
class ApproveSpecialization(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            if request.user.role != 'SuperAdmin':
                return Response({"error": "Only super admins can approve specializations."}, status=403)
            
            specialization_name = request.data.get('specialization_name')
            if not specialization_name:
                return Response({"error": "Please provide a specialization name."}, status=400)
            
            try:
                specialization = Specialization.objects.get(name__iexact=specialization_name)
            except Specialization.DoesNotExist:
                return Response({"error": "This specialization does not exist"}, status=400)
            
            if specialization.is_approved:
                return Response({'message': 'Specialization already approved'}, status=400)
            
            specialization.is_approved = True
            specialization.save()
            return Response({'message': 'Specialization approved successfully'}, status=200)
        
        except Exception as e:
            return Response({"error": str(e)}, status=500)
        
    def get(self, request):
        try:
            if request.user.role != 'SuperAdmin':
                return Response({"error": "Only super admins can perform this action."}, status=403)
            
            specialization = Specialization.objects.filter(is_approved=False)       
            if specialization:
                data = [
                {
                    "id": spec.id,
                    "name": spec.name,
                    "created_at": spec.created_date.strftime("%Y-%m-%d") if spec.created_date else None,
                }
                for spec in specialization
            ]     
            else:
                data = {}
            
            return Response({'message': 'Retrieved successfully', 'data': data}, status=200)
        
        except Exception as e:
            return Response({"error": str(e)}, status=500)
          
class MergeSpecialization(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            specializations = Specialization.objects.filter(is_approved=True)  
            data = {
                    "message": "Specializations list retrieved successfully",
                    "number_of_specializations": len(specializations),
                    "specializations": [
                        {
                            "id": specialization.id,
                            "name": specialization.name,
                            "description": specialization.description if specialization.description else "No description available",
                            "is_approved": specialization.is_approved,
                            "created_at": specialization.created_date.strftime("%Y-%m-%d") if specialization.created_date else None,
                            }
                        for specialization in specializations
                    ]
                }
            
            return Response(data, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
    
    def post(self, request):
        try:
            if request.user.role != 'SuperAdmin':
                return Response({"error": "Only super admins can merge specializations."}, status=403)
            
            data = request.data
            specialization = data.get('source_specialization')
            target_specialization = data.get('target_specialzation')
            
            if not specialization or not target_specialization:
                return Response({"error": "Source specialization and target specialization are required."}, status=400)
            
            merged_specialization = f"{specialization} {target_specialization}".capitalize()
            
            if Specialization.objects.filter(name__iexact=merged_specialization).exists():
                return Response({"error": "Specialization already exists."}, status=400)
            
            Specialization.objects.create(
                name=merged_specialization,
                is_approved = True  
            )
            
            specialization_to_delete = Specialization.objects.filter(name__iexact=target_specialization)
            specialization_to_delete.delete()
            return Response({'message': "specialization merged"}, status=201)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class NewSpecializationAPIView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]

    def post(self, request):
        try:
            serializer = SpecializationSerializer(data=request.data)

            if serializer.is_valid():
                serializer.save(is_approved=True)
                return Response(
                    {
                        "message": "Specialization added successfully",
                        "data": serializer.data
                    },
                    status=status.HTTP_201_CREATED
                )

            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": "Unexpected error occurred: " + str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def get(self, request):
        try:
            specializations = Specialization.objects.all()
            serializer = SpecializationSerializer(specializations, many=True)
            return Response(
                {
                    "message": "Specializations retrieved successfully",
                    "data": serializer.data
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def put(self, request):
        try:
            specialization_id = request.data.get('specialization_id')
            if not specialization_id:
                return Response(
                    {"error": "specialization_id is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            specialization = Specialization.objects.get(id=specialization_id)
            serializer = SpecializationSerializer(specialization, data=request.data, partial=True)

            if serializer.is_valid():
                serializer.save()
                return Response(
                    {
                        "message": "Specialization updated successfully",
                        "data": serializer.data
                    },
                    status=status.HTTP_200_OK
                )

            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        except Specialization.DoesNotExist:
            return Response(
                {"error": "Specialization not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": f"Unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request):
        try:
            specialization_id = request.data.get('specialization_id')
            if not specialization_id:
                return Response(
                    {"error": "specialization_id is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            specialization = Specialization.objects.get(id=specialization_id)
            specialization.delete()

            return Response(
                {"message": "Specialization deleted successfully"},
                status=status.HTTP_200_OK
            )

        except Specialization.DoesNotExist:
            return Response(
                {"error": "Specialization not found"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
class AdminWithdrawalRequestAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            if request.user.role != 'SuperAdmin':
                return Response({"error": "You are not authorized to perform this action"}, status=status.HTTP_403_FORBIDDEN)
            
            transactions = Transaction.objects.filter(transaction_type="Withdrawal", status="pending").order_by('-timestamp')
            withdrwal = []
            
            for transaction in transactions:
                data = {
                    "id": transaction.id,
                    "name": transaction.account.full_name,
                    "account_number": transaction.account.account_number,
                    "amount": transaction.amount,
                    "transaction_type": transaction.transaction_type,
                    "payment link": transaction.stripe_payment_link ,
                    "timestamp": transaction.timestamp
                }
                
                withdrwal.append(data) 
            return Response({'message': "Retrieved successfully", 'data': withdrwal}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
              
class ExportDataAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        model_input = request.query_params.get('table_name')
        export_format = request.query_params.get('file_type', 'csv')
        user_type_filter = request.query_params.get('user_type')

        if not model_input:
            return HttpResponse({"error": "Model name is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            model = apps.get_model('users', model_input) if model_input == 'User' else \
                    apps.get_model('doctors', model_input) if model_input == 'BookedAppointment' else \
                    apps.get_model('payments', model_input) if model_input == 'Payment' else \
                    apps.get_model('payments', model_input) if model_input == 'Transaction' else None
            if not model:
                raise LookupError
        except LookupError:
            return HttpResponse({"error": "Model not found"}, status=status.HTTP_404_NOT_FOUND)

        model_fields_map = {
            'User': ['id', 'first_name', 'last_name', 'phone_number', 'city', 'country', 'residence', 'email'],
            'BookedAppointment': ['id', 'doctor_name', 'patient_name', 'appointment_type', 'slot',  'status' , 'date', 'amount', 'payment_status'],
            'Payment': ['id', 'appointment', 'amount', 'total_amount', 'method', 'status', 'payment_notes'],
            'Transaction' : ['id', 'account', 'amount', 'transaction_type', 'reference']
        }

        selected_fields = model_fields_map.get(model_input)
        if not selected_fields:
            return HttpResponse({"error": "Model fields not found"}, status=status.HTTP_404_NOT_FOUND)

        user_ids = User.objects.filter(role=user_type_filter).values_list('id', flat=True)

        if model_input == 'User' and user_type_filter:
            data = User.objects.filter(role=user_type_filter).values(*selected_fields)

        elif model_input == 'BookedAppointment':
            status_filter = request.query_params.get('status')
            appointment_type = request.query_params.get('appointment_type')
            if appointment_type not in ['past', 'upcoming']:
                return Response({"error": "Invalid appointment type"}, status=status.HTTP_400_BAD_REQUEST)
            appointments = BookedAppointment.objects.filter(
                Q(doctor__in=user_ids) | Q(patient__in=user_ids)
            ) if user_type_filter else BookedAppointment.objects.all()

            if status_filter:
                appointments = appointments.filter(status__iexact=status_filter)

            if appointment_type == 'past':
                appointments = appointments.filter(date__lt=now().date())
            elif appointment_type == 'upcoming':
                appointments = appointments.filter(date__gte=now().date())

            # Get doctor and patient IDs to map names
            user_ids_in_appts = set(appointments.values_list('doctor', flat=True)) | set(appointments.values_list('patient', flat=True))
            user_map = {
                user.id: f"{user.first_name} {user.last_name}".strip()
                for user in User.objects.filter(id__in=user_ids_in_appts)
            }

            data = []
            for appt in appointments:
                data.append({
                    "id": appt.id,
                    "doctor_name": User.objects.get(id=appt.doctor).get_full_name(),
                    "patient_name": User.objects.get(id=appt.patient).get_full_name(),
                    "appointment_type": appt.appointment_type,
                    "slot": str(appt.slot),
                    "status": appt.status,
                    "date": appt.date,
                    "amount": appt.amount,
                    "payment_status": appt.payment_status
                })

        elif model_input == 'Payment' and user_type_filter:
            appointment_ids = BookedAppointment.objects.filter(
                Q(doctor__in=user_ids) | Q(patient__in=user_ids)
            ).values_list('id', flat=True)
            data = Payment.objects.filter(appointment_id__in=appointment_ids).values(*selected_fields)

        elif model_input == 'Transaction' and user_type_filter:
            account_ids = AccountDetail.objects.filter(user_id__in=user_ids).values_list('id', flat=True)
            data = Transaction.objects.filter(account_id__in=account_ids).values(*selected_fields)

        else:
            # For all other cases (no filter)
            data = model.objects.all().values(*selected_fields)

        if export_format == 'csv':
            return self.export_csv(data, selected_fields, model_input)
        elif export_format == 'pdf':
            return self.export_pdf(data, selected_fields, model_input, role=user_type_filter)
        else:
            return HttpResponse({"error": "Invalid format"}, status=status.HTTP_400_BAD_REQUEST)

    def export_csv(self, data, fields, model_name):
        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=fields)
        writer.writeheader()
        writer.writerows(data)
        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{model_name}.csv"'
        return response
    
    def export_pdf(self, data, fields, model_name, role):
        buffer = BytesIO()

        # Create PDF document
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []

        # Title
        styles = getSampleStyleSheet()
        title_text = f"{model_name.title()} {role or ''} Data"
        title = Paragraph(title_text, styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 20))  # Space after title

        # Prepare table data: header + rows
        table_data = [ [field.replace("_", " ").title() for field in fields] ]
        for row in data:
            table_data.append([str(row.get(field, "")) for field in fields])

        # Create the table
        table = Table(table_data, repeatRows=1)

        # Apply table styling
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))

        # Add table to document
        elements.append(table)

        # Build PDF
        doc.build(elements)
        buffer.seek(0)

        # Return response
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{model_name}_data.pdf"'
        return response

class ImportDataView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]
    parser_classes = [MultiPartParser]

    REQUIRED_FIELDS = [
        'first_name',
        'last_name',
        'email',
        'gender',
        'city',
        'country',
        'currency',
        'role',
    ]

    def post(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'No file was provided'}, status=status.HTTP_400_BAD_REQUEST)

        if not file_obj.name.endswith('.csv'):
            return Response({'error': 'Only CSV files are supported'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            decoded_file = file_obj.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)

            header_fields = reader.fieldnames
            missing_fields = [field for field in self.REQUIRED_FIELDS if field not in header_fields]
            if missing_fields:
                return Response(
                    {'error': 'Missing required fields', 'missing_fields': missing_fields},
                    status=status.HTTP_400_BAD_REQUEST
                )

            created_users = []
            for row_num, row in enumerate(reader, start=2):
                if not all(row.get(field) for field in self.REQUIRED_FIELDS):
                    return Response({'error': f'Missing values in row: {row}'}, status=status.HTTP_400_BAD_REQUEST)

                random_password = self.generate_password()

                if row['role'] not in ['Admin', 'Doctor', 'Patient', 'Clinic']:
                    return Response(
                        {'error': f"Invalid role '{row['role']}' at row {row_num}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                user = User.objects.create_user(
                    first_name=row['first_name'],
                    last_name=row['last_name'],
                    email=row['email'],
                    gender=row['gender'],
                    city=row['city'],
                    country=row['country'],
                    currency=row['currency'],
                    role=row['role'],
                    password=random_password,
                    is_verified=True
                )
                
                model_input = row['role']
                if model_input != 'Admin':
                    model = apps.get_model('doctors', model_input) if model_input == 'Doctor' else \
                        apps.get_model('patients', model_input) if model_input == 'Patient' else \
                        apps.get_model('clinics', model_input) if model_input == 'Clinic' else \
                        apps.get_model('MasterPanel', model_input) if model_input == 'Admin' else None
                    if not model:
                        raise LookupError
                    else:
                        model.objects.create(user=user)

                self.send_temp_password_email(user.email, random_password)
                created_users.append(user.email)

            return Response({'message': 'Users created successfully', 'users': created_users}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def generate_password(self, length=10):
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def send_temp_password_email(self, email, temp_password, name="User"):
        try:
            message = Mail(
                from_email=From(settings.SENDGRID_FROM_EMAIL, "Health Help"),
                to_emails=To(email)
            )
            message.template_id = 'd-f7b46f3ac1dc4d1e964ac7054a71f9e1'
            
            # dynamic template
            message.dynamic_template_data = {
                "name": name,
                "temp_password": temp_password
        }

            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            sg.send(message)
        except Exception as e:
            logger.error(f"Error sending temporary password email to {email}: {str(e)}")

class UserCSVTemplateAPIView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]

    def get(self, request, *args, **kwargs):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="user_import_template.csv"'

        writer = csv.writer(response)
        writer.writerow(['first_name', 'last_name', 'email', 'role', 'gender', 'city', 'country', 'currency'])
        return response

class DepartmentAPIView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]
    def get(self, request):
        try:
            data = []

            all_specializations = Specialization.objects.all()
            specializations, headers = pagination_view(all_specializations, request)
            for spec in specializations:
                doctors = Doctor.objects.filter(specialty=spec)

                doctor_list = []
                for doctor in doctors:
                    doctor_list.append({
                        'id': doctor.user.id,
                        'name': doctor.user.get_full_name(),
                        'profile_picture': doctor.user.profile_picture.url if doctor.user.profile_picture else None
                    })

                data.append({
                    'total_doctors': len(doctors),
                    'specialization': spec.name,
                    'description': spec.description,
                    'doctors': doctor_list
                })
            return create_paginated_response(f"Retrieved successfully.",data, headers)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class DoctorStripeLinkAddView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]

    def post(self, request, *args, **kwargs):
        doctor_id = request.data.get("doctor_id")
        stripe_link = request.data.get("stripe_link")

        if not doctor_id or not stripe_link:
            return Response({"error": "Doctor ID and Stripe link are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            doctor = Doctor.objects.get(id=doctor_id)
        except Doctor.DoesNotExist:
            return Response({"error": "Doctor not found."}, status=status.HTTP_404_NOT_FOUND)

        doctor.stripe_link = stripe_link
        doctor.save()

        return Response(
            {
                "message": "Stripe link saved successfully",
                "stripe_link": doctor.stripe_link
                },
            status=status.HTTP_200_OK
            )

class ReviewApproveView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]

    def post(self, request):
        try:
            review_id = request.data.get('review_id')
            review_status = request.data.get('status')
            
            try:
                review = get_object_or_404(Review, id=review_id)
            except Http404:
                return Response({"message": f"Review not found with given ID:{review_id}"}, status=status.HTTP_404_NOT_FOUND)
            
            if not review_status or review_status not in ["Approved", "Rejected"]:
                return Response({"message": "Invalid review status"}, status=status.HTTP_400_BAD_REQUEST)
            
            if review.status == review_status:
                return Response({"message": f"Review is already {review_status}"}, status=status.HTTP_400_BAD_REQUEST)
        
            if review_status == "Approved":
                review.status = review_status
                
            elif review_status == "Rejected":
                review.status = review_status
    
            review.save()
            return Response({"message": f"Review {review_status} successfully"}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    def get(self, request):
        try:
            review_list = Review.objects.filter(status="Pending").order_by('-created_at')
            reviews, headers = pagination_view(review_list, request)
            data = [
                 {
                    "id": review.id,
                    "patientName": review.patient.user.get_full_name(),
                    "doctorName": review.doctor.user.get_full_name(),
                    "rating": review.rating,
                    "content": review.content,
                    "date": review.created_at.strftime("%Y-%m-%d"),
                    "status": review.status
                }
                for review in reviews
            ]
            return create_paginated_response("Retrieved successfully.", data, headers)    
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)   
        

class ReplyApproveView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]

    def post(self, request):
        try:
            reply_id = request.data.get('reply_id')
            
            try:
                reply = get_object_or_404(Reply, id=reply_id)
            except Http404:
                return Response({"message": f"Reply not found with given ID:{reply_id}"}, status=status.HTTP_404_NOT_FOUND)
            
            if reply.is_approved:
                return Response({"message": "Reply is already approved"}, status=status.HTTP_400_BAD_REQUEST)

            reply.is_approved = True
            reply.save()
            return Response({"message": "Reply approved successfully"}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    def get(self, request):
        try:
            replies = Reply.objects.filter(is_approved=False)
            serializer = ReplySerializer(replies, many=True)
            return Response({"message": "Retrieved successfully", "data": serializer.data}, status=status.HTTP_200_OK)     
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class CloseDiscussionAPIView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]

    def post(self, request):
        try:
            review_id = request.data.get('review_id')
            if not review_id:
                return Response({"message": "Review ID is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                review = get_object_or_404(Review, id=review_id)
            except Http404:
                return Response({"message": f"Review not found with given id:{review_id}"}, status=status.HTTP_404_NOT_FOUND)
            
            if review.is_closed:
                return Response({"message": "Discussion is already closed"}, status=400)
            
            review.is_closed = True
            review.save()
            return Response({"message": "Discussion closed successfully"}, status=200)
        except Review.DoesNotExist:
            return Response({"message": "Review not found."}, status=404)

class DeleteInappropriateReviewOrReplyView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]

    def post(self, request):
        try:
            data = request.data
            target_type = data.get('target_type')
            target_id = data.get('target_id')
            
            if not target_type or not target_id:
                return Response({"message": "target_type and target_id are required."}, status=400)
            
            if target_type == 'review':
                try:
                    review = Review.objects.get(id=target_id)
                    review.delete()
                except Review.DoesNotExist:
                    return Response({"message": "Review not found."}, status=404)
                 
            elif target_type == 'reply':
                try:
                    reply = Reply.objects.get(id=target_id)
                    reply.delete()
                except Reply.DoesNotExist:
                    return Response({"message": "Reply not found."}, status=404)
                
            return Response({"message": f"{target_type.capitalize()} deleted successfully"}, status=200)
        except Review.DoesNotExist:
            return Response({"detail": "Review not found."}, status=404)

    
class CreateAdminAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != "SuperAdmin":
            return Response({"message": "You don't have permission."}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data
        required_fields = ["first_name", "last_name", "email", "dob", "city", "country"]

        missing_fields = [f for f in required_fields if not data.get(f)]
        if missing_fields:
            return Response({"detail": f"Missing fields: {', '.join(missing_fields)}"}, status=status.HTTP_400_BAD_REQUEST)

        email = data.get("email")
        if User.objects.filter(email=email).exists():
            return Response({"error": "email already exists."}, status=400)

        temp_password = get_random_string(length=10) 

        user = User(
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            email=email,
            dob=data.get("dob"),
            city=data.get("city"),
            country=data.get("country"),
            role="Admin",
            temp_password=temp_password,
            is_verified=True,
            is_staff=True,
        )
        user.set_password(temp_password)
        user.save()

        self.send_temp_password_email(user.email, temp_password)

        return Response({"message": "Admin account created successfully"}, status=status.HTTP_201_CREATED)

    def send_temp_password_email(self, email, temp_password):
        message = Mail(
            from_email=settings.SENDGRID_FROM_EMAIL,
            to_emails=email,
            subject='Temporary Password',
            plain_text_content=f'Your temporary password is {temp_password}'
            )
    
        try:
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            sg.send(message)
        except Exception as e:
            logger.error(f"Error sending email: {e}")


    def get(self, request):
        if request.user.role != "SuperAdmin":
            return Response({"message": "You don't have permission."}, status=status.HTTP_400_BAD_REQUEST)
        users = User.objects.filter(role="Admin").values("id", "first_name", "last_name", "email", "dob", "city", "country")
        paginated_users, headers = pagination_view(users, request)
        return create_paginated_response("Admins account fetched successfully", paginated_users, headers)
    
    def put(self, request):
        if request.user.role != "SuperAdmin":
            return Response({"message": "You don't have permission."}, status=status.HTTP_400_BAD_REQUEST)

        admin_id = request.query_params.get("admin_id")
        if not admin_id:
            return Response({"message": "Admin ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(id=admin_id, role="Admin")
        except User.DoesNotExist:
            return Response({"message": "Admin not found."}, status=status.HTTP_404_NOT_FOUND)
        
        for field in ["first_name", "last_name", "email", "dob", "city", "country"]:
            if field in request.data:
                setattr(user, field, request.data[field])

        user.save()
        updated_data = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "dob": user.dob,
            "city": user.city,
            "country": user.country,
            "email": user.email

        }
        return Response({"message": "Admin data updated successfully.", "data" : updated_data}, status=status.HTTP_200_OK)
    
    def delete(self, request):
        if request.user.role != "SuperAdmin":
            return Response({"message": "You don't have permission."}, status=status.HTTP_400_BAD_REQUEST)
        admin_id = request.data.get("admin_id")
        if not admin_id:
            return Response({"message": "Admin ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(id=admin_id, role="Admin")
            user.delete()
            return Response({"message": "Admin deleted successfully"}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "Admin not found"}, status=status.HTTP_404_NOT_FOUND)
    
class RevenueAPIView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]

    def get(self, request):
        try:
            start_date = request.query_params.get('start_date') 
            end_date = request.query_params.get('end_date')

            if not start_date or not end_date:
                return Response({"error": "start_date and end_date are required."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                converted_start_date = datetime.strptime(start_date, '%d-%m-%Y').date()
                converted_end_date = datetime.strptime(end_date, '%d-%m-%Y').date()
            except ValueError:
                return Response({"error": "Date format must be dd-mm-yyyy."}, status=status.HTTP_400_BAD_REQUEST)

            start_datetime = timezone.make_aware(datetime.combine(converted_start_date, time.min))
            end_datetime = timezone.make_aware(datetime.combine(converted_end_date, time.max))

            appointments = BookedAppointment.objects.filter(
                created_at__range=(start_datetime, end_datetime),
                status="Completed"
            )
            
            total_appointments = appointments.aggregate(total=Count('id'))['total'] or 0
            total_revenue = appointments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            gross_revenue = total_revenue * Decimal('0.20')

            data = {
                "total_appointments": total_appointments,
                "total_revenue": total_revenue,
                "gross_revenue": gross_revenue
            }

            return Response({"message":"Revenue data retrieved successfully","revenue": data}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class PastAndAUpcomingAppointmentsAPIView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]

    def get(self, request):
        try:
            search_key = request.query_params.get("search_key", "").strip()

            if search_key:
                users = User.objects.filter(
                    (Q(first_name__istartswith=search_key) | Q(last_name__istartswith=search_key)) & Q(role="Doctor")
                )
            else:
                users = User.objects.filter(role="Doctor")

            doctor_ids = list(users.values_list('id', flat=True))
            filtered_upcoming_appointments = BookedAppointment.objects.filter(
                status__in=["Pending", "Confirmed"],
                doctor__in=doctor_ids
            ).order_by('date')

            filtered_completed_appointments = BookedAppointment.objects.filter(
                status__in=["Completed", "Cancelled"],
                doctor__in=doctor_ids
            ).order_by('date')

            doctor_dict = {user.id: user for user in users}

            upcoming_appointments = pagination_view(filtered_upcoming_appointments, request)
            completed_appointments = pagination_view(filtered_completed_appointments, request)

            upcoming_appointments_list = []
            completed_appointments_list = []

            for appointment in upcoming_appointments[0]:
                doctor = doctor_dict.get(appointment.doctor)
                name = f"{doctor.first_name} {doctor.last_name}" if doctor else "Unknown"

                data = {
                    "id": appointment.id,
                    "doctor_name": name,
                    "date": appointment.date.strftime('%d-%m-%Y'),
                    "time": appointment.slot,
                    "status": appointment.status,
                    "appointment_type": appointment.appointment_type
                }
                upcoming_appointments_list.append(data)

            for appointment in completed_appointments[0]:
                doctor = doctor_dict.get(appointment.doctor)
                name = f"{doctor.first_name} {doctor.last_name}" if doctor else "Unknown"

                data = {
                    "id": appointment.id,
                    "doctor_name": name,
                    "date": appointment.date.strftime('%d-%m-%Y'),
                    "time": appointment.slot,
                    "status": appointment.status,
                    "appointment_type": appointment.appointment_type,
                    "amount": appointment.amount
                }
                completed_appointments_list.append(data)

            appointments = {
                "upcoming_appointments": upcoming_appointments_list,
                "past_appointments": completed_appointments_list
            }

            return create_paginated_response("Appointments retrieved successfully", appointments, {**upcoming_appointments[1], **completed_appointments[1]})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AdminSupportTicketAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        tickets = Ticket.objects.all().order_by('-created_at')
        paginated_tickets, headers = pagination_view(tickets, request)
        serializer = AdminSupportTicketSerializer(paginated_tickets, many=True)
        return create_paginated_response(
            "All support tickets retrieved successfully",
            serializer.data,
            headers
            )

    def patch(self, request):
        ticket_id = request.data.get("ticket_id")
        if not ticket_id:
            return Response({
                "message": "Ticket ID is required",
                "data": {}
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            ticket = Ticket.objects.get(ticket_id=ticket_id)
        except Ticket.DoesNotExist:
            return Response({
                "message": "Ticket not found",
                "data": {}
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = AdminSupportTicketSerializer(ticket, data=request.data, partial=True)
        if serializer.is_valid():
            if request.data.get("status", "").lower() == "resolved":
                ticket.resolved_at = now()
            serializer.save()
            return Response({
                "message": "Support ticket updated successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        return Response({
            "message": "Invalid data",
            "data": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class DoctorCountFromClinicAPIView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]

    def get(self, request):
        try:
            clinic_id = request.query_params.get('clinic_id')
            if not clinic_id:
                return Response({"error": "Clinic ID is required"}, status=status.HTTP_400_BAD_REQUEST)
              
            try:
                clinic = Clinic.objects.get(pk=clinic_id, user__role="Clinic", user__is_deleted=False) 
            except Clinic.DoesNotExist:
                return Response({"error": "Clinic not found"}, status=status.HTTP_404_NOT_FOUND) 
            
            search_key = request.query_params.get("search_key", "").strip()
            if search_key:
                users = User.objects.filter(first_name__istartswith=search_key, work_place=clinic, role="Doctor") | \
                        User.objects.filter(last_name__istartswith=search_key, work_place=clinic, role="Doctor")
            else:
                users = User.objects.filter(work_place=clinic, role="Doctor")
            paginated_users, headers = pagination_view(users, request)  
              
            doctor_list = []
            for user in paginated_users:
                try:
                    doctor = Doctor.objects.get(user=user)
                except Doctor.DoesNotExist:
                    continue
                data = {
                        "doctor_user_id": doctor.user.id,
                        "doctor_id": doctor.id,
                        "uid": doctor.user.uid,
                        "name": doctor.user.get_full_name(),
                        "gender": doctor.user.gender,
                        "dob": doctor.user.dob,
                        "email": doctor.user.email,
                        "profile_picture": doctor.user.profile_picture.url if doctor.user.profile_picture else None,
                        "speciality": doctor.specialty,
                        "city": doctor.user.city,
                        "country": doctor.user.country,
                        "phone_number": doctor.user.phone_number,
                        "currency": doctor.user.currency,
                        "expertise": doctor.user.expertise,
                        "experience_years": doctor.experience_years,
                        "professional_stat": doctor.user.professional_stat,
                        "is_active": user.is_active,
                        "bio": doctor.user.bio,
                        "total_appointments": BookedAppointment.objects.filter(doctor=doctor.user.id).count(),
                        "completed_appointments": BookedAppointment.objects.filter(doctor=doctor.user.id, status="Completed").count(),
                        "total_patients": BookedAppointment.objects.filter(doctor=doctor.user.id, status="Completed").values('patient').distinct().count(),
                        "today's_appointments": BookedAppointment.objects.filter(date=date.today(), doctor=doctor.user.id).count(),
                        "stripe_link": doctor.stripe_link if doctor.stripe_link else None,
                    }  
                doctor_list.append(data)
            
            doctor_in_clinic = {
                "clinic_name": clinic.public_name if clinic.public_name else clinic.user.get_full_name(),
                "doctors": doctor_list
            }            
            return create_paginated_response("Doctor count retrieved successfully", doctor_in_clinic, headers)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ConsultationReportListAPIView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]

    def get(self, request):
        try:    
            consultations = ConsultationReport.objects.all()
            report_list = []
            for consultation in consultations:
                if consultation.consultation_report:
                    report = {
                        "id": consultation.id,
                        "view_report": consultation.consultation_report.url,
                        "download_report": request.build_absolute_uri(f"/MasterPanel/consulation-report-download/{consultation.pk}/")
                        }
                    report_list.append(report)
                

            return Response({
                "message": "Consultation reports retrieved successfully",
                "data": report_list
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ConsultationReportDownloadAPIView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]

    def get(self, request, pk):
        try:
            consultation = ConsultationReport.objects.get(pk=pk)
            pdf_file = consultation.consultation_report

            response = FileResponse(pdf_file.open('rb'), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{pdf_file.name.split("/")[-1]}"'
            return response

        except ConsultationReport.DoesNotExist:
            return Response({"error": "Report not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
class DoctorCountWithSpecialization(APIView):
    permission_classes = [IsSuperAdminOrAdmin]
    def get(Self, request):
        try:
            doctor_count = []
            specializations = Specialization.objects.filter(is_approved=True)
            for specialization in specializations:
                doctors = User.objects.filter(role="Doctor", professional_stat=str(specialization.id)).count()
                data = {
                    "specialization": specialization.name,
                    "doctor_count": doctors
                }
                doctor_count.append(data)

            return Response({'message': "Retrieved successfully.", 'data': doctor_count}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)