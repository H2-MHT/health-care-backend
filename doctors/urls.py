from django.urls import path
from .views import DoctorNotesCreateAPIView, DoctorListAPIView

urlpatterns = [
    path('create-note/', DoctorNotesCreateAPIView.as_view(), name='create_doctor_note'),
    path('doctor-notes/<int:pk>/', DoctorNotesCreateAPIView.as_view(), name='delete_doctor_note'),
    path("get-doctors/", DoctorListAPIView.as_view(), name="doctor-list"),
]
