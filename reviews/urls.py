# urls.py
from django.urls import path
from .views import DoctorReviewsAPIView

urlpatterns = [
    path('doctor/<int:doctor_id>/', DoctorReviewsAPIView.as_view(), name='doctor-reviews'),
]
