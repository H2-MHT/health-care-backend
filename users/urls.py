from django.urls import path
from .views import EducationAPIView, UpdateEducationAPIView, SelectMethodsAPIView, AvailableMethodsAPIView, ViewSkills

urlpatterns = [
        path('education/', EducationAPIView.as_view(), name='add-education'),
        path('skills/', ViewSkills.as_view(), name='add-education'),
        path('education/<int:education_id>/', UpdateEducationAPIView.as_view(), name='update-education'),

        # 2FA
        path('select-methods/', SelectMethodsAPIView.as_view(), name='select_2fa_method'),
        path('all-methods/', AvailableMethodsAPIView.as_view(), name='available_2fa_method'),
]
