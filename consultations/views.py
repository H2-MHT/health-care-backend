from django.conf import settings
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import base64
from django.template.loader import get_template
import logging
from django.templatetags.static import static
import os
from datetime import datetime
from appointments.models import Appointment
from doctors.models import Doctor
from weasyprint import HTML
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.http import HttpResponse
from .models import Prescription
from django.utils.dateparse import parse_date
from rest_framework.permissions import IsAuthenticated
from .serializers import PrescriptionSerializer
from django.urls import reverse
from django.core.files.base import ContentFile
from doctors.models import BookedAppointment
from users.models import User
from django.shortcuts import get_object_or_404

# Configure logging
logger = logging.getLogger(__name__)


def generate_pdf(template_path, context_dict, request):
    """
    Generate a PDF from an HTML template and return the PDF content and file path.
    """
    template = get_template(template_path)
    logging.debug("Rendering HTML content...")
    html_content = template.render(context_dict)
    logging.debug("HTML rendered. Generating PDF...")

    now = datetime.now()
    filename = now.strftime("%d%b%y-%H-%M") + ".pdf"

    current_dir = os.getcwd()
    temp_dir = os.path.join(current_dir, 'temp')

    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
        logging.debug(f"Temporary directory created: {temp_dir}")
    else:
        logging.debug(f"Temporary directory already exists: {temp_dir}")

    temp_pdf_name = os.path.join(temp_dir, filename)

    logging.debug(f"Creating PDF at: {temp_pdf_name}")
    HTML(string=html_content).write_pdf(temp_pdf_name)
    logging.debug("PDF generation complete.")

    with open(temp_pdf_name, 'rb') as temp_pdf:
        pdf_content = temp_pdf.read()

    logging.debug("PDF content ready.")
    return pdf_content, temp_pdf_name

