from django.urls import path

from .views import(
    TotalPatientAndDoctorsView,
    PatientListCreateAPIView,
    PatientRetrieveUpdateDeleteAPIView,
    PatientBlockUnblockAPIView,
    DoctorManagementView,
    DoctorBlockUnblockView,
    UserListAPIView,
    DetailOfUser,
    BlockUser,
    DeleteUser,
    DoctorWithdrawAPIView,
    VerifyDocumentAPIView,
    ReviewReportAPIView,
    ApproveSpecialization,
    MergeSpecialization,
    NewSpecializationAPIView,
    AdminWithdrawalRequestAPIView,
    ExportDataAPIView,
    DepartmentAPIView,
    DoctorStripeLinkAddView,
    ReviewApproveView,
    ReplyApproveView,
    CloseDiscussionAPIView,
    DeleteInappropriateReviewOrReplyView,
    CreateAdminAPIView,
    RevenueAPIView,
    PastAndAUpcomingAppointmentsAPIView,
    AdminSupportTicketAPIView,
    DoctorCountFromClinicAPIView,
    ConsultationReportListAPIView,
    ConsultationReportDownloadAPIView
)

urlpatterns = [
    # Define your URL patterns here, for example:
    path("total-count/", TotalPatientAndDoctorsView.as_view(), name="total-count"),
    # path("total-patient/", Patient_Record.as_view(), name="taker_get"),
    # path("patient-post/", Patient_Record.as_view(), name="taker_get"),
    # path("patient-put/<int:pk>/",Patient_Record.as_view(), name="taker_get"),
    # path("patient-delete/<int:pk>/", Patient_Record.as_view(), name="taker_delete"),
    # path("patient-search/", PatientSearchView.as_view(), name="patient-search"),
    # path("patient-filter/",PatientFilterView.as_view(), name="patient-filter"),


    # path("total-doctor/", Doctor_Record.as_view(), name="taker_get"),
    # path("doctor-post/", Doctor_Record.as_view(), name="taker_get"),
    # path("doctor-put/<int:pk>/",Doctor_Record.as_view(), name="taker_get"),
    # path("doctor-delete/<int:pk>/", Doctor_Record.as_view(), name="tooker_delete"),
    # path("doctor-search/", DoctorSearchView.as_view(), name="doctor-search"),
    # path("doctor-filter/", DoctorFilterView.as_view(), name="doctor-filter"),

    # path("status_user/", StatusUser.as_view(), name="status_user"),
    # path("block-user/<int:id>/", BlockuserAPI.as_view(), name="status_user"),

    # path("search_doctor/", SearchDoctorByName.as_view(), name="search_doctor"),

    # Manage Patient
    path("patients/", PatientListCreateAPIView.as_view(), name="patient-list-create"),
    path("patients/<int:pk>/", PatientRetrieveUpdateDeleteAPIView.as_view(), name="patient-detail"),
    path("patients/block-unblock/<int:pk>/", PatientBlockUnblockAPIView.as_view(), name="patient-block-unblock"),
    
    # Mange Doctor
    path("doctors/", DoctorManagementView.as_view(), name="manage-doctors"),
    path("doctors/<int:doctor_id>/", DoctorManagementView.as_view(), name="edit-doctor"),
    path("doctors/<int:doctor_id>/block-unblock/", DoctorBlockUnblockView.as_view(), name="block-unblock-doctor"),


    path("user_list/",  UserListAPIView.as_view(), name="user_list"),
    path("user_detail/<int:pk>/",  DetailOfUser.as_view(), name="user_detail"),
    path("user_block/<int:id>/", BlockUser.as_view(), name="user_block"),
    path("user_delete/<int:pk>/", DeleteUser.as_view(), name="user_delete"),
    path("get-accounts/", DoctorWithdrawAPIView.as_view(), name='get-accounts'),
    path("approv-reject-payment/", DoctorWithdrawAPIView.as_view(), name="approv-reject-payment"),
    path("verify-document/", VerifyDocumentAPIView.as_view(), name="verify-document"),
    path("get-report/", ReviewReportAPIView.as_view(), name="get-report"),
    path("review-report/", ReviewReportAPIView.as_view(), name="review-report"),
    # add new specialization by admin
    path('specialization/', NewSpecializationAPIView.as_view(), name='specialization'),
    # approve specialization added by doctor from admin side
    path('approve-specialization/', ApproveSpecialization.as_view(), name="approve-specialization"),
    path('merge-specialization/', MergeSpecialization.as_view(), name="merge-specialization"),
    # withdrawal request 
    path('withdrawal-request/', AdminWithdrawalRequestAPIView.as_view(), name='withdrawal-request'),
    path('export-data/', ExportDataAPIView.as_view(), name='export-data'),
    # department
    path('department/', DepartmentAPIView.as_view(), name='department'),
    # add stripe link on doctor profile
    path("add-stripe-link/", DoctorStripeLinkAddView.as_view(), name="add-stripe-link"),
    # review
    path('approve-review/', ReviewApproveView.as_view(), name="approve-review"),
    path('approve-reply/', ReplyApproveView.as_view(), name="approve-reply"),
    path('close-discussion/', CloseDiscussionAPIView.as_view(), name="close-discussion"),
    path('delete-inappropriate/', DeleteInappropriateReviewOrReplyView.as_view(), name="delete-inappropriate"),
    path("admin-account/", CreateAdminAPIView.as_view(), name="admin-account"),
    path('revenue/', RevenueAPIView.as_view(), name="revenue"),
    path('past-upcoming-appointments/', PastAndAUpcomingAppointmentsAPIView.as_view(), name="past-and-upcoming-appointments"),
    
    path('all-support/', AdminSupportTicketAPIView.as_view(), name='admin-support-list'),
    path('doctor-count-from-clinic/', DoctorCountFromClinicAPIView.as_view(), name="patient-count-from-clinic"),
    path('consultation-report-list/', ConsultationReportListAPIView.as_view(), name="consultation-report-list"),
    path('consulation-report-download/<int:pk>/',  ConsultationReportDownloadAPIView.as_view(), name="consultation-report-download"),

]