from django.urls import path
from .views import (
    StripePaymentAPIView,
    TransactionHistoryAPIView,
    AddAccountDetailAPIView,
    WithdrawalAPIView,
    StripeConnectAPIView,
    StripeWebhookView
)

urlpatterns = [
    path('', StripePaymentAPIView.as_view(), name='stripe-payment'),
    # transactions history 
    path("transactions/", TransactionHistoryAPIView.as_view(), name="transactions"),
    # add account information
    path('add-account-detail/', AddAccountDetailAPIView.as_view(), name='add-account-detail'),
    # view account information
    path('withdrawal-request/', WithdrawalAPIView.as_view(), name='withdrawal-request'),
    # stripe connnect
    path('stripe-connect/', StripeConnectAPIView.as_view(), name='stripe-connect'),
    # webhook-stripe
    path('stripe-webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
]
