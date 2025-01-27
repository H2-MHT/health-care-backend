from django.urls import path
from .views import (
    DoctorNotesCreateAPIView,
    DoctorListAPIView,
    AppointmentManagementAPIView,
    CombinedAPIView
    )


urlpatterns = [
    path('create-note/', DoctorNotesCreateAPIView.as_view(), name='create_doctor_note'),
    path('doctor-notes/<int:pk>/', DoctorNotesCreateAPIView.as_view(), name='delete_doctor_note'),
    path("get-doctors/", DoctorListAPIView.as_view(), name="doctor-list"),
    # appointment management 
    path('preferences/', AppointmentManagementAPIView.as_view(), name='appointment-preferences'),
    path('preferences/<int:pk>/', AppointmentManagementAPIView.as_view(), name='appointment-preference-detail'),
    path('doctor-setting/', CombinedAPIView.as_view(), name='combined-api'),
    path('doctor-setting/<int:pk>/', CombinedAPIView.as_view(), name='combined-api'),

]
