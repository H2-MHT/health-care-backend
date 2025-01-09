from django.urls import path
from .views import StripePaymentAPIView

urlpatterns = [
    path('', StripePaymentAPIView.as_view(), name='stripe-payment'),
]
