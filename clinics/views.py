from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.response import Response
from clinics.models import *
from clinics.serializers import *
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Count, Avg, Q
from django.db.models.functions import ExtractDay, ExtractMonth, ExtractYear
from datetime import timedelta, datetime
from appointments.models import Appointment
from users.serializers import UserSerializer
from django.conf import settings
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from doctors.models import Doctor
from django.utils import timezone
from django.utils.timezone import now

# Create your views here.


class ClinicAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            clinic = Clinic.objects.all()
            serializer = ClinicSerializer(clinic, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"{e}"}, status=status.HTTP_417_EXPECTATION_FAILED
            )


class LanguageAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            clinic = Language.objects.all()
            serializer = LanguageSerializer(clinic, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"{e}"}, status=status.HTTP_417_EXPECTATION_FAILED
            )


class ServicesProvidedAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            clinic = ServicesProvided.objects.all()
            serializer = ServicesProvidedSerializer(clinic, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"{e}"}, status=status.HTTP_417_EXPECTATION_FAILED
            )


class ClinicRegisterAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, *args, **kwargs):
        try:
            serializer = ClinicRegisterSerializer(
                data=request.data, context={"request": request}
            )
            if serializer.is_valid():
                serializer.save()
                clinic_user = UserSerializer(serializer.instance.user)
                response_data = serializer.data
                response_data["user"] = clinic_user.data
                return Response(response_data, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_417_EXPECTATION_FAILED
            )


class ClinicInfoAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            clinic = Clinic.objects.get(user=request.user)
            serializer = ClinicInfoSerializer(clinic)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Clinic.DoesNotExist:
            return Response(
                {"error": "Clinic not found"}, status=status.HTTP_404_NOT_FOUND
            )

    def put(self, request, *args, **kwargs):
        try:
            clinic = Clinic.objects.get(user=request.user)
            serializer = ClinicInfoSerializer(
                clinic, data=request.data, partial=True
            )  # Allow partial updates
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {
                        "message": "Clinic information successfully updated",
                        "data": serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )
            return Response(
                {"error": "Invalid data provided.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Clinic.DoesNotExist:
            return Response(
                {"error": "Clinic not found"}, status=status.HTTP_404_NOT_FOUND
            )


class ClinicReviewListCreateAPIView(APIView):
    """
    API to list and create clinic reviews.
    Requires authentication.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """List all clinic reviews"""
        reviews = ClinicReview.objects.filter(clinic__user=request.user)
        serializer = ClinicReviewSerializer(reviews, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        """Create a new clinic review"""
        serializer = ClinicReviewSerializer(data=request.data)
        try:
            doctor = Doctor.objects.get(user=request.user)
        except Doctor.DoesNotExist:
            return Response(
                {"error": "Your have not permisson to review, only doctors allowed!."}, status=status.HTTP_404_NOT_FOUND
            )
        
        if serializer.is_valid():
            serializer.save(
                doctor=doctor
            )  # Associate review with the logged-in doctor
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClinicReviewDetailAPIView(APIView):
    """
    API to retrieve, update, or delete a clinic review.
    Requires authentication.
    """

    permission_classes = [IsAuthenticated]

    def get_object(self, review_id):
        """Helper method to get a review object"""
        try:
            return ClinicReview.objects.get(pk=review_id)
        except ClinicReview.DoesNotExist:
            return None

    def get(self, request, review_id, *args, **kwargs):
        """Retrieve a clinic review"""
        review = self.get_object(review_id)
        if not review:
            return Response(
                {"error": "Review not found"}, status=status.HTTP_404_NOT_FOUND
            )
        serializer = ClinicReviewSerializer(review)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, review_id, *args, **kwargs):
        """Update a clinic review"""
        review = self.get_object(review_id)
        if not review:
            return Response(
                {"error": "Review not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = ClinicReviewSerializer(review, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, review_id, *args, **kwargs):
        """Delete a clinic review"""
        review = self.get_object(review_id)
        if not review:
            return Response(
                {"error": "Review not found"}, status=status.HTTP_404_NOT_FOUND
            )

        review.delete()
        return Response(
            {"message": "Review deleted successfully"},
            status=status.HTTP_204_NO_CONTENT,
        )


class ClinicReviewReplyListCreateAPIView(APIView):
    """
    API to list and create replies to a review.
    Requires authentication.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, review_id, *args, **kwargs):
        """List all replies for a specific review"""
        replies = ClinicReviewReply.objects.filter(review_id=review_id)
        serializer = ClinicReviewReplySerializer(replies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, review_id, *args, **kwargs):
        """Create a reply for a specific review"""
        try:
            review = ClinicReview.objects.get(pk=review_id)
        except ClinicReview.DoesNotExist:
            return Response(
                {"error": "Review not found"}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = ClinicReviewReplySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                user=request.user, review=review
            )  # Associate reply with the logged-in user
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClinicReviewStatsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            user = request.user

            stats = {"total_reviews": user.reviews, "average_score": user.rating}

            return Response(stats, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ActiveDoctorsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            user = request.user
            # Get all doctors of the clinic
            all_doctors = User.objects.filter(role="Doctor", work_place__user=user)
            total_doctors = all_doctors.count()

            # Get only active doctors (last activity within 30 minutes)
            thirty_minutes_ago = timezone.localtime().now() - timedelta(minutes=30)
            active_doctors = all_doctors.filter(last_activity__gte=thirty_minutes_ago)
            active_doctors_count = active_doctors.count()

            # Serialize active doctors
            serializer = ActiveDoctorSerializer(active_doctors, many=True)

            return Response(
                {
                    "total_doctors": total_doctors,
                    "active_doctors": active_doctors_count,
                    "active_doctors_list": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ClinicAppointmentStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get 'today' from request params (format: YYYY-MM-DD)
        today_param = request.GET.get("date", None)
        try:
            today = (
                datetime.strptime(today_param, "%Y-%m-%d").date()
                if today_param
                else datetime.now().date()
            )
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD."}, status=400
            )

        # Define start dates
        week_start = today.replace(day=1)  # Start of the current month
        week_end = today  # Until today
        month_start = today.replace(day=1)  # First day of this month

        # Default appointment data (set all counts to 0)
        appointment_data = {
            "booked": {"today": 0, "week": 0, "month": 0},
            "declined": {"today": 0, "week": 0, "month": 0},
            "completed": {"today": 0, "week": 0, "month": 0},
        }

        # Query database efficiently
        counts = (
            Appointment.objects.filter(
                clinic__user=request.user, date_time__date__gte=month_start
            )
            .values("status")
            .annotate(
                today=Count("id", filter=Q(date_time__date=today)),
                week=Count(
                    "id",
                    filter=Q(
                        date_time__date__gte=week_start, date_time__date__lte=week_end
                    ),
                ),
                month=Count("id"),
            )
        )

        # Status mapping from model to API response keys
        status_map = {
            "Confirmed": "booked",
            "Cancelled": "declined",
            "Completed": "completed",
        }

        # Update appointment data with actual counts
        for c in counts:
            key = status_map.get(c["status"])
            if key:
                appointment_data[key] = {
                    "today": c["today"],
                    "week": c["week"],
                    "month": c["month"],
                }

        # Format the final response
        result = {
            "booked_today_appointment": appointment_data["booked"]["today"],
            "booked_weekly_appointment": appointment_data["booked"]["week"],
            "booked_monthly_appointment": appointment_data["booked"]["month"],
            "declined_today_appointment": appointment_data["declined"]["today"],
            "declined_weekly_appointment": appointment_data["declined"]["week"],
            "declined_monthly_appointment": appointment_data["declined"]["month"],
            "completed_today_appointment": appointment_data["completed"]["today"],
            "completed_weekly_appointment": appointment_data["completed"]["week"],
            "completed_monthly_appointment": appointment_data["completed"]["month"],
        }

        return Response(result)


class ClinicAppointmentActivityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        date_param = request.query_params.get(
            "date", datetime.now().date().strftime("%Y-%m-%d")
        )
        activity_type = request.query_params.get("type", "month").lower()

        try:
            selected_date = datetime.strptime(date_param, "%Y-%m-%d").date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD."}, status=400
            )

        # Default response structure
        data = {}

        if activity_type == "day":
            start_date = selected_date - timedelta(days=selected_date.weekday())  # Start of the week (Monday)
            end_date = start_date + timedelta(days=6)  # End of the week (Sunday)
            date_format = "%Y-%m-%d"

            # Initialize default data for the entire week
            days_range = (end_date - start_date).days + 1  # Ensure full week

            for i in range(days_range):
                day_key = (start_date + timedelta(days=i)).strftime(date_format)
                data[day_key] = {
                    "name": (start_date + timedelta(days=i)).strftime("%d"),  # Day name
                    "Declined": 0,
                    "Completed": 0,
                    "Booked": 0,
                }

            # Query database for appointments within the week
            appointments = (
                Appointment.objects.filter(clinic__user=request.user, date_time__date__range=[start_date, end_date])
                .values("date_time__date", "status")
                .annotate(count=Count("id"))
            )

            # Populate actual data with appointment counts
            for entry in appointments:
                date_key = entry["date_time__date"].strftime(date_format)
                if entry["status"] == "Cancelled":
                    data[date_key]["Declined"] += entry["count"]
                elif entry["status"] == "Completed":
                    data[date_key]["Completed"] += entry["count"]
                elif entry["status"] == "Confirmed":
                    data[date_key]["Booked"] += entry["count"]

        elif activity_type == "week":
            start_date = selected_date.replace(day=1)  # First day of the month
            next_month = start_date.month % 12 + 1
            next_month_year = start_date.year + (1 if next_month == 1 else 0)
            end_date = start_date.replace(month=next_month, year=next_month_year, day=1) - timedelta(days=1)  # Last day of the month
            date_format = "%Y-%m-%d"

            # Calculate total weeks dynamically
            total_days = (end_date - start_date).days + 1
            total_weeks = (total_days + 6) // 7  # Ensure full weeks

            # Initialize default weeks
            for i in range(1, total_weeks + 1):
                week_key = f"Week {i}"
                data[week_key] = {
                    "name": week_key,
                    "Declined": 0,
                    "Completed": 0,
                    "Booked": 0,
                }

            # Query database for appointments within the month
            appointments = (
                Appointment.objects.filter(clinic__user=request.user, date_time__date__range=[start_date, end_date])
                .annotate(day=ExtractDay("date_time"))
                .values("day", "status")
                .annotate(count=Count("id"))
            )

            # Populate actual data with appointment counts
            for entry in appointments:
                week_number = (entry["day"] - 1) // 7 + 1  # Determine week number dynamically
                week_key = f"Week {week_number}"

                if entry["status"] == "Cancelled":
                    data[week_key]["Declined"] += entry["count"]
                elif entry["status"] == "Completed":
                    data[week_key]["Completed"] += entry["count"]
                elif entry["status"] == "Confirmed":
                    data[week_key]["Booked"] += entry["count"]

        elif activity_type == "month":
            start_date = selected_date.replace(month=1, day=1)  # Start of the year
            end_date = selected_date.replace(month=12, day=31)  # End of the year

            # Initialize default months
            for month in range(1, 13):
                month_key = datetime(2000, month, 1).strftime("%b")
                data[month_key] = {"name": month_key, "Declined": 0, "Completed": 0, "Booked": 0}

            # Query database
            appointments = (
                Appointment.objects.filter(
                    clinic__user=request.user,
                    date_time__date__range=[start_date, end_date]
                )
                .annotate(month=ExtractMonth("date_time"))
                .values("month", "status")
                .annotate(count=Count("id"))
            )

            # Populate actual data
            for entry in appointments:
                month_key = datetime(2000, entry["month"], 1).strftime("%b")
                if entry["status"] == "Cancelled":
                    data[month_key]["Declined"] += entry["count"]
                elif entry["status"] == "Completed":
                    data[month_key]["Completed"] += entry["count"]
                elif entry["status"] == "Confirmed":
                    data[month_key]["Booked"] += entry["count"]

        else:
            return Response(
                {"error": "Invalid type. Use 'day', 'week', or 'month'."}, status=400
            )

        return Response(list(data.values()))


class ClinicDoctorsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        try:
            user = request.user
            # Get all doctors of the clinic
            all_doctors = User.objects.filter(role="Doctor", work_place__user=user)
            serializer = ClinicDoctorSerializer(all_doctors, many=True)

            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ClinicReportRemoveDoctorAPIView(APIView):
    def post(self, request):
        """
        Allows a clinic to report a doctor.
        """
        doctor_id = request.data.get("doctor_id")
        reason = request.data.get("reason")

        if not doctor_id or not reason:
            return Response(
                {"error": "Doctor ID and reason are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            doctor = User.objects.get(id=doctor_id, role="Doctor")
        except User.DoesNotExist:
            return Response(
                {"error": "Doctor not found."}, status=status.HTTP_404_NOT_FOUND
            )

        # Send report email via SendGrid
        self.send_report_email(request.user, doctor, reason)

        return Response(
            {"message": "Doctor reported successfully."}, status=status.HTTP_201_CREATED
        )

    def delete(self, request, doctor_id):
        try:
            doctor = User.objects.get(
                id=doctor_id, work_place__user=request.user, role="Doctor"
            )
            doctor.work_place = None
            doctor.save()
            return Response(
                {"message": "Doctor removed successfully"},
                status=status.HTTP_204_NO_CONTENT,
            )
        except User.DoesNotExist:
            return Response(
                {"error": "Doctor not found in this clinic."},
                status=status.HTTP_404_NOT_FOUND,
            )

    def send_report_email(self, clinic, doctor, reason):
        """
        Sends a report email via SendGrid.
        """
        subject = f"Clinic Report: {doctor.get_full_name()} Reported by {clinic.get_full_name()}"

        content = f"""
        <h3>Doctor Report Details</h3>
        <p><strong>Clinic Name:</strong> {clinic.get_full_name()}</p>
        <p><strong>Clinic Email:</strong> {clinic.email}</p>
        <p><strong>Doctor Reported:</strong> {doctor.get_full_name()} ({doctor.email})</p>
        <p><strong>Reason for Report:</strong> {reason}</p>
        """

        message = Mail(
            from_email=settings.SENDGRID_FROM_EMAIL,
            to_emails=settings.REPORT_ADMIN_EMAIL,
            subject=subject,
            html_content=content,
        )

        try:
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            sg.send(message)
        except Exception as e:
            print("Error sending email:", e)


class ClinicCalendarAppointmentsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Filters appointments based on:
        - date: Specific date from request params (default: today)
        - type: day, week, or month
        """
        try:
            # Use timezone-aware current date
            today = now().date()
            start = request.query_params.get("start_date", today.isoformat())
            end = request.query_params.get("end_date", (today + timedelta(days=1)).isoformat())

            # Validate and convert string dates to date objects
            try:
                start_date = datetime.strptime(start, "%Y-%m-%d").date()
                end_date = datetime.strptime(end, "%Y-%m-%d").date()
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Query appointments within the given date range
            queryset = Appointment.objects.filter(
                clinic__user=request.user,
                date_time__date__range=[start_date, end_date]
            )

            serializer = CalendarAppointmentSerializer(queryset.order_by("date_time"), many=True)

            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
