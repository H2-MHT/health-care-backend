from django.urls import path
from .views import(
    PatientListView,
    PatientDashboardAPIView,
)

urlpatterns = [
    path('', PatientListView.as_view()),
    path('patient-dashboard', PatientDashboardAPIView.as_view()),
]