class PrescriptionPDFView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        try:
            appointment_id = request.query_params.get('appointment_id')
            try:
                prescription = Prescription.objects.get(appointment__id=appointment_id)
            except Prescription.DoesNotExist:
                return Response({'message':'prescription not found'}, status=status.HTTP_404_NOT_FOUND)

            template_path = 'prescription.html'
            context = {
                'prescription_id': prescription.id,
                'created_date': prescription.created_at,
                'doctor_name': prescription.appointment.doctor.user.first_name + " " + prescription.appointment.doctor.user.last_name,
                'doctor_email': prescription.appointment.doctor.user.email,
                'doctor_phone': prescription.appointment.doctor.user.phone_number,
                'hospital_name': prescription.appointment.clinic.user.first_name,
                'hospital_address': prescription.appointment.clinic.address,
                'patient_name': prescription.appointment.patient.user.first_name,
                'patient_email': prescription.appointment.patient.user.email,
                'patient_address': prescription.appointment.patient.user.city,
                'patient_phone': prescription.appointment.patient.user.phone_number,
                'diagnosis': prescription.diagnosis,
                'notes': prescription.appointment.notes,
                'medicines': prescription.medicines,
                'qr_code_url': request.build_absolute_uri(static('images/QR_Code.svg')),
            }
            
            pdf_content, temp_pdf_name = generate_pdf(template_path, context, request)
            pdf_filename = os.path.basename(temp_pdf_name)
            if pdf_filename:
                prescription.pdf_file.save(f'{pdf_filename}', ContentFile(pdf_content))
                prescription.save()
            # Return PDF response
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename={temp_pdf_name}'
            return response

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class PrescriptionView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            if request.user.role != 'Doctor':
                return Response({'message': 'only doctor can perform this action'}, status=status.HTTP_400_BAD_REQUEST)

            data = request.data
            appointment_id = data.get("appointment_id")

            # Validate appointment
            appointment = get_object_or_404(BookedAppointment, id=appointment_id)

            # Ensure the logged-in doctor matches the appointment doctor (IntegerField comparison)
            if appointment.doctor != request.user.id:
                return Response({"error": "You are not authorized for this appointment."}, status=status.HTTP_403_FORBIDDEN)

            # Prevent duplicate prescription
            if Prescription.objects.filter(appointment_id=appointment_id).exists():
                return Response({"error": "Prescription already exists for this appointment."}, status=status.HTTP_400_BAD_REQUEST)

            # Create the prescription
            prescription = Prescription.objects.create(
                appointment=appointment,
                doctor=request.user,  # request.user is a User instance
                diagnosis=data.get("diagnosis"),
                medicines=data.get("medicines"),
                additional_instruction=data.get("additional_instruction")
            )

            send = send_prescription_email(request, prescription)

            return Response(
                {"message": "Prescription saved and email sent!", "prescription_id": prescription.id},
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self, request):
        try:
            appointment_id = request.query_params.get('appointment_id')

            if not appointment_id:
                return Response({"error": "appointment_id is required"}, status=status.HTTP_400_BAD_REQUEST)

            prescriptions = Prescription.objects.select_related('appointment').filter(appointment__id=appointment_id)

            user_ids = set()
            for pres in prescriptions:
                user_ids.add(pres.appointment.doctor)
                user_ids.add(pres.appointment.patient)

            users = User.objects.in_bulk(user_ids)

            data = []
            for prescription in prescriptions:
                appointment = prescription.appointment
                doctor = users.get(appointment.doctor)
                patient = users.get(appointment.patient)

                data.append({
                    'appointment_id': appointment.id,
                    'prescription_id': prescription.id,
                    'created_date': prescription.created_at.strftime('%d %b, %Y'),
                    'doctor': {
                        'id': appointment.doctor,
                        'name': f"{doctor.first_name} {doctor.last_name}" if doctor else "",
                        'email': doctor.email if doctor else "",
                        'phone': doctor.phone_number if doctor else "",
                    },
                    'patient': {
                        'id': appointment.patient,
                        'name': f"{patient.first_name} {patient.last_name}" if patient else "",
                        'email': patient.email if patient else "",
                        'phone': patient.phone_number if patient else "",
                        'address': patient.city if patient else "",
                    },
                    # 'notes': getattr(appointment, 'notes', ""),  # assuming `notes` field might not exist
                    'diagnosis': prescription.diagnosis,
                    'medicines': prescription.medicines,
                    'additional_instruction': prescription.additional_instruction,
                })

            return Response(
                {"message": "Prescriptions retrieved successfully", "prescriptions": data},
                status=status.HTTP_200_OK
            ) if data else Response(
                {"prescriptions": []}, status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        try:
            if request.user.role != 'Doctor':
                return Response({'message': 'only doctor can perform this action'}, status=status.HTTP_400_BAD_REQUEST)

            appointment_id = request.query_params.get('appointment_id', None)
            prescription = Prescription.objects.filter(appointment__id=appointment_id).first()

            data = request.data
            serializer = PrescriptionSerializer(prescription, data=data, partial=True)

            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PrescriptionListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            user = request.user
            try:
                patient = user.patient_profile
            except Exception:
                return Response({"error": "User is not a patient"}, status=status.HTTP_400_BAD_REQUEST)

            # patient.user.id since BookedAppointment.patient is an IntegerField
            appointments = BookedAppointment.objects.filter(patient=patient.user.id, status='Completed')

            if not appointments.exists():
                return Response({'message': 'No completed appointments found'}, status=status.HTTP_404_NOT_FOUND)

            prescriptions = Prescription.objects.filter(appointment__in=appointments)

            if not prescriptions.exists():
                return Response({'message': 'No prescriptions found'}, status=status.HTTP_404_NOT_FOUND)

            data = [
                {
                    'appointment_id': prescription.appointment.id,
                    "created_date": prescription.created_at.strftime('%d %b, %Y'),
                    "doctor": {
                        "name": f"{prescription.appointment.doctor.user.first_name} {prescription.appointment.doctor.user.last_name}",
                        "email": prescription.appointment.doctor.user.email,
                    },
                    'patient': {
                        'name': f"{prescription.appointment.patient.user.first_name} {prescription.appointment.patient.user.last_name}",
                        "email": prescription.appointment.patient.user.email,
                    },
                    'pdf_url': request.build_absolute_uri(
                        reverse('prescription_template') + f"?appointment_id={prescription.appointment.id}"
)

                }
                for prescription in prescriptions
            ]

            return Response({"message": "Prescriptions retrieved successfully", "prescriptions": data},status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



def send_pdf_via_sendgrid(template_path, context_dict, recipient_email, request):
    """
    Generate a PDF and send it via SendGrid email with the attachment.
    """
    pdf_content, temp_pdf_name = generate_pdf(template_path, context_dict, request)

    # Encode PDF file in base64 for SendGrid attachment
    encoded_pdf = base64.b64encode(pdf_content).decode()

    # Create email message
    message = Mail(
        from_email=settings.SENDGRID_FROM_EMAIL,
        to_emails=recipient_email,
        subject="Your Prescription",
        plain_text_content="Please find the attached prescription."
    )

    # Create and attach the PDF
    attachment = Attachment(
        FileContent(encoded_pdf),
        FileName(os.path.basename(temp_pdf_name)),
        FileType('application/pdf'),
        Disposition('attachment')
    )
    message.attachment = attachment

    # Send email via SendGrid
    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        logging.info(f"Email with PDF sent successfully to {recipient_email}.")
        return response
    except Exception as e:
        logging.error(f"Failed to send email via SendGrid: {str(e)}")
        return str(e)


def send_prescription_email(request, prescription):
    """
    API endpoint to send a prescription email with a PDF attachment using SendGrid.
    """
    try:
        # Fetch doctor and patient User instances using their IDs
        doctor_user = User.objects.get(id=prescription.appointment.doctor)
        patient_user = User.objects.get(id=prescription.appointment.patient)
        
        # # Fetch the clinic's user (if needed)
        # hospital_user = prescription.appointment.clinic.user

        context = {
            'prescription_id': prescription.id,
            'created_date': prescription.created_at,
            'doctor_name': f"{doctor_user.first_name} {doctor_user.last_name}",
            'doctor_email': doctor_user.email,
            'doctor_phone': doctor_user.phone_number,
            # 'hospital_name': hospital_user.first_name,  # Assuming `clinic.user` is the hospital's user
            # 'hospital_address': prescription.appointment.clinic.address,
            'patient_name': f"{patient_user.first_name} {patient_user.last_name}",
            'patient_email': patient_user.email,
            'patient_address': patient_user.city,
            'patient_phone': patient_user.phone_number,
            'diagnosis': prescription.diagnosis,
            # 'notes': prescription.appointment.notes,
            'medicines': prescription.medicines,
            'qr_code_url': request.build_absolute_uri(static('images/QR_Code.svg')),
        }

        template_path = 'prescription.html'
        recipient_email = context['patient_email']

        send_pdf_via_sendgrid(template_path, context, recipient_email, request)

        return {"status": "Email sent successfully via SendGrid!"}

    except User.DoesNotExist as e:
        return {"error": f"User not found: {str(e)}"}
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}
