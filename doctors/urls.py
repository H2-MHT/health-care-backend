from django.urls import path
from .views import (
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
    RequestPasswordChangeAPIView,
    VerifyOTPAndChangePasswordAPIView,
    MembershipAPIView,
    ConsultationSettingsAPIView,
    # AllDaySlotsAPIView,
    BookAppointmentAPIView,
    PatientAppointmentAPIView,
    DoctorAppointmentAPIView,
    # MyAppointmentsAPIView,
    RescheduleAppointmentAPIView,
    CancelAppointmentAPIView,
    AppointmentReminderAPIView,
    PaymentConfirmationAPIView,
    CreateStripeCheckoutSession,
    PaymentSuccessView,
    GetSlotsAPIView,
    AppointmentSummaryAPIView,
    # AvailableSlotsAPIView,
    LicenceCertificateAPIView,
    redeem_invitation,
    MediaDigestAPIView,
    PublicDoctorListAPIView,
    PublicDoctorDetailAPIView,
    DeleteDocumentAPIView,
    DeleteAppointmentAPIView,
    RefundAppointmentPaymentAPIView, 
    CompletedAppointmentListView,
    ClinicsAssociatedToDoctorsAPIView,
    PatientsAssociatedToDoctorAPIView,
    DoctorWalletAPIView,
    DoctorInfoAPIView,
    AddSpecializationAPIView
    )


urlpatterns = [
    path("get-doctors/", DoctorListAPIView.as_view(), name="doctor-list"),
    path('public-doctor-list/', PublicDoctorListAPIView.as_view(), name='public-doctor-list'),
    path('doctor-detail/', PublicDoctorDetailAPIView.as_view(), name='doctor-detail'),
    path("delete-appointment/", DeleteAppointmentAPIView.as_view(), name="appointment"),
    path('appointment-list/', CompletedAppointmentListView.as_view(), name='appoitment-list'),
    path('doctor-info/', DoctorInfoAPIView.as_view(), name="doctor-info"),
    path('add-specialization/', AddSpecializationAPIView.as_view(), name="add-specialization"),

    
    # referral and invitation 
    path('referral/generate/', GenerateReferralCodeView.as_view(), name='generate_referral'),
    path('invite/', InviteUserView.as_view(), name='invite_user'),
    path('referral/redeem/<str:invitation_code>/', redeem_invitation, name='redeem_invitation'),
    
    # Doctor's consultation settings
    path('consultation-settings/', ConsultationSettingsAPIView.as_view(), name='create_consultation_settings'),
    # Appointment preferences (Doctor sets availability)
    path('create-appointment-and-generate-slot/', AppointmentManagementAPIView.as_view(), name='appointment-preferences'),
    path('doctor-schedule/<int:doctor_id>/', AppointmentManagementAPIView.as_view(), name='doctor-schedule'),
    path('delete-appointment-and-generated-slot/', AppointmentManagementAPIView.as_view(), name='delete-preferences'),
    path("get-all-slots/", GetSlotsAPIView.as_view(), name="get-slots"),

    # Get All Day Slots for a Doctor
    # path("all-slots/", AllDaySlotsAPIView.as_view(), name="all-slots"),
    
    # Fetch available slots for a doctor based on settings
    # path('available-slots/', AvailableSlotsAPIView.as_view(), name='available-slots'),
    
    # Book an appointment (Patient)
    path('book-and-get-appointment/', BookAppointmentAPIView.as_view(), name='book-appointment'),
    path("patient-booked-appointment/", PatientAppointmentAPIView.as_view(), name="patient-appointment"),
    path("doctor-booked-appointment/", DoctorAppointmentAPIView.as_view(), name="doctor-appointment"),
    # View booked appointments
    # path("my-appointments/", MyAppointmentsAPIView.as_view(), name="my_appointments"),
    
    path("appointment/reschedule/", RescheduleAppointmentAPIView.as_view(), name="reschedule-appointment"),
    path("appointment/cancel/", CancelAppointmentAPIView.as_view(), name="cancel-appointment"),
    path("appointment/reminders/", AppointmentReminderAPIView.as_view(), name="appointment-reminders"),
    path("appointment/payment-confirmation/", PaymentConfirmationAPIView.as_view(), name="payment-confirmation"),
    path("appointment/create-checkout-session/", CreateStripeCheckoutSession.as_view(), name="payment-confirmation"),
    path("appointment-summary/<int:appointment_id>/", AppointmentSummaryAPIView.as_view(), name="payment-details"),
    path('refund-payment/',RefundAppointmentPaymentAPIView.as_view(), name="refund-payment"),

    path("payment-success/", PaymentSuccessView.as_view(), name="payment-success"),

    path('user-preferences/', UserPreferenceView.as_view(), name='user-preferences'),
    path('reschedule-policies/', ReschedulePolicyView.as_view(), name='reschedule-policy-list'),  # GET all, POST
    path('cancellation-policy/', CancellationPolicyView.as_view(), name='cancellation-policy'),
    path('no-show-policy/', NoShowPolicyAPIView.as_view(), name='no_show_policy'),
    path('communication-preferences/', CommunicationPreferencesAPIView.as_view(), name='communication-preferences'),
    
    # 2FA
    path('request-password-change/', RequestPasswordChangeAPIView.as_view(), name='request_otp'),
    path('verify-otp-change-password/', VerifyOTPAndChangePasswordAPIView.as_view(), name='verify_otp_change_password'),

    # Subsciption plan
    path('select-membership/', MembershipAPIView.as_view(), name='select-membership'),
    path('licence-certificate/', LicenceCertificateAPIView.as_view(), name='licence-certificate'),
    path("delete-document/", DeleteDocumentAPIView.as_view(), name='delete-document'),
    path("media-digest-document/", MediaDigestAPIView.as_view(), name="media-digest-document"),
    path("clinics-associated-to-doctors/", ClinicsAssociatedToDoctorsAPIView.as_view(), name="all-clinic-on-doctor"),
    path("patient-associated-to-doctors/", PatientsAssociatedToDoctorAPIView.as_view(), name="all-patient-on-doctor"),
    path('get-wallet/', DoctorWalletAPIView.as_view(), name='get-wallet'),

]
