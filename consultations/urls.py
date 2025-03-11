from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from .views import PrescriptionPDFView, PrescriptionView, PrescriptionListView

urlpatterns = [
    path('prescription/', PrescriptionView.as_view(), name='prescription'),
    path('prescription_template/', PrescriptionPDFView.as_view()),
    path('prescription-list/', PrescriptionListView.as_view(), name='prescription-list'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
