from celery import shared_task
from django.contrib.auth import get_user_model
from .models import Reminder
import sendgrid
from sendgrid.helpers.mail import Mail
from django.conf import settings
from django.utils.timezone import now
from datetime import datetime, timedelta
from django.utils import timezone
from twilio.rest import Client

User = get_user_model()

@shared_task
def send_email_reminder(reminder_id):
    """Send email reminder to the patient."""
    try:
        reminder = Reminder.objects.get(id=reminder_id)
        appointment = reminder.appointment  # BookedAppointment instance
        patient = User.objects.get(id=appointment.patient)
        doctor = User.objects.get(id=appointment.doctor)
        start_time_str = appointment.slot.split(" - ")[0]  # Extract 'HH:MM'
        appointment_time = datetime.combine(
            appointment.date, datetime.strptime(start_time_str, "%H:%M").time()
        )
        sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        message = Mail(
            from_email="it@my-health.today",
            to_emails=patient.email,
            subject="Appointment Reminder",
            html_content=f"""
                <p>Dear {patient.first_name},</p>
                <p>This is a reminder for your appointment with Dr. {doctor.first_name} on {appointment.date} at {appointment.slot}.</p>
                <p>Thank you!</p>
            """,
        )
        sg.send(message)
        print(f"Email reminder sent to {patient.email}")
    except Reminder.DoesNotExist:
        print(f"Error: Reminder with ID {reminder_id} not found.")
    except User.DoesNotExist as e:
        print(f"Error: User not found - {e}")
    except Exception as e:
        print(f"Error sending email reminder: {e}")

@shared_task
def send_whatsapp_reminder(reminder_id):
    """Send WhatsApp reminder to the patient."""
    try:
        reminder = Reminder.objects.get(id=reminder_id)
        appointment = reminder.appointment
        patient = User.objects.get(id=appointment.patient)
        doctor = User.objects.get(id=appointment.doctor)
        # Extract start time from slot
        start_time_str = appointment.slot.split(" - ")[0]  # Extract 'HH:MM'
        appointment_datetime = datetime.combine(
            appointment.date, 
            datetime.strptime(start_time_str, "%H:%M").time()
        )

        # Make appointment datetime timezone-aware (UTC)
        appointment_datetime_utc = timezone.make_aware(appointment_datetime, timezone.utc)
        print(f"Appointment DateTime (UTC): {appointment_datetime_utc}")

        client = Client(settings.ACCOUNT_SID, settings.AUTH_TOKEN)
        message = client.messages.create(
            from_=settings.TWILIO_WHATSAPP_NUMBER,
            body=f"Reminder: Your appointment with Dr. {doctor.first_name} is on {appointment.date} at {appointment.slot}.",
            to=f"whatsapp:{patient.phone_number}",
        )
        print(f"WhatsApp reminder sent to {patient.phone_number}: {message.sid}")
        # Schedule next reminder if applicable
        schedule_next_reminder(reminder, appointment_datetime_utc, "whatsapp")
    except Exception as e:
        print(f"Error sending WhatsApp reminder: {e}")

@shared_task
def send_sms_reminder(reminder_id):
    """Send SMS reminder to the patient."""
    try:
        reminder = Reminder.objects.get(id=reminder_id)
        appointment = reminder.appointment
        patient = User.objects.get(id=appointment.patient)
        doctor = User.objects.get(id=appointment.doctor)
        # Extract start time from slot
        start_time_str = appointment.slot.split(" - ")[0]  # Extract 'HH:MM'
        appointment_time = datetime.combine(
            appointment.date, datetime.strptime(start_time_str, "%H:%M").time()
        )
        # Make the appointment time timezone-aware (UTC)
        appointment_time = timezone.make_aware(appointment_time, timezone.utc)
        print(f"Appointment Time (UTC): {appointment_time}")
        client = Client(settings.ACCOUNT_SID, settings.AUTH_TOKEN)
        message = client.messages.create(
            from_='+14342681318',
            body=f"Reminder: Your appointment with Dr. {doctor.first_name} is on {appointment.date} at {appointment.slot}.",
            to=patient.phone_number,  # Ensure phone number is in international format
        )
        print(f"SMS reminder sent to {patient.phone_number}: {message.sid}")
        # Schedule next reminder if applicable
        schedule_next_reminder(reminder, appointment_time, "sms")
    except Exception as e:
        print(f"Error sending SMS reminder: {e}")

def schedule_next_reminder(reminder, appointment_time, method):
    """Schedule the next reminder (Email, WhatsApp, or SMS)."""
    next_reminder_time = None
    if reminder.notification_time_type == "days":
        next_reminder_time = now() + timedelta(days=reminder.notification_time)
    elif reminder.notification_time_type == "hours":
        next_reminder_time = now() + timedelta(hours=reminder.notification_time)
    elif reminder.notification_time_type == "minutes":
        next_reminder_time = now() + timedelta(minutes=reminder.notification_time)

    if next_reminder_time and next_reminder_time < appointment_time:
        if method == "whatsapp":
            send_whatsapp_reminder.apply_async(args=[reminder.id], utc=next_reminder_time)
            print(f"Next WhatsApp reminder scheduled for {next_reminder_time}")
        elif method == "phone":
            send_sms_reminder.apply_async(args=[reminder.id], utc=next_reminder_time)
            print(f"Next SMS reminder scheduled for {next_reminder_time}")
        else:
            send_email_reminder.apply_async(args=[reminder.id], utc=next_reminder_time)
            print(f"Next Email reminder scheduled for {next_reminder_time}")
