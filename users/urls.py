from django.urls import path
from .views import UpdateEducationAPIView

urlpatterns = [
        path('update-education/<int:user_id>/', UpdateEducationAPIView.as_view(), name='update-education'),
        path('get-education/<int:user_id>/', UpdateEducationAPIView.as_view(), name=' view-education'),
]
