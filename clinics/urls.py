from django.urls import path
from clinics.views import *

urlpatterns = [
    path("clinic_register/", ClinicRegisterAPIView.as_view()),
    path("", ClinicAPIView.as_view()),
    path("clinic_info/", ClinicInfoAPIView.as_view()),
    path("languages/", LanguageAPIView.as_view()),
    path("services_provided/", ServicesProvidedAPIView.as_view()),
    path("clinic-reviews/", ClinicReviewListCreateAPIView.as_view(), name="clinic_reviews"),
    path("clinic-reviews/<int:review_id>/", ClinicReviewDetailAPIView.as_view(), name="clinic_review_detail"),
    path("clinic-reviews/<int:review_id>/replies/", ClinicReviewReplyListCreateAPIView.as_view(), name="clinic_review_replies"),
    path("clinic-reviews/stats/", ClinicReviewStatsAPIView.as_view(), name="clinic_review_stats"),
    path("active-doctors/", ActiveDoctorsAPIView.as_view(), name="active_doctors"),
]
