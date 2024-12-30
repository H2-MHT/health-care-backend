from django.urls import path
from .views import reschedule_appointment, update_appointment_status

urlpatterns = [
    path('<int:appointment_id>/reschedule/', reschedule_appointment, name='reschedule-appointment'),
    path('update-appointment-status/', update_appointment_status, name='update_appointment_status'),
]
