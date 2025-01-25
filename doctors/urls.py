from django.urls import path
from .views import (
    DoctorNotesCreateAPIView,
    DoctorListAPIView,
    ReferralView,
    InvitationView,
    AppointmentManagementAPIView,
    )


urlpatterns = [
    path('create-note/', DoctorNotesCreateAPIView.as_view(), name='create_doctor_note'),
    path('doctor-notes/<int:pk>/', DoctorNotesCreateAPIView.as_view(), name='delete_doctor_note'),
    path("get-doctors/", DoctorListAPIView.as_view(), name="doctor-list"),
    
    # referral and invitation 
    path('referral/', ReferralView.as_view(), name='referral'),
    path('invitation/', InvitationView.as_view(), name='invitation'),
    
    # appointment management 
    path('preferences/', AppointmentManagementAPIView.as_view(), name='appointment-preferences'),
    path('preferences/<int:pk>/', AppointmentManagementAPIView.as_view(), name='appointment-preference-detail'),

]
