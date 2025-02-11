from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.response import Response
from clinics.models import *
from clinics.serializers import *
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Count, Avg, Q
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
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
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

        week_start = today - timedelta(
            days=today.weekday()
        )  # Start of this week (Monday)
        week_end = week_start + timedelta(days=6)  # Sunday
        month_start = today.replace(day=1)  # Start of this month

        # Single query: Aggregate appointment counts
        counts = (
            Appointment.objects.select_related("clinic")
            .filter(clinic__user=request.user, date_time__date__gte=month_start)
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

        # Directly construct response dict using dictionary comprehension
        result = {
            "booked": next(
                (c for c in counts if c["status"] == "Pending"),
                {"today": 0, "week": 0, "month": 0},
            ),
            "declined": next(
                (c for c in counts if c["status"] == "Cancelled"),
                {"today": 0, "week": 0, "month": 0},
            ),
            "completed": next(
                (c for c in counts if c["status"] == "Completed"),
                {"today": 0, "week": 0, "month": 0},
            ),
        }

        return Response(result)


class ClinicAppointmentActivityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        reference_year = int(request.GET.get("year", datetime.today().year))

        counts = (
            Appointment.objects.select_related("clinic")
            .filter(clinic__user=request.user, date_time__year=reference_year)
            .values("date_time__month", "status")
            .annotate(count=Count("id"))
        )

        # Define month names
        month_names = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]

        # Initialize response
        monthly_data = {
            month: {"booked": 0, "completed": 0, "declined": 0} for month in month_names
        }

        # Populate the data
        for entry in counts:
            month = month_names[entry["date_time__month"] - 1]
            status = entry["status"]
            count = entry["count"]

            if status == "Pending":
                monthly_data[month]["booked"] = count
            elif status == "Completed":
                monthly_data[month]["completed"] = count
            elif status == "Cancelled":
                monthly_data[month]["declined"] = count

        return Response(monthly_data)
