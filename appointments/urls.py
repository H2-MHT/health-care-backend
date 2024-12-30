from django.urls import path
from .views import reschedule_appointment

urlpatterns = [
    path('<int:appointment_id>/reschedule/', reschedule_appointment, name='reschedule-appointment'),
]
