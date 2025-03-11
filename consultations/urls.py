from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import PrescriptionPDFView, PrescriptionView, SpecificPrescriptionView

urlpatterns = [
    path('prescription/', PrescriptionView.as_view(), name='prescription'),
    path('prescription_template/', PrescriptionPDFView.as_view()),
    path('user-prescription/', SpecificPrescriptionView.as_view(), name='user-prescription'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
