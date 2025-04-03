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
)

urlpatterns = [
    # Define your URL patterns here, for example:
    path("total-count/", TotalPatientAndDoctorsView.as_view(), name="signup"),
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
]