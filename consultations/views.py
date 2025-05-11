from django.conf import settings
from django.http import HttpResponse
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail,
    Attachment,
    FileContent,
    FileName,
    FileType,
    Disposition,
)
import base64
import logging
import os
from weasyprint import HTML
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from .models import (
    Prescription,
    ConsultationReport,
)
from rest_framework.permissions import IsAuthenticated
from .serializers import PrescriptionSerializer
from django.urls import reverse
from django.core.files.base import ContentFile
from doctors.models import (
    BookedAppointment,
    Doctor,
)
from patients.models import Patient
from users.models import User
from django.shortcuts import get_object_or_404
import qrcode
from io import BytesIO
from django.template.loader import render_to_string
from utils.prescription_translation import translate_prescription_content
from users.models import AppLanguage
from django.shortcuts import redirect

# Configure logging
logger = logging.getLogger(__name__)


def generate_qr_code_base64(data: str) -> str:
    qr = qrcode.QRCode(box_size=2, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#00bbd3", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buffered.getvalue()).decode()}"


def generate_pdf(template_path: str, context: dict, request) -> tuple:
    html_string = render_to_string(template_path, context)
    pdf_file = BytesIO()
    HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf(pdf_file)
    
    temp_pdf_name = os.path.join(settings.BASE_DIR, f"H2-Prescription_{context['prescription_id']}.pdf")
    with open(temp_pdf_name, 'wb') as f:
        f.write(pdf_file.getvalue())

    return pdf_file.getvalue(), temp_pdf_name

def send_pdf_via_sendgrid(template_path, context_dict, recipient_email, request):
    pdf_content, temp_pdf_name = generate_pdf(template_path, context_dict, request)
    encoded_pdf = base64.b64encode(pdf_content).decode()

    message = Mail(
        from_email=settings.SENDGRID_FROM_EMAIL,
        to_emails=recipient_email,
        subject="Your Prescription",
        plain_text_content="Please find the attached prescription."
    )
    attachment = Attachment(
        FileContent(encoded_pdf),
        FileName(os.path.basename(temp_pdf_name)),
        FileType('application/pdf'),
        Disposition('attachment')
    )
    message.attachment = attachment

    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        logging.info(f"Email with PDF sent to {recipient_email}")
        return response
    except Exception as e:
        logging.error(f"SendGrid Email Error: {e}")
        return str(e)
    finally:
        if os.path.exists(temp_pdf_name):
            os.remove(temp_pdf_name)


def prescription_pdf_redirect(request):
    uid = request.GET.get("uid")
    if not uid:
        return Response({"error": "UUID is required in query parameters."}, status=status.HTTP_400_BAD_REQUEST)

    user = get_object_or_404(User, uid=uid)
    prescription = get_object_or_404(Prescription, appointment__patient=user.id)
    return redirect(prescription.pdf_file.url)

def send_prescription_email(request, prescription):
    try:
        doctor_user = User.objects.get(id=prescription.appointment.doctor)
        patient_user = User.objects.get(id=prescription.appointment.patient)
        formatted_date = prescription.created_at.strftime("%d %B %Y")

        context = {
            'prescription_id': prescription.id,
            'created_date': formatted_date,
            'doctor_name': doctor_user.get_full_name(),
            'doctor_email': doctor_user.email,
            'doctor_phone': doctor_user.phone_number,
            'patient_name': patient_user.get_full_name(),
            'patient_email': patient_user.email,
            'patient_address': patient_user.city,
            'patient_phone': patient_user.phone_number,
            'diagnosis': prescription.diagnosis,
            'medicines': prescription.medicines,
            'additional_instruction': prescription.additional_instruction,
            "prescription": "Prescription",
            "diagnosis_title": "Diagnosis",
            "quantity": "Quantity",
            "time": "Time",
            "medication": "Medication",
            "times_day": "Times/day",
            "duration": "Duration",
            "notes_title": "Notes",
            "signature": "Signature",
            "assurance": "Assurance info",
            "creating_date": "Date",
            "due_date": "Due Date",
        }

        try:
            user_language_pref = AppLanguage.objects.get(user=patient_user)
        except AppLanguage.DoesNotExist:
            user_language_pref = AppLanguage(code='en')

        if user_language_pref.code != 'en':
            context = translate_prescription_content(context, user_language_pref.code)
        
        template_path = 'prescription.html'
        pdf_file, _ = generate_pdf(template_path, context, request)
        prescription.pdf_file.save(f"prescription_{prescription.id}.pdf", ContentFile(pdf_file))
        prescription.save()

        prescription_url = request.build_absolute_uri(prescription.pdf_file.url)
        qr_code_base64 = generate_qr_code_base64(prescription_url)
        context['qr_code_base64'] = qr_code_base64
        
        user = User.objects.get(id=prescription.appointment.patient)
        short_url = request.build_absolute_uri(reverse("prescription_pdf")) + f"?uid={user.uid}"
        qr_code_base64 = generate_qr_code_base64(short_url)
        context['qr_code_base64'] = qr_code_base64

        final_pdf_file, _ = generate_pdf(template_path, context, request)
        prescription.pdf_file.save(f"prescription_{prescription.id}_with_qr.pdf", ContentFile(final_pdf_file))
        prescription.save()
     
        send_pdf_via_sendgrid(template_path, context, patient_user.email, request)

        return {"status": "Email sent successfully via SendGrid!"}

    except User.DoesNotExist as e:
        return {"error": f"User not found: {str(e)}"}
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}

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
                return Response({"message": "You are not authorized for this appointment."}, status=status.HTTP_403_FORBIDDEN)
            
            if appointment.status != "Completed":
                return Response({'message': 'You can not create the prescription as appointment is not completed yet'}, status=status.HTTP_200_OK)

            # Prevent duplicate prescription
            if Prescription.objects.filter(appointment_id=appointment_id).exists():
                return Response({"message": "Prescription already exists."}, status=status.HTTP_200_OK)

            doctor_user = request.user
            patient_user = User.objects.get(id=appointment.patient)

            # Save prescription to DB (No QR here)
            prescription = Prescription.objects.create(
                appointment=appointment,
                doctor=doctor_user,
                diagnosis=data.get("diagnosis"),
                medicines=data.get("medicines"),
                additional_instruction=data.get("additional_instruction")
            )

            # Prepare PDF context
            context = {
                'prescription_id': prescription.id,
                'created_date': prescription.created_at,
                'doctor_name': doctor_user.get_full_name(),
                'doctor_email': doctor_user.email,
                'doctor_phone': doctor_user.phone_number,
                'patient_name': patient_user.get_full_name(),
                'patient_email': patient_user.email,
                'patient_address': patient_user.city,
                'patient_phone': patient_user.phone_number,
                'diagnosis': prescription.diagnosis,
                'medicines': prescription.medicines,
            }

            # Generate PDF and attach to saved model (no QR in DB)
            pdf_file, _ = generate_pdf("prescription.html", context, request)
            prescription.pdf_file.save(f"prescription_{prescription.id}.pdf", ContentFile(pdf_file))

            # Email PDF with QR
            send_prescription_email(request, prescription)

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
            user_ids = {pres.appointment.doctor for pres in prescriptions} | {pres.appointment.patient for pres in prescriptions}
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
            if not prescription:
                return Response({'error': 'Prescription not found'}, status=status.HTTP_404_NOT_FOUND)

            serializer = PrescriptionSerializer(prescription, data=request.data, partial=True)
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

            # Ensure the user has a Patient profile
            try:
                patient = user.patient_profile
            except Exception:
                return Response({"error": "User is not a patient"}, status=status.HTTP_400_BAD_REQUEST)

            # Filter appointments by raw user ID
            appointments = BookedAppointment.objects.filter(patient=user.id, status='Completed')

            if not appointments.exists():
                return Response({'message': 'No completed appointments found'}, status=status.HTTP_200_OK)

            prescriptions = Prescription.objects.filter(appointment__in=appointments)

            if not prescriptions.exists():
                return Response({'message': 'No prescriptions found'}, status=status.HTTP_200_OK)

            data = []
            for prescription in prescriptions:
                appointment = prescription.appointment

                # Fetch Doctor and Patient profiles using user IDs
                doctor_user = User.objects.filter(id=appointment.doctor).first()
                patient_user = User.objects.filter(id=appointment.patient).first()

                data.append({
                    'appointment_id': appointment.id,
                    "created_date": prescription.created_at.strftime('%d %b, %Y'),
                    "doctor": {
                        "name": f"{doctor_user.first_name} {doctor_user.last_name}" if doctor_user else "Unknown",
                        "email": doctor_user.email if doctor_user else "Unknown",
                    },
                    'patient': {
                        'name': f"{patient_user.first_name} {patient_user.last_name}" if patient_user else "Unknown",
                        "email": patient_user.email if patient_user else "Unknown",
                    },
                    'pdf_url': prescription.pdf_file.url
                    # 'pdf_url': request.build_absolute_uri(
                    #     reverse('prescription_template') + f"?appointment_id={appointment.id}"
                    # )
                })

            return Response({"message": "Prescriptions retrieved successfully", "prescriptions": data},status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class PrescriptionPDFView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            appointment_id = request.query_params.get('appointment_id')
            try:
                prescription = Prescription.objects.get(appointment__id=appointment_id)
            except Prescription.DoesNotExist:
                return Response({'message':'prescription not found'}, status=status.HTTP_404_NOT_FOUND)

            template_path = 'prescription.html'
            doctor_user = User.objects.get(id=prescription.appointment.doctor)
            patient_user = User.objects.get(id=prescription.appointment.patient)
            context = {
                'prescription_id': prescription.id,
                'created_date': prescription.created_at,
                'doctor_name': doctor_user.first_name + " " + doctor_user.last_name,
                'doctor_email': doctor_user.email,
                'doctor_phone': doctor_user.phone_number,
                'hospital_name': '',
                'hospital_address': '',
                'patient_name': patient_user.first_name,
                'patient_email': patient_user.email,
                'patient_address': patient_user.city,
                'patient_phone': patient_user.phone_number,
                'diagnosis': prescription.diagnosis,
                # 'notes': prescription.appointment.notes,
                'medicines': prescription.medicines,
                # 'qr_code_url': request.build_absolute_uri(static('images/QR_Code.svg')),
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


class ConsultationReportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):        
        appointment = request.data.get('appointment_id')
        prescription = request.data.get('prescription')
        short_description = request.data.get('short_description')
        translated_text = request.data.get('translated_text')
        recommendation = request.data.get('recommendation')

        if not appointment or not translated_text:
            return Response({"error": "Appointment or translated text is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            appointment = BookedAppointment.objects.get(pk=appointment)
        except BookedAppointment.DoesNotExist:
            return Response({"error": "Appointment not found."}, status=status.HTTP_404_NOT_FOUND)

        
        doctor = Doctor.objects.filter(user_id=appointment.doctor).first()
        patient = Patient.objects.filter(user_id=appointment.patient).first()

        if not doctor or not patient:
            return Response({"error": "Doctor or patient not found."}, status=status.HTTP_404_NOT_FOUND)
        
        if request.user.role == "Patient":
            user = "patient_id"
            user_id = request.user.patient_profile.id
        elif request.user.role == "Doctor":
            user = "doctor_id"
            user_id = request.user.doctor.id
            
        Consultation = ConsultationReport.objects.create(
            patient=patient,
            doctor=doctor,
            appointment=appointment,
            short_description=short_description,
            translated_text=translated_text,
            prescription = prescription,
            recommendation=recommendation
        )
        return Response(
            { 
              "message": "Consultation created successfully",
              "data":{
                  "id": Consultation.id,
                   user: user_id,
                  "appointment_id": Consultation.appointment.id,
                  "translated_text": Consultation.translated_text,
                  "created_at": Consultation.created_at
              }
            },
              status=status.HTTP_200_OK)
    

    def get(self, request):
        try:
            appointment_id = request.query_params.get('appointment_id')
            if not appointment_id:
                return Response({"error": "Appointment id is required."}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                 appointment = BookedAppointment.objects.get(id =appointment_id)
            except BookedAppointment.DoesNotExist:
                return Response({"error": "Invalid appointment id"}, status=status.HTTP_404_NOT_FOUND)
            
            prescription = Prescription.objects.filter(appointment=appointment).first()
            prescription_data = PrescriptionSerializer(prescription).data if prescription else None
            
            patient = ""
            doctor = ""
            if request.user.role == "Patient":
                patient = request.user.patient_profile
                consultations = ConsultationReport.objects.filter(patient=patient, appointment=appointment)
            elif request.user.role == "Doctor":
                doctor = request.user.doctor
                consultations = ConsultationReport.objects.filter(doctor=doctor, appointment=appointment)
                        
            data = [
                {
                    "id": consultation.id,
                    "appointment_id": consultation.appointment.id,
                    "prescription": prescription_data,
                    "short_description": consultation.short_description,
                    "translated_text": consultation.translated_text,
                    "recommendation": consultation.recommendation,
                    "created_at": consultation.created_at,
                }
                for consultation in consultations
            ]
            return Response(
                {
                    "message": "Consultation list retrieved successfully",
                    "consultation": data
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        consultation_id = request.data.get('consultation_id')
        if not consultation_id:
            return Response({"error": "Consultation ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            consultation = ConsultationReport.objects.get(pk=consultation_id)
        except ConsultationReport.DoesNotExist:
            return Response({"error": "Consultation report not found."}, status=status.HTTP_404_NOT_FOUND)

        short_description = request.data.get('short_description')
        translated_text = request.data.get('translated_text')
        recommendation = request.data.get('recommendation')

        if not translated_text and not recommendation and not short_description:
            return Response({"error": "No fields provided for update."}, status=status.HTTP_400_BAD_REQUEST)

        if translated_text:
            consultation.translated_text = translated_text

        if recommendation:
            consultation.recommendation = recommendation

        if short_description:
            consultation.short_description = short_description

        consultation.save()
        data=[
            {
                "short_description": consultation.short_description,
                "recommendation": consultation.recommendation,
                "translated_text": consultation.translated_text
            }
        ]
        return Response(
            {
                "message": "Consultation report updated successfully.",
                "data":data
            },
            status=status.HTTP_200_OK)


