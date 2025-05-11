from django.shortcuts import render, get_object_or_404

# Create your views here.

from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from django.http import HttpResponse
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
from payments.models import Transaction, AccountDetail
from rest_framework import status
from doctors.models import LicenceCertificate
from reviews.models import Review, Report
from reviews.serializers import ReportSerializer
from doctors.models import Specialization
from .serializers import SpecializationSerializer
from django.conf import settings
import stripe
import os 
from django.apps import apps
import csv
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

stripe.api_key = settings.STRIPE_SECRET_KEY

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
        total_doctors = Doctor.objects.count()
        total_patients = Patient.objects.count()
        total_clinics = Clinic.objects.count()

        data = {
            'total_doctors': total_doctors,
            'total_patients': total_patients,
            'total_clinics': total_clinics
        }
        return Response({'total_counts': data})


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
            role = request.query_params.get("role")  # Role from query parameters
            if not role:
                return Response({"message": "Role is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            if role.capitalize() == "Doctor":
                doctors_data = Doctor.objects.filter(user__role="Doctor", user__is_deleted=False)
                doctors, headers = pagination_view(doctors_data, request)
                
                data = [
                    {
                        "id": doctor.user.uid,
                        "name": doctor.user.get_full_name(),
                        "profile_picture": doctor.user.profile_picture.url if doctor.user.profile_picture else None,
                        "speciality": doctor.specialty,
                        "country": doctor.user.country,
                        "total_patients": BookedAppointment.objects.filter(doctor=doctor.user.id, status="Completed").values('patient').distinct().count(),
                        "today's_appointments": BookedAppointment.objects.filter(date=date.today(), doctor=doctor.user.id).count(),
                        "stripe_link": doctor.stripe_link if doctor.stripe_link else None,
                    }
                    for doctor in doctors
                ]
            
            elif role.capitalize() == "Patient":
                patients_data = User.objects.filter(role="Patient", is_deleted=False)
                patients, headers = pagination_view(patients_data, request)
                
                data = [
                    {
                        "id": patient.uid,
                        "name": patient.get_full_name(),
                        "email": patient.email,
                        "profile_picture": patient.profile_picture.url if patient.profile_picture else None,
                        "country": patient.country,
                        "total_appointments": BookedAppointment.objects.filter(patient=patient.id).count(),
                        "completed_appointments": BookedAppointment.objects.filter(patient=patient.id, status="Completed").count(),
                    }
                    for patient in patients
                ]

            elif role.capitalize() == "Clinic":
                clinics_data = User.objects.filter(role="Clinic", is_deleted=False)
                clinics, headers = pagination_view(clinics_data, request)
                
                data = [
                    {
                        "id": clinic.uid,
                        "name": clinic.get_full_name(),
                        "email": clinic.email,
                        "profile_picture": clinic.profile_picture.url if clinic.profile_picture else None,
                        "country": clinic.country,
                        "city": clinic.city,
                        "phone_number": clinic.phone_number,
                        "address": clinic.residence,
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
                transaction = Transaction.objects.all()
                transaction_serializer = TransactionSerializer(transaction, many=True)
                return Response(
                    {
                        "message": "Account details fetched successfully.",
                        # "accounts": account_serializer.data,
                        "transactions": transaction_serializer.data
                    },status=status.HTTP_200_OK
                )
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
                report = Report.objects.filter(reported_by=user).order_by("-created_at")
            else:
                report = Report.objects.all().order_by('-created_at')

            report_serializer = ReportSerializer(report, many=True)

            return Response(
                {
                    "message": "Report Fetched Successfully",
                    "report": report_serializer.data
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
                        {"id": specialization.id, "name": specialization.name}
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
            model = apps.get_model('users', model_input)
        except LookupError:
            return HttpResponse({"error": "Model not found"}, status=status.HTTP_404_NOT_FOUND)

        selected_fields = [
            "id",
            "first_name",
            "last_name",
            "phone_number",
            "city",
            "country",
            "residence",
             "email",

        ] 

        if model_input == 'User' and user_type_filter:
            data = User.objects.filter(role=user_type_filter).values(*selected_fields)

        else:
            data = User.objects.all().values(*selected_fields)

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
        title_text = f"{model_name.title()} {role} Data"
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
            ('FONTSIZE', (0, 0), (-1, -1), 9),
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