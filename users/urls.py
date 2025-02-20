from django.urls import path
from .views import UpdateEducationAPIView, SelectMethodsAPIView, AvailableMethodsAPIView

urlpatterns = [
        path('update-education/<int:user_id>/', UpdateEducationAPIView.as_view(), name='update-education'),
        path('get-education/<int:user_id>/', UpdateEducationAPIView.as_view(), name=' view-education'),
        
        # 2FA
        path('select-methods/', SelectMethodsAPIView.as_view(), name='select_2fa_method'),
        path('all-methods/', AvailableMethodsAPIView.as_view(), name='available_2fa_method'),
]
