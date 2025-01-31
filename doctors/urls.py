from django.urls import path
from .views import (
    DoctorNotesCreateAPIView,
    DoctorListAPIView,
    AppointmentManagementAPIView,
    GenerateReferralCodeView,
    InviteUserView,
    ConsultationSettingsAPIView,
    UserPreferenceView,
    UpdateReschedulePolicyView,
    AllowRescheduleView,
    redeem_invitation,
    )


urlpatterns = [
    path('create-note/', DoctorNotesCreateAPIView.as_view(), name='create_doctor_note'),
    path('doctor-notes/<int:pk>/', DoctorNotesCreateAPIView.as_view(), name='delete_doctor_note'),
    path("get-doctors/", DoctorListAPIView.as_view(), name="doctor-list"),
    
    # referral and invitation 
    path('referral/generate/', GenerateReferralCodeView.as_view(), name='generate_referral'),
    path('invite/', InviteUserView.as_view(), name='invite_user'),

    path('referral/redeem/<str:invitation_code>/', redeem_invitation, name='redeem_invitation'),
    path('consultation-settings/', ConsultationSettingsAPIView.as_view(), name='create_consultation_settings'),

    
    # appointment management 
    path('preferences/', AppointmentManagementAPIView.as_view(), name='appointment-preferences'),
    path('preferences/<int:pk>/', AppointmentManagementAPIView.as_view(), name='appointment-preference-detail'),
    
    path('user-preferences/', UserPreferenceView.as_view(), name='user-preferences'),
    
    path('allow-reschedule/', AllowRescheduleView.as_view(), name='reschedule-policy-list'),  # GET all, POST
    path('reschedule-policies/', UpdateReschedulePolicyView.as_view(), name='reschedule-policy-list'),  # GET all, POST


]
