from django.conf import settings
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import base64
from django.template.loader import get_template
import logging
from django.templatetags.static import static
import os
from datetime import datetime
from weasyprint import HTML
from django.http import JsonResponse

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


def send_prescription_email(request):
    """
    API endpoint to send a prescription email with a PDF attachment using SendGrid.
    """
    context = {
        'prescription_id': '27346733-022',
        'created_date': '6 March, 2020',
        'due_date': '7 March, 2020',
        'doctor_name': 'Dr. Ava Willson',
        'doctor_email': 'starfleet@abagal.com',
        'doctor_phone': '(+254) 243-124-392',
        'hospital_name': 'Hospital St.Katarina',
        'hospital_address': '9029 Arcane, Jupiter 2',
        'patient_name': 'Din Djarin',
        'patient_email': 'dindjarin@gmail.com',
        'patient_address': '9029 Salt Lake, Mandalor',
        'patient_phone': '(+254) 724-453-233',
        'diagnosis': 'ave dolurum kircbe',
        'notes': 'akdncurfj ksk fycn wjkd sa chfnra,',
        'medicines': [
            {'name': 'Medical consultation', 'description': 'details of description', 'quantity': '1 ml',
             'time': 'Morning', 'times_per_day': '2', 'duration': '6 days'},
            {'name': 'Paracetamol', 'description': 'Pain reliever', 'quantity': '500 mg', 'time': 'Evening',
             'times_per_day': '3', 'duration': '5 days'}
        ],
        'qr_code_url': request.build_absolute_uri(static('images/QR_Code.svg')),
    }

    template_path = 'prescription.html'
    recipient_email = 'prescription@yopmail.com'

    send_pdf_via_sendgrid(template_path, context, recipient_email, request)

    return JsonResponse({"status": "Email sent successfully via SendGrid!"})
