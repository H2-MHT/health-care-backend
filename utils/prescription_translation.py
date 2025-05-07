from deep_translator import GoogleTranslator

def translate_prescription_content(context: dict, lang_code: str) -> dict:
    fields_to_translate = [
        'diagnosis',
        'medicines',
        'additional_instruction',
        'doctor_address',
        'doctor_name',
        'patient_name',
        'created_date',
        'patient_email',
        'doctor_email',
        'diagnosis_title',
        'notes_title',
        'notes',
        'quantity',
        'time',
        'times_day',
        'duration', 
        'medication', 
        'signature', 
        'assurance', 
        'prescription', 
        'patient_address', 
        'creating_date', 
        'due_date',
    ]

    for field in fields_to_translate:
        if context.get(field):
            try:
                if field == 'medicines' and isinstance(context[field], list):
                    for med in context[field]:
                        for key in ['description', 'time', 'quantity']:
                            if med.get(key):
                                med[key] = GoogleTranslator(source='auto', target=lang_code).translate(med[key])
                else:
                    context[field] = GoogleTranslator(source='auto', target=lang_code).translate(context[field])
            except Exception as e:
                context[field] = f"Translation failed: {str(e)}"
    return context


def translate_reschedule_message(patient_name, doctor_name, old_date, old_slot, new_date, new_slot, lang_code):
    try:
        message = (
            f"Dear {patient_name}, your appointment with Dr. {doctor_name} has been rescheduled "
            f"from {old_date} at {old_slot} to {new_date} at {new_slot}."
        )
        if lang_code and lang_code.lower() != 'en':
            return GoogleTranslator(source='auto', target=lang_code).translate(message)
        return message
    except Exception as e:
        return f"Translation failed: {str(e)}"