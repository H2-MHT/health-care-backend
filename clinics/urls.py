from django.urls import path
from clinics.views import *

urlpatterns = [
    path("clinic_register/", ClinicRegisterAPIView.as_view()),
    path("", ClinicAPIView.as_view()),
    path("public-clinic-list/", PublicClinicListAPIView.as_view()),
    path("clinic_info/", ClinicInfoAPIView.as_view()),
    path("clinic_detail/", PublicClinicDetailAPIView.as_view()),
    path("languages/", LanguageAPIView.as_view()),
    path("services_provided/", ServicesProvidedAPIView.as_view()),
    path("clinic-reviews/", ClinicReviewListCreateAPIView.as_view()),
    path("clinic-reviews/<int:review_id>/", ClinicReviewDetailAPIView.as_view()),
    path("clinic-reviews/<int:review_id>/replies/", ClinicReviewReplyListCreateAPIView.as_view()),
    path("clinic-reviews/stats/", ClinicReviewStatsAPIView.as_view()),
    path("active-doctors/", ActiveDoctorsAPIView.as_view()),
    path("appointments/stats/", ClinicAppointmentStatsView.as_view()),
    path("appointments/activity/", ClinicAppointmentActivityView.as_view()),
    path("doctors/", ClinicDoctorsAPIView.as_view()),
    path("doctor-report/", ClinicReportRemoveDoctorAPIView.as_view()),
    path("doctor-remove/<int:doctor_id>/", ClinicReportRemoveDoctorAPIView.as_view()),
    path("calendar-appointments/", ClinicCalendarAppointmentsAPIView.as_view()),
    path("doctor-associated-to-clinic/", DoctorAssociatedToClinicListAPIView.as_view()),
    path('address/', ClinicAddressAPIView.as_view(), name='clinic-address-list')
]
