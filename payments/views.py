# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import stripe
from django.conf import settings
from .models import Payment, User
from doctors.models import DoctorWallet
from appointments.models import Appointment
from rest_framework.permissions import IsAuthenticated
from doctors.models import Doctor
from .serializers import AccountDetailSerializer, TransactionSerializer
from .models import AccountDetail, Transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import os
import uuid
from datetime import datetime, timedelta, date
from django.utils import timezone
import random 
import string
from weasyprint import HTML
from django.template.loader import render_to_string
from django.http import HttpResponse 
from io import BytesIO
from django.core.files.base import ContentFile
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, Attachment, FileContent, FileType, FileName, Disposition
import base64
from utils.prescription_translation import translate_invoice
from users.models import AppLanguage
from doctors.models import BookedAppointment, UserPreference
from utils.whatsapp import (
    send_whatsapp_message_patient,
    send_whatsapp_message_doctor,
)
from utils.notifications import send_notification
from pytz import timezone as pytz_timezone
import pytz
import logging

logger = logging.getLogger(__name__)
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
            if not hasattr(request.user, 'doctor'):
                return Response(
                    {"error": "Only doctors can add account details."},
                    status=status.HTTP_403_FORBIDDEN
                )
            account_number = request.data.get('account_number')
            account = AccountDetail.objects.filter(user=request.user, account_number=account_number).first()
            
            if account:
                return Response(
                    {"error":"This account number is already added"},
                    status=status.HTTP_400_BAD_REQUEST)

            serializer = AccountDetailSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(user=request.user)
                return Response(
                    {
                        "message": "Account details added successfully.",
                        "data": serializer.data
                        },
                    status=status.HTTP_201_CREATED
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

                accounts = AccountDetail.objects.filter(user=user)
                account_serializer = AccountDetailSerializer(accounts, many=True)
                return Response(
                    {
                        "message": "Doctor Account details fetched successfully.",
                        "accounts": account_serializer.data,
                    },status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


def generate_invoice_pdf(template_path: str, context: dict, request) -> tuple:
    html_string = render_to_string(template_path, context)
    pdf_file = BytesIO()

    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(pdf_file)

    folder_path = os.path.join(settings.MEDIA_ROOT, 'invoices')
    os.makedirs(folder_path, exist_ok=True)

    filename = f"invoice_{context['reference']}.pdf"
    file_path = os.path.join(folder_path, filename)

    with open(file_path, 'wb') as f:
        f.write(pdf_file.getvalue())

    media_url = f"{settings.MEDIA_URL}invoices/{filename}"
    return pdf_file.getvalue(), media_url

def generate_invoice(request, withdrawal, reference):
    context = {
        'reference': reference,
        'doctor_id': str(withdrawal.account.user.id),
        'doctor_name': withdrawal.account.user.get_full_name(),
        'date': withdrawal.timestamp.strftime('%d-%b-%Y'),
        'amount': str(withdrawal.amount),
        'account_no': str(withdrawal.account.account_number),
        'ifsc': withdrawal.account.ifsc_code,
        'bank_name': withdrawal.account.bank_name,
        'withdrawal': "Doctor Withdrawal Invoice",
        'Reference_No': "Reference Number",
        'Doctor_ID': "Doctor ID",
        'Doctor_Name': "Doctor Name",
        'Date_of_Request': "Date of Request",
        'Amount': "Amount",
        'bank': "Bank_Name",
        'Account_No': "Account No",
        'IFSC_Code': "IFSC Code",
        'note': "Note: Processing may take up to 5 working days.",
        'service': "Thank you for using our services."      
    }
    
    try:
        doctor = User.objects.get(id=int(context['doctor_id']))
    except User.DoesNotExist:
        pass
    
    try:
        language = AppLanguage.objects.get(user=doctor)
        lang_code = language.code
    except AppLanguage.DoesNotExist:
        lang_code = "en"
    
    context = translate_invoice(context, lang_code)
    pdf_bytes, pdf_url = generate_invoice_pdf("invoice.html", context, request)
    return pdf_bytes, pdf_url

def generate_reference():
    date_part = datetime.now().strftime("%Y%m%d")
    random_part = ''.join(random.choices(string.digits, k=5))  
    return f"HC-{date_part}-{random_part}"

def send_invoice_email(transaction, doctor_email, request):
    try:
        invoice_bytes, invoice_url = generate_invoice(request, transaction, transaction.reference)
        encoded_invoice = base64.b64encode(invoice_bytes).decode()

        doctor_message = Mail(
            from_email=settings.SENDGRID_FROM_EMAIL,
            to_emails=doctor_email,
            subject="Your Invoice",
            plain_text_content="Please find the attached invoice."
        )

        attachment = Attachment(
            FileContent(encoded_invoice),
            FileName(os.path.basename(invoice_url)),
            FileType('application/pdf'),
            Disposition('attachment')
        )
        doctor_message.attachment = attachment

        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        sg.send(doctor_message)

        try: 
            user = User.objects.get(pk=transaction.account.user.id)
        except User.DoesNotExist:
            user = ""
        
        doctor = Doctor.objects.get(user=user)
             
        admin_email = settings.ADMIN_EMAIL
        profile_id = transaction.account.user.uid
        doctor_name = transaction.account.user.get_full_name()
        specialty = doctor.specialty
        hourly_rate = doctor.urgent_hourly_rate
        currency = transaction.account.user.currency
        commission = round(transaction.amount * 0.10, 2)
        earnings = round(transaction.amount - commission, 2)

        admin_body = f"""Dear Admin,

A new Doctor Payment Form (DPF) request has been submitted. Below are the details for your action:

Doctor Details:
Profile ID: {profile_id}
Name: {doctor_name}
Specialty: {specialty}
Hourly Rate: {hourly_rate} {currency}
Currency: {currency}

Payment Breakdown:
Platform Commission (10%): {commission} {currency}
Doctor’s Earning per Consultation: {earnings} {currency}

Action Required:
Please generate the Doctor Payment Form and add it to the system. Once completed, notify the doctor and provide access to their updated profile.
"""

        admin_message = Mail(
            from_email=settings.SENDGRID_FROM_EMAIL,
            to_emails=admin_email,
            subject=f"[DPF-Request-{profile_id}] Doctor Payment Form Request - {doctor_name}",
            plain_text_content=admin_body
        )
        sg.send(admin_message)

        return "Emails sent successfully."

    except Exception as e:
        return str(e)
    finally:
        if os.path.exists(invoice_url):
            os.remove(invoice_url)


class WithdrawalAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user_id = request.data.get('user_id')
            account_number = request.data.get('account_number')
            full_name = request.data.get('full_name')
            amount = request.data.get('amount')

            if not all([user_id, account_number, full_name, amount]):
                return Response(
                    {"error": "user_id, account_number, full_name, and amount are required."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                user_id = int(user_id)
            except ValueError:
                return Response({"error": "Invalid user_id format."}, status=status.HTTP_400_BAD_REQUEST)

            if request.user.id != user_id:
                return Response(
                    {"error": "Authenticated user does not match the doctor_id provided."},
                    status=status.HTTP_403_FORBIDDEN
                )

            account = AccountDetail.objects.filter(
                user__id=user_id,
                account_number=account_number.strip(), 
                full_name__istartswith=full_name.strip()
            ).first()
            
            if not account:
                print(f"Account not found! Available accounts: {AccountDetail.objects.filter(user__id=user_id).values_list('account_number', 'full_name')}")
                return Response(
                    {"error": "Account not found for the given doctor details."},
                    status=status.HTTP_404_NOT_FOUND
                )
            # if not account.stripe_account_id:
            #     return Response({"error": "Stripe account not found for the given doctor details."}, status=status.HTTP_400_BAD_REQUEST)
            
            user = request.user
            try:
                wallet = DoctorWallet.objects.get(doctor=user)
            except DoctorWallet.DoesNotExist:
                return Response({"error": "Doctor wallet not found."}, status=status.HTTP_404_NOT_FOUND)
            
            walletAmount  = wallet.balance
            
            if amount > walletAmount:
                return Response({"error": "Insufficient balance."}, status=status.HTTP_400_BAD_REQUEST)
            
            if amount <= 0:
                return Response({"error": "Invalid amount."}, status=status.HTTP_400_BAD_REQUEST)
        
            try: 
                # price = stripe.Price.create(
                #     unit_amount=int(amount * 100),
                #     currency=user.currency.lower(), 
                #     product_data={
                #         "name": f"Doctor Payment: {account.full_name}",
                #     }
                # )
                # payment_intent_id = str(uuid.uuid4())
                # payment_link = stripe.PaymentLink.create(
                #     line_items=[{
                #         "price": price.id,
                #         "quantity": 1, 
                #     }],
                #     after_completion={
                #         "type": "redirect",
                #         "redirect": {
                #             "url": "https://h2.doctor/superadmin/managepayment"
                #         },
                #     },
                #     transfer_data={
                #         "destination": account.stripe_account_id 
                #     },
                #     metadata={"payment_link_id": payment_intent_id}
                # )
    
                wallet.balance -= amount
                wallet.save()
                
                transaction = Transaction.objects.create(
                account=account,
                transaction_type="Withdrawal",
                amount=amount,
                status="pending",
                 # stripe_payment_link = payment_link.url,
                # stripe_payment_link_id = payment_intent_id    
                )
                reference = generate_reference() 
                invoice_bytes, invoice_url  = generate_invoice(request, transaction, reference)
                transaction.reference = reference
                transaction.invoice.save(
                    f"invoice_{reference}.pdf",
                    ContentFile(invoice_bytes)
                )
                transaction.save()
                recepient_email = transaction.account.user.email
                send_invoice_email(transaction, recepient_email, request)
                
                transaction_serializer = TransactionSerializer(transaction)    
                return Response(
                {
                    "message": "Withdrawal request submitted successfully.",
                    "data": transaction_serializer.data,
                    "referal_no": reference,
                    "invoice": transaction.invoice.url
                },
                status=status.HTTP_201_CREATED)
    
            except stripe.error.StripeError as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
    def get(self, request):
        try:
            user_id = request.user.id
            
            transactions = Transaction.objects.filter(
                account__user_id=user_id,
                transaction_type="Withdrawal"
            ).order_by('-timestamp')
            
            if not transactions.exists():
                return Response(
                    {"message": "No withdrawal transactions found."},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            transaction_serializer = TransactionSerializer(transactions, many=True)
            return Response(
                {
                    "message": "Withdrawal transactions fetched successfully.",
                    "data": transaction_serializer.data
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class StripeConnectAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        account_detail, _ = AccountDetail.objects.get_or_create(user=user)

        if account_detail.stripe_account_id:
            return Response({
                "message": "Stripe account already exists",
                "stripe_account_id": account_detail.stripe_account_id
            }, status=status.HTTP_200_OK)


        try:
            capabilities = {
            "transfers": {"requested": True}
            }

            if user.country.upper() == "US":
                capabilities["card_payments"] = {"requested": True}
                
            account = stripe.Account.create(
                type="express",
                country=user.country,
                email=user.email,
                capabilities=capabilities
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

        account_detail.stripe_account_id = account.id
        account_detail.save()

        try:
            account_link = stripe.AccountLink.create(
                account=account.id,
                refresh_url="https://h2.doctor/dashboard",  
                return_url=f"https://h2.doctor/dashboard",
                type="account_onboarding"
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": "Stripe account created successfully",
            "onboarding_url": account_link.url
        }, status=status.HTTP_201_CREATED)
        
    def get(self, request):
        user = request.user

        try:
            account_detail = AccountDetail.objects.get(user=user)

            if not account_detail.stripe_account_id:
                return Response({"error": "Stripe account not found."}, status=400)

            login_link = stripe.Account.create_login_link(account_detail.stripe_account_id)

            return Response({
                "login_url": login_link.url
            })

        except AccountDetail.DoesNotExist:
            return Response({"error": "Account details not found."}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
 
class TransactionHistory(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            user = request.user  
            if user.role == "Patient":
                transactions = Payment.objects.filter(appointment__patient=user.id)
                payment = []
                for transaction in transactions:
                    doctor = User.objects.get(pk=transaction.appointment.doctor)
                    patient = User.objects.get(pk=transaction.appointment.patient)
                    
                    data = {
                        "id": transaction.id,
                        "appointment_id": transaction.appointment.id,
                        "appointment_date": datetime.strftime(transaction.appointment.date, "%d/%m/%Y"),
                        "appointment_status": transaction.appointment.status,
                        "doctor":{
                            "id":doctor.id,
                            "name": doctor.get_full_name(),
                            "email": doctor.email
                            },
                        "patient": {
                            "id":patient.id,
                            "name": patient.get_full_name(),
                            "email": patient.email
                            },
                        "amount": transaction.amount,
                        "currency": patient.currency if patient.currency else "USD",
                        "payment_status": transaction.appointment.payment_status,
                        "payment_method": transaction.method,
                        "payment_date": datetime.strftime(transaction.timestamp, "%d/%m/%Y")
            
                    }
                    payment.append(data)
                
            elif request.user.role == "Doctor":
                transactions = Payment.objects.filter(appointment__doctor=user.id)
                payment = []
                for transaction in transactions:
                    doctor = User.objects.get(pk=transaction.appointment.doctor)
                    patient = User.objects.get(pk=transaction.appointment.patient)
                    
                    data = {
                        "id": transaction.id,
                        "appointment_id": transaction.appointment.id,
                        "appointment_date": datetime.strftime(transaction.appointment.date, "%d/%m/%Y"),
                        "appointment_status": transaction.appointment.status,
                        "doctor":{
                            "id":doctor.id,
                            "name": doctor.get_full_name(),
                            "email": doctor.email
                            },
                        "patient": {
                            "id":patient.id,
                            "name": patient.get_full_name(),
                            "email": patient.email
                            },
                        "amount": transaction.amount,
                        "currency": patient.currency if patient.currency else "USD",
                        "payment_status": transaction.appointment.payment_status,
                        "payment_method": transaction.method,
                        "payment_date": datetime.strftime(transaction.timestamp, "%d/%m/%Y")
            
                    }
                    payment.append(data)
            
            else:
                return Response({"error": "You are not authorized to access this"}, status=status.HTTP_400_BAD_REQUEST)
                
            return Response({"message": "Transaction history retrieved successfully", "data":payment})
        except Exception as e:
            return Response({"error": str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class WebhookAPI(APIView):
    def post(self, request):
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY_TEST')
        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
        endpoint_secret = os.getenv('WEBHOOK_KEY_TEST') 
        
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError:
            return Response({"error": "Invalid payload"}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError:
            return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)
        
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            metadata = session.get('metadata', {})
            appointment_id = metadata.get('appointment_id')
            payment_intent_id = session.get('payment_intent')
            
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

            try:
                appointment = BookedAppointment.objects.get(id=appointment_id)
                appointment.payment_status = "Completed"
                appointment.status = 'Pending'
                appointment.payment_intent = payment_intent.id
                appointment.charge_id = payment_intent.latest_charge
                appointment.amount = payment_intent.amount_received / 100
                appointment.save()
                
                Payment.objects.create(
                    appointment=appointment,
                    amount=appointment.amount,
                    method=payment_intent.payment_method_types[0],
                    status='Success',
                    payment_notes=payment_intent.get('description')              
                )
                
                slot = appointment.slot
                date_obj = appointment.date
                date = str(date_obj)
                
                doctor = User.objects.filter(pk=appointment.doctor).first()
                if not doctor:
                    return Response({"error": "Invalid doctor ID"}, status=404)
                
                patient = User.objects.filter(pk=appointment.patient).first()
                if not patient:
                    return Response({'error':'Invalid patient ID'}, status=404)
                
                doctor_tz = self.get_user_timezone(doctor)
                patient_tz = self.get_user_timezone(patient)

        
                slot_start_str = slot.split("-")[0].strip()
                slot_start_time = datetime.strptime(slot_start_str, "%H:%M").time()            
                appointment_datetime = datetime.combine(date_obj, slot_start_time)
                
                aware_appointment_datetime = doctor_tz.localize(appointment_datetime)
                utc_appointment_datetime = aware_appointment_datetime.astimezone(pytz.UTC)
                
                patient_appointment_datetime = utc_appointment_datetime.astimezone(patient_tz)
                doctor_appointment_datetime = utc_appointment_datetime.astimezone(doctor_tz)
                
                slot_patient_start = patient_appointment_datetime.strftime("%H:%M")
                slot_patient_end = (patient_appointment_datetime + timedelta(minutes=30)).strftime("%H:%M")
                slot_doctor_start = doctor_appointment_datetime.strftime("%H:%M")
                slot_doctor_end = (doctor_appointment_datetime + timedelta(minutes=30)).strftime("%H:%M")
                
                # WhatsApp Notification Message
                message = (
                    f"Hello {patient.first_name},\n"
                    f"Your appointment has been successfully booked.\n"
                    f"Date: {date}\n"
                    f"Time: {slot}\n"
                    f"Doctor: {doctor.first_name} {doctor.last_name}\n"
                    f"Location: Online/Clinic\n"
                    f"Thank you for choosing our service!"
                )
                  
                doctor = User.objects.get(id=appointment.doctor)  # get doctor as a User object
                doctor_name = f"{doctor.first_name} {doctor.last_name}"  # access first_name
                doctor_profile = Doctor.objects.filter(user=doctor).first()

                patient = User.objects.get(id=appointment.patient)  # get patient as a User object
                patient_name = f"{patient.first_name} {patient.last_name}"
                
                # Send WhatsApp Notification to patient
                send_whatsapp_message_patient(
                    to=patient.phone_number,
                    patient_name=patient_name,
                    date=appointment.date.strftime("%Y-%m-%d"),
                    slot=f"{slot_patient_start} - {slot_patient_end}",
                    doctor_name=doctor_name,
                    appointment_type=appointment.appointment_type
                )
                
                # Send WhatsApp Notification to doctor
                send_whatsapp_message_doctor(
                    to=doctor.phone_number,
                    patient_name=patient_name,
                    date=appointment.date.strftime("%Y-%m-%d"),
                    slot=f"{slot_doctor_start} - {slot_doctor_end}",
                    doctor_name=doctor_name,
                    appointment_type=appointment.appointment_type
                )
                
                # Send **In-App Notifications**
                send_notification(
                    user_id=doctor.id,
                    message=f"You have a new appointment with {patient_name} on {date} at {slot}."
                )

                send_notification(
                    user_id=patient.id,
                    message=f"Your appointment with Dr. {doctor_name} is scheduled on {date} at {slot}."
                )
                
                try:
                    sendgrid_client = SendGridAPIClient(settings.SENDGRID_API_KEY)

                    patient_email = Mail(
                        from_email=settings.SENDGRID_FROM_EMAIL,
                        to_emails=patient.email,
                    )
                    patient_email.template_id = "d-20159cf43e714e4b86bf4af62d3b40ba" 
                    patient_email.dynamic_template_data = {
                        "patient_name": patient_name,
                        "doctor_name": doctor_name,
                        "appointment_date": date,
                        "slot": f"{slot_patient_start} - {slot_patient_end}",
                        "appointment_type": str(appointment.get_appointment_type_display()),
                    }
                    sendgrid_client.send(patient_email)

                    doctor_email = Mail(
                        from_email=settings.SENDGRID_FROM_EMAIL,
                        to_emails=doctor.email,
                    )
                    doctor_email.template_id = "d-74121fda9fe9417697f59c2541dfa69d"
                    doctor_email.dynamic_template_data = {
                        "doctor_name": doctor_name,
                        "patient_name": patient_name,
                        "appointment_date": date,
                        "slot": f"{slot_doctor_start} - {slot_doctor_end}",
                        "appointment_type": str(appointment.get_appointment_type_display()),
                    }
                    sendgrid_client.send(doctor_email)

                except Exception as e:
                    logger.error(f"SendGrid email sending failed: {str(e)}")

                return Response({
                    "success": True,
                    "message": "Payment successful",
                    "data": {
                        "appointment_id": appointment.id,
                        "amount": f"{appointment.amount:.2f}",
                        "currency": payment_intent.currency.upper(),
                        "stripe_payment_id": payment_intent.id,
                        "payment_method": payment_intent.payment_method_types[0],
                        "payment_status": payment_intent.status
                    }
                }, status=200)
            
            except BookedAppointment.DoesNotExist:
                return Response({"success": False, "message": "Appointment not found"}, status=404)
        
        elif event['type'] == 'payment_intent.payment_failed':
            intent = event['data']['object']
            metadata = intent.get('metadata',{})
            appointment_id = metadata.get('appointment_id')
            
            try:
                appointment = BookedAppointment.objects.get(id=appointment_id)
                appointment.payment_status = "Falied"
                appointment.save()
                
                Payment.objects.create(
                    appointment=appointment,
                    amount=appointment.amount,
                    method=payment_intent.payment_method_types[0],
                    status='Failed',
                    payment_notes=payment_intent.get('description')              
                )
                
                return Response({
                    "success": False,
                    "message": "Payment failed",
                    "data": {
                        "appointment_id": appointment.id,
                        "stripe_payment_id": intent.id,
                        "failure_reason": intent.last_payment_error.get('message')
                    }
                }, status=200)
                
            except BookedAppointment.DoesNotExist:
                return Response({"success": False, "message": "Appointment not found"}, status=404)
        
        elif event['type'] == "Checkout.session.expired":
            appointment = event['data']['object']
            appointment.status = "Failed"
            appointment.save()
            
            Payment.objects.create(
                    appointment=appointment,
                    amount=appointment.amount,
                    method=payment_intent.payment_method_types[0],
                    status='Failed',
                    payment_notes=payment_intent.get('description')              
                )
            return Response({"success": False, "message": "Session expired"}, status=400)
        
        return Response(status=status.HTTP_200_OK)
    
    def get_user_timezone(self, user):
        try:
            pref = UserPreference.objects.filter(user=user).first()
            if pref and not pref.use_system_timezone:
                return pytz_timezone(pref.timezone)
        except:
            pass
        tz_str = str(getattr(user, 'timezone', 'UTC'))
        return pytz_timezone(tz_str)
        