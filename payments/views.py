# Create your views here.

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import stripe
from django.conf import settings
from .models import Payment, User
from appointments.models import Appointment
from rest_framework.permissions import IsAuthenticated
from doctors.models import Doctor
from .serializers import AccountDetailSerializer, TransactionSerializer
from .models import AccountDetail, Transaction

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
            payment_method_types = request.data.get('payment_method_types')
            description = request.data.get('description')
            
            # Validate required fields
            if not test_token or not amount or not appointment_id or not payment_method_types:
                return Response(
                    {
                        "error": "Missing required fields",
                        "message": "'test_token', 'amount', 'appointment_id', and 'payment_method_types' are required.",
                    },
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
                description=description or f"Payment for Appointment {appointment.id}",
                payment_method_types=payment_method_types,
            )
            print(intent, '------------------INTENT')
            # Save payment details
            Payment.objects.create(
                appointment=appointment,
                amount=amount,
                total_amount=amount,
                method=intent.get("payment_method_types", ["unknown"])[0],
                status=intent.get("status", "unknown"),
                payment_notes=intent.get("description"),
            )

            return Response(
                {
                    "message": "Payment successful!",
                    "payment_intent_id": intent['id'],
                    "status": intent['status'],
                    "payment_method": intent['payment_method'],
                    "payment_method_type": intent['payment_method_types'],
                    "amount": amount,
                    "payment_notes": intent.description,
                    "clientSecret": intent.client_secret,
                    },
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
                status=status.HTTP_400_BAD_REQUEST,
            )
            
            
class TransactionHistoryAPIView(APIView):
    """
    API to fetch transaction history and include total, clinic charges, final amount,
    and current balance after clinic charge deductions.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            # Ensure the logged-in user is a doctor
            if request.user.role != "Doctor":
                return Response(
                    {"error": "You are not authorized to view this information."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Fetch the doctor instance linked to the logged-in user
            try:
                doctor = request.user.doctor
            except Doctor.DoesNotExist:
                return Response(
                    {"error": "Doctor profile not found for the current user."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Fetch transactions associated with this doctor
            transactions = Payment.objects.filter(
                appointment__doctor=doctor
            ).select_related("appointment", "appointment__patient")

            # Clinic charge deduction
            clinic_charge = 4.8

            # Calculate total balance and current balance
            total_balance = sum([transaction.amount for transaction in transactions])  # Total before deductions
            final_amounts = [float(transaction.amount) - clinic_charge for transaction in transactions]  # After clinic charge deductions
            total_final_amount = sum(final_amounts)  # Final amount after deductions

            # Serialize transactions and apply the clinic charge deduction
            transaction_data = [
                {
                    "sender": f"{transaction.appointment.patient.user.first_name} {transaction.appointment.patient.user.last_name}",
                    "date": transaction.timestamp,
                    "total": float(transaction.amount),  # The total amount from the payment
                    "clinic_charge": clinic_charge,  # The clinic charge field
                    "final_amount": round(float(transaction.amount) - clinic_charge, 2),  # Deduct the clinic charge to get the final amount
                    "description": transaction.payment_notes or f"Payment for Appointment {transaction.appointment.id}",
                    "status": transaction.status,
                }
                for transaction in transactions
            ]

            # response with transactions and balance information
            return Response(
                {
                    "transactions": transaction_data,
                    "total_balance": total_balance,  # The sum of total amounts before deductions
                    "current_balance": total_final_amount,  # The sum of amounts after clinic charge deductions
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"error": "An error occurred.", "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

class AddAccountDetailAPIView(APIView):
    """
    API to allow doctors to add their account details.
    Only authenticated doctors can add their own details.
    A doctor can add multiple accounts with unique account numbers.
    """
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        try:
            # Ensure the user is a doctor
            if not hasattr(request.user, 'doctor'):
                return Response(
                    {"error": "Only doctors can add account details."},
                    status=status.HTTP_403_FORBIDDEN
                )
            # Check if the account already exists
            account_number = request.data.get('account_number')
            account = AccountDetail.objects.filter(user=request.user, account_number=account_number).first()
            
            if account:
                # Create a transaction record for the existing account
                transaction=Transaction.objects.create(
                    account=account,
                    transaction_type="Withdrawal",
                    amount=request.data.get('amount'),
                )
                transaction_serializer = TransactionSerializer(transaction)
                return Response(
                    {
                        "message": "Transaction recorded successfully.",
                        "data": transaction_serializer.data
                        },
                    status=status.HTTP_200_OK
                )
            
            # Create a new account if it doesn't exist
            serializer = AccountDetailSerializer(data=request.data)
            if serializer.is_valid():
                account = serializer.save(user=request.user)
                # Optionally create a transaction for the new account
                Transaction.objects.create(
                    account=account,
                    transaction_type="Withdrawal",
                    amount=request.data.get('amount'),
                )
                return Response(
                    {
                        "message": "Account detail added successfully.", 
                        "data": serializer.data
                    },
                    status=status.HTTP_200_OK
                )
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
    def get(self, request, *args, **kwargs):
        """
        Fetch all account details for the current logged-in doctor.
        """
        try:
            if request.user.role in ['Doctor', 'SuperAdmin']:
                user_id = request.query_params.get("user_id")

                if not user_id:
                    return Response({"error": "User ID is required"}, status=status.HTTP_400_BAD_REQUEST)
                
                user = User.objects.filter(pk=user_id).first()
                if not user:
                    return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

                if request.user.role == 'Doctor' and request.user.id != user.id:
                    return Response({"error": "only associated doctor to access this data"}, status=status.HTTP_403_FORBIDDEN)

                transaction = Transaction.objects.filter(account__user=user)
                transaction_serializer = TransactionSerializer(transaction, many=True)
                return Response(
                    {
                        "message": "Doctor Account details fetched successfully.",
                        # "accounts": account_serializer.data,
                        "transactions": transaction_serializer.data
                    },status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )