from django.urls import path
from .views import (
    DoctorNotesCreateAPIView,
    DoctorListAPIView,
    AppointmentManagementAPIView,
    GenerateReferralCodeView,
    InviteUserView,
    ConsultationSettingsAPIView,
    UserPreferenceView,
    ReschedulePolicyView,
    CancellationPolicyView,
    NoShowPolicyAPIView,
    CommunicationPreferencesAPIView,
    SelectMethodsAPIView,
    RequestPasswordChangeAPIView,
    VerifyOTPAndChangePasswordAPIView,
    MembershipAPIView,
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
    path('user-preferences/', UserPreferenceView.as_view(), name='user-preferences'),
    path('reschedule-policies/', ReschedulePolicyView.as_view(), name='reschedule-policy-list'),  # GET all, POST
    path('cancellation-policy/', CancellationPolicyView.as_view(), name='cancellation-policy'),
    path('no-show-policy/', NoShowPolicyAPIView.as_view(), name='no_show_policy'),
    path('communication-preferences/', CommunicationPreferencesAPIView.as_view(), name='communication-preferences'),
    
    # 2FA
    path('select-methods/', SelectMethodsAPIView.as_view(), name='select_2fa_method'),
    path('request-password-change/', RequestPasswordChangeAPIView.as_view(), name='request_otp'),
    path('verify-otp-change-password/', VerifyOTPAndChangePasswordAPIView.as_view(), name='verify_otp_change_password'),

    # Subsciption plan
    path('select-membership/', MembershipAPIView.as_view(), name='select-membership'),
]
