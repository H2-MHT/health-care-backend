from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import(
    PrescriptionPDFView,
    PrescriptionView,
    PrescriptionListView,
    ConsultationReportAPIView,
)

urlpatterns = [
    path('prescription/', PrescriptionView.as_view(), name='prescription'),
    path('prescription_template/', PrescriptionPDFView.as_view(), name='prescription_template'),
    path('prescription-list/', PrescriptionListView.as_view(), name='prescription-list'),
    path("consultation-report/", ConsultationReportAPIView.as_view(), name="consultation-report"),
    path("update-consultation-report/", ConsultationReportAPIView.as_view(), name="update-consultation-report"),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
