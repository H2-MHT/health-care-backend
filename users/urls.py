from django.urls import path
from .views import EducationAPIView

urlpatterns = [
    path('add_education/', EducationAPIView.as_view(), name='education-api'),
]
