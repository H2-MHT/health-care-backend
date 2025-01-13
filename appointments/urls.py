from django.urls import path
from .views import RescheduleAppointmentView, update_appointment_status, AppointmentAPIView, ChatAPIView, CallAPIView

urlpatterns = [
    path('<int:pk>/reschedule/', RescheduleAppointmentView.as_view(), name='reschedule-appointment'),
    path('update-appointment-status/', update_appointment_status, name='update_appointment_status'),
    path('api/appointments/', AppointmentAPIView.as_view()),
    path('api/chats/', ChatAPIView.as_view()),
    path('api/chats/<int:chat_id>/calls/', CallAPIView.as_view()),
]
