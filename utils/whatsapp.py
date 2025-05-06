from twilio.rest import Client
from django.conf import settings
# Twilio credentials
TWILIO_WHATSAPP_NUMBER = settings.TWILIO_WHATSAPP_NUMBER

client = Client(settings.ACCOUNT_SID, settings.AUTH_TOKEN)

def send_whatsapp_message_patient(to, date, slot, patient_name, doctor_name, appointment_type):
    """
    Sends a WhatsApp message to the patient .
    """
    try:
        message_body = f"Hello {patient_name}, your appointment has been booked.\n\n" \
            f"Date: {date}\n" \
            f"Time: {slot}\n" \
            f"Doctor: {doctor_name}\n" \
            f"Type: {appointment_type}\n\n" \
            "Thank you for choosing our service!"

        msg = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=f"whatsapp:{to}",
            body=message_body
        )
        return {"success": True, "message_id": msg.sid}  
    except Exception as e:
        return {"success": False, "error": str(e)}


def send_whatsapp_message_doctor(to, date, slot, patient_name, doctor_name, appointment_type):
    """
    Sends a WhatsApp message to the doctor.
    """
    try:
        message_body = f"Hello Dr. {doctor_name},\n\n" \
            f"A new appointment has been booked.\n\n" \
            f"Patient: {patient_name}\n" \
            f"Date: {date}\n" \
            f"Time: {slot}\n" \
            f"Type: {appointment_type}\n\n" \
            "Please check your schedule. Thank you!"

        msg = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=f"whatsapp:{to}",
            body=message_body
        )
        return {"success": True, "message_id": msg.sid}  
    except Exception as e:
        return {"success": False, "error": str(e)}


def appointment_cancel_notification_patient(to, date, slot, patient_name, doctor_name):
    """
    Sends a WhatsApp message to the patient when an appointment is canceled.
    """
    try:
        message_body = f"Hello {patient_name},\n\n" \
            f"Your appointment scheduled on {date} at {slot} with Dr. {doctor_name} has been CANCELED.\n\n" \
            "If this was a mistake, please rebook.\n\n" \
            "Thank you for using our service!"
        msg = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=f"whatsapp:{to}",
            body=message_body
        )
        return {"success": True, "message_id": msg.sid}  
    except Exception as e:
        return {"success": False, "error": str(e)}
    

def appointment_cancel_notification_doctor(to, date, slot, patient_name, doctor_name):
    """
    Sends a WhatsApp message to the doctor when an appointment is canceled.
    """
    try:
        message_body = f"Hello Dr. {doctor_name},\n\n" \
            f"{patient_name} has canceled their appointment scheduled on {date} at {slot}.\n\n" \
            "If this was a mistake, please reschedule.\n\n" \
            "Thank you for using our service!"
        msg = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=f"whatsapp:{to}",
            body=message_body
        )
        return {"success": True, "message_id": msg.sid}  
    except Exception as e:
        return {"success": False, "error": str(e)}
    
    
def appointment_reschedule_notification_patient(to, old_date, old_slot, new_date, new_slot, doctor_name, patient_name):
    """
    Sends a WhatsApp message to the patient when they reschedule an appointment.
    """
    try:
        message_body = f"Hello {patient_name},\n\n" \
            f"Your appointment on {old_date} at {old_slot} has been rescheduled to {new_date} at {new_slot} with Dr. {doctor_name}.\n\n" \
            "Thank you for using our service!"
        
        msg = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=f"whatsapp:{to}",
            body=message_body
        )
        return {"success": True, "message_id": msg.sid}  
    except Exception as e:
        return {"success": False, "error": str(e)}


def appointment_reschedule_notification_doctor(to, old_date, old_slot, new_date, new_slot, doctor_name, patient_name):
    """
    Sends a WhatsApp message to the doctor when a patient reschedules an appointment.
    """
    try:
        message_body = f"Hello Dr. {doctor_name},\n\n" \
            f"{patient_name} has rescheduled their appointment from {old_slot} on {old_date} " \
            f"to {new_slot} on {new_date}.\n\n" \
            "Thank you for using our service!"
        
        msg = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=f"whatsapp:{to}",
            body=message_body
        )
        return {"success": True, "message_id": msg.sid}  
    except Exception as e:
        return {"success": False, "error": str(e)}
    

def appointment_reschedule_notification_patient(to, old_date, old_slot, new_date, new_slot, doctor_name, patient_name):
    """
    Sends a WhatsApp message to the patient when an appointment is rescheduled,
    with instructions to confirm or cancel.
    """
    try:
        message_body = f"Hello {patient_name},\n\n" \
            f"Your appointment with Dr. {doctor_name} has been rescheduled.\n" \
            f"Old: {old_date} at {old_slot}\n" \
            f"New: {new_date} at {new_slot}\n\n" \
            f"Please reply:\n1 to Confirm\n2 to Cancel"

        msg = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=f"whatsapp:{to}",
            body=message_body
        )
        return {"success": True, "message_id": msg.sid}

    except Exception as e:
        return {"success": False, "error": str(e)}
