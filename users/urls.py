from django.urls import path
from .views import(EducationAPIView,
                UpdateEducationAPIView, 
                SelectMethodsAPIView,
                AvailableMethodsAPIView,
                ViewSkills,
                NotesAPIView,
                DeviceAccessListCreateAPIView,
)

urlpatterns = [
        path('education/', EducationAPIView.as_view(), name='add-education'),
        path('skills/', ViewSkills.as_view(), name='add-education'),
        path('education/<int:education_id>/', UpdateEducationAPIView.as_view(), name='update-education'),

        # 2FA
        path('select-methods/', SelectMethodsAPIView.as_view(), name='select_2fa_method'),
        path('all-methods/', AvailableMethodsAPIView.as_view(), name='available_2fa_method'),
        
        # notes
        path("notes/", NotesAPIView.as_view(), name="notes-list-create"),
        path("notes/<int:pk>/", NotesAPIView.as_view(), name="notes-detail"),
        path('device-access/', DeviceAccessListCreateAPIView.as_view(), name='device-access-list-create'),

]
