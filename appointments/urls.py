from django.urls import path
from .views import RescheduleAppointmentView, update_appointment_status

urlpatterns = [
    path('<int:pk>/reschedule/', RescheduleAppointmentView.as_view(), name='reschedule-appointment'),
    path('update-appointment-status/', update_appointment_status, name='update_appointment_status'),
]
