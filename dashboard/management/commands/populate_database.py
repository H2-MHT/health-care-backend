from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from appointments.models import Appointment
from clinics.models import Clinic
from consultations.models import ConsultationSummary, Prescription
from doctors.models import Doctor
from patients.models import MedicalHistory, Patient
from payments.models import Payment
from reviews.models import Review
from users.models import User


class Command(BaseCommand):
    help = "Populate the database with sample data"

    def handle(self, *args, **kwargs):
        with transaction.atomic():
            # Create Doctors
            doctor_users = []
            doctors = []
            for i in range(1, 4):
                user = User.objects.create_user(
                    email=f"doctor{i}@example.com",
                    password="password",
                    first_name=f"Doctor{i}",
                    last_name="Smith",
                    role="Doctor",
                )
                doctor_users.append(user)
                doctor = Doctor.objects.create(
                    user=user,
                    specialty="General Medicine",
                    qualifications="MBBS, MD",
                    experience_years=5 + i,
                )
                doctors.append(doctor)

            # Create Patients
            patients = []
            for i in range(1, 6):
                user = User.objects.create_user(
                    email=f"patient{i}@example.com",
                    password="password",
                    first_name=f"Patient{i}",
                    last_name="Doe",
                    role="Patient",
                )
                patient = Patient.objects.create(
                    user=user,
                    chronic_conditions="Condition A",
                    current_medication="Medication A",
                )
                patients.append(patient)

            # Assign Multiple Patients to a Single Doctor
            for i, patient in enumerate(patients):
                doctor = doctors[i % len(doctors)]  # Distribute patients across doctors
                clinic = Clinic.objects.create(
                    name=f"Clinic{i+1}",
                    address="123 Main St",
                    phone_number="1234567890",
                    password="clinicpassword",
                    email=f"clinic{i+1}@example.com",
                )
                appointment = Appointment.objects.create(
                    patient=patient,
                    doctor=doctor,
                    clinic=clinic,
                    date_time=timezone.now() + timedelta(days=i + 1),
                    status="Confirmed",
                )

                # Create Reviews
                Review.objects.create(
                    patient=patient,
                    doctor=doctor,
                    rating=4 + (i % 2),
                    content="Good service",
                    recommend=True,
                    reply="Thank you!",
                )

                # Create Medical History
                MedicalHistory.objects.create(
                    patient=patient,
                    condition="Condition A",
                    diagnosis_date=timezone.now().date(),
                    status="Active",
                    notes="Needs regular checkups",
                )

                # Create Payments
                Payment.objects.create(
                    appointment=appointment,
                    amount=100.00 + i,
                    total_amount=120.00 + i,
                    method="Credit Card",
                    status="Paid",
                )

                # Create Prescription
                Prescription.objects.create(
                    appointment=appointment,
                    doctor=doctor,
                    file="prescription.pdf",
                    content="Take medicine daily",
                )

                # Create Consultation Summary
                ConsultationSummary.objects.create(
                    appointment=appointment,
                    ai_generated_summary="AI generated summary",
                    human_verified_summary="Doctor approved summary",
                )

        self.stdout.write(self.style.SUCCESS("Database populated successfully."))
