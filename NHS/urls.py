# urls.py

from django.urls import path
from .views import NHSAPIResourceAPIView

urlpatterns = [
    path("api/", NHSAPIResourceAPIView.as_view(), name="nhs-condition"),
]
