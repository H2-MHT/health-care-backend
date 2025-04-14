from django.shortcuts import render, get_object_or_404

# Create your views here.

from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from doctors.models import Doctor
from clinics.models import Clinic
from patients.models import Patient
from rest_framework import status
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
    def post(self, request):
        role = request.data.get("role")
        user = User.objects.filter(role=role, is_deleted=False)
        serializer = PatientListSerializer(user, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


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
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



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
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
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
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

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
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
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
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class ReviewReportAPIView(APIView):
    permission_classes = [IsSuperAdminOrAdmin]
    def get(self, request, *args, **kwargs):
        try:
            user_id = request.query_params.get("user_id")

            if user_id:
                user = User.objects.get(pk=user_id)
                report = Report.objects.filter(reported_by=user)
            else:
                report = Report.objects.all()

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
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def patch(self, request, *args, **kwargs):
        try:
            report_id = request.data.get("report_id")
            print("Request Data:", request.data)
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