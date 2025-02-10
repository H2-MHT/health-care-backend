from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from consultations.views import send_prescription_email

urlpatterns = [
    path('prescription_template/', send_prescription_email),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
