from django.shortcuts import render

# Create your views here.

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import stripe
from django.conf import settings
from .models import Payment
from appointments.models import Appointment

# Stripe secret key
stripe.api_key = settings.STRIPE_SECRET_KEY

class StripePaymentAPIView(APIView):
    """
    Stripe payment using PaymentIntent.
    """

    def post(self, request, *args, **kwargs):
        try:
            # Get data from the request
            test_token = request.data.get('test_token')
            amount = request.data.get('amount')
            appointment_id = request.data.get('appointment_id')

            if not test_token or not amount or not appointment_id:
                return Response(
                    {"error": "Missing required fields: 'test_token', 'amount', or 'appointment_id'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # get the appointment
            try:
                appointment = Appointment.objects.get(id=appointment_id)
            except Appointment.DoesNotExist:
                return Response({"error": "Appointment not found."}, status=status.HTTP_404_NOT_FOUND)

            # Create a PaymentIntent
            intent = stripe.PaymentIntent.create(
                amount=int(float(amount) * 100),  # dollars to cents
                currency="usd",
                payment_method=test_token,
                confirm=True,
                description=f"Payment for Appointment {appointment.id}",
                automatic_payment_methods={
                    "enabled": True,
                    "allow_redirects": "never"
                }
            )
            print(intent, '------------------INTENT')
            # Save payment details
            Payment.objects.create(
                appointment=appointment,
                amount=amount,
                total_amount=amount,
                method=intent.get("payment_method_types", ["unknown"])[0],
                status=intent.get("status", "unknown"),
            )

            return Response(
                {"message": "Payment successful!", "clientSecret": intent['id'], "status": intent['status']},
                status=status.HTTP_200_OK,
            )

        except stripe.error.CardError as e:
            return Response(
                {"error": "Card declined", "message": e.user_message},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": "Payment failed", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )