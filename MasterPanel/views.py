from django.shortcuts import render, get_object_or_404

# Create your views here.

from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from doctors.models import Doctor
from clinics.models import Clinic
from patients.models import Patient
from rest_framework import status
from .serializers import PatientSerializer, DoctorSerializer
from django.db.models import Q
from users.models import User

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
