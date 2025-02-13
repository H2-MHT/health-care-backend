from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import PrescriptionPDFView

urlpatterns = [
    path('prescription_template/', PrescriptionPDFView.as_view()),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
