from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.response import Response
from clinics.models import *
from clinics.serializers import *
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Count, Avg, Q
from django.db.models.functions import ExtractDay, ExtractMonth, ExtractYear
from django.utils import timezone
from datetime import timedelta, datetime
from appointments.models import Appointment
from users.serializers import UserSerializer

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
                    "data": serializer.data
                    },
                    status=status.HTTP_200_OK
                    )
            return Response(
                {
                    "error": "Invalid data provided.", "details": serializer.errors},
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
        reviews = ClinicReview.objects.all()
        serializer = ClinicReviewSerializer(reviews, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        """Create a new clinic review"""
        serializer = ClinicReviewSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                doctor=request.user.doctor
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
            stats = ClinicReview.objects.filter(clinic__user=request.user).aggregate(
                total_reviews=Count("id"), average_score=Avg("rating")
            )

            if stats["total_reviews"] == 0:
                return Response(
                    {"error": "No reviews found for this clinic"},
                    status=status.HTTP_404_NOT_FOUND,
                )

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
            thirty_minutes_ago = timezone.now() - timedelta(minutes=30)
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
            "Pending": "booked",
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
            start_date = selected_date - timedelta(
                days=4
            )  # Last 5 days including today
            end_date = selected_date
            date_format = "%Y-%m-%d"

            # Initialize default data for last 5 days
            for i in range(5):
                day_key = (start_date + timedelta(days=i)).strftime(date_format)
                data[day_key] = {"name": f"0{i+1}", "red": 0, "green": 0, "blue": 0}

            # Query database
            appointments = (
                Appointment.objects.filter(
                    date_time__date__range=[start_date, end_date]
                )
                .values("date_time__date", "status")
                .annotate(count=Count("id"))
            )

            # Populate actual data
            for entry in appointments:
                date_key = entry["date_time__date"].strftime(date_format)
                print(date_key, entry)
                if entry["status"] == "Cancelled":
                    data[date_key]["red"] += entry["count"]
                elif entry["status"] == "Completed":
                    data[date_key]["green"] += entry["count"]
                elif entry["status"] == "Confirmed":
                    data[date_key]["blue"] += entry["count"]

        elif activity_type == "week":
            start_date = selected_date.replace(day=1)  # First day of the month
            end_date = start_date.replace(
                month=start_date.month % 12 + 1, day=1
            ) - timedelta(
                days=1
            )  # Last day of the month

            # Initialize default weeks
            for i in range(1, 5):
                week_key = f"Week {i}"
                data[week_key] = {"name": week_key, "red": 0, "green": 0, "blue": 0}

            # Query database
            appointments = (
                Appointment.objects.filter(
                    date_time__date__range=[start_date, end_date]
                )
                .annotate(day=ExtractDay("date_time"))
                .values("day", "status")
                .annotate(count=Count("id"))
            )

            # Populate actual data
            for entry in appointments:
                week_number = (entry["day"] - 1) // 7 + 1  # Custom week calculation
                week_key = f"Week {week_number}"

                if entry["status"] == "Cancelled":
                    data[week_key]["red"] += entry["count"]
                elif entry["status"] == "Completed":
                    data[week_key]["green"] += entry["count"]
                elif entry["status"] == "Confirmed":
                    data[week_key]["blue"] += entry["count"]

        elif activity_type == "month":
            start_date = selected_date.replace(month=1, day=1)  # Start of the year
            end_date = selected_date.replace(month=12, day=31)  # End of the year

            # Initialize default months
            for month in range(1, 13):
                month_key = datetime(2000, month, 1).strftime("%b")
                data[month_key] = {"name": month_key, "red": 0, "green": 0, "blue": 0}

            # Query database
            appointments = (
                Appointment.objects.filter(
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
                    data[month_key]["red"] += entry["count"]
                elif entry["status"] == "Completed":
                    data[month_key]["green"] += entry["count"]
                elif entry["status"] == "Confirmed":
                    data[month_key]["blue"] += entry["count"]

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
