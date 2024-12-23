from django.urls import path

from dashboard.views import DashboardAPIView

urlpatterns = [
    # Define your URL patterns here, for example:
    path("", DashboardAPIView.as_view(), name="signup"),
]
