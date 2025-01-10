from django.urls import path
from .views import (
    StripePaymentAPIView,
    TransactionHistoryAPIView,
)

urlpatterns = [
    path('', StripePaymentAPIView.as_view(), name='stripe-payment'),
    path("transactions/", TransactionHistoryAPIView.as_view(), name="transactions"),
]
