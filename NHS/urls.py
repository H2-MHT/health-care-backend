# urls.py

from django.urls import path
from .views import(
    NHSSymptomAPIView,
    NHSAPIResourceAPIView,
)

urlpatterns = [
    path("api/", NHSAPIResourceAPIView.as_view(), name="nhs-condition"),
    path("symptoms/", NHSSymptomAPIView.as_view(), name="nhs-symptoms"),
]
