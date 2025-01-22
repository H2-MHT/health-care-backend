from django.urls import path
from .views import (
    StripePaymentAPIView,
    TransactionHistoryAPIView,
    AddAccountDetailAPIView,
)

urlpatterns = [
    path('', StripePaymentAPIView.as_view(), name='stripe-payment'),
    # transactions history 
    path("transactions/", TransactionHistoryAPIView.as_view(), name="transactions"),
    # add account information
    path('add-account-detail/', AddAccountDetailAPIView.as_view(), name='add-account-detail'),
    # view account information
    path('account-detail/', AddAccountDetailAPIView.as_view(), name='view-account-detail'),
]
