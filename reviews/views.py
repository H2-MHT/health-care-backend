from rest_framework import generics
from rest_framework.response import Response
from .models import Review, Reply
from .serializers import ReviewSerializer, ReplySerializer
from rest_framework.views import APIView
from rest_framework import status, permissions
from doctors.models import Doctor
from appointments.models import Appointment
from rest_framework.generics import get_object_or_404
from patients.models import Patient
# Create your views here.

class AddReviewPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    # Create a new review
    def post(self, request, *args, **kwargs):
        # Ensure the user is logged in and is a patient
        if not hasattr(request.user, 'patient'):
            return Response(
                {"detail": "Only patients can create reviews."},
                status=status.HTTP_403_FORBIDDEN,
            )

        patient = request.user.patient
        doctor_id = request.data.get('doctor')  # doctor ID is passed in the request data

        if not doctor_id:
            return Response(
                {"detail": "Doctor ID is required to create a review."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Verify if the doctor exists
            doctor = Doctor.objects.get(id=doctor_id)

            # Check if the patient has any appointment with this doctor
            has_any_appointment = Appointment.objects.filter(
                patient=patient, doctor=doctor
            ).exists()

            if not has_any_appointment:
                return Response(
                    {"detail": "You can only review doctors you have had an appointment with."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        except Doctor.DoesNotExist:
            return Response(
                {"detail": "The specified doctor does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Proceed with review creation
        serializer = ReviewSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            serializer.save(patient=patient)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
# view all reviews
    def get(self, request):
        user = self.request.user
        doctor_id = request.query_params.get("doctor_id")
        patient_id = request.query_params.get("patient_id")

        # Fetch reviews by doctor_id if provided
        if doctor_id:
            doctor = get_object_or_404(Doctor, id=doctor_id)
            reviews = Review.objects.filter(doctor=doctor)
            serializer = ReviewSerializer(reviews, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Fetch reviews by patient_id if provided
        if patient_id:
            patient = get_object_or_404(Patient, id=patient_id)
            reviews = Review.objects.filter(patient=patient)
            serializer = ReviewSerializer(reviews, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # If the user is a doctor, fetch all reviews for the doctor
        if hasattr(user, "doctor"):
            doctor = user.doctor
            reviews = Review.objects.filter(doctor=doctor)
            serializer = ReviewSerializer(reviews, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # If the user is a patient, fetch all reviews created by the patient
        elif hasattr(user, "patient"):
            patient = user.patient
            reviews = Review.objects.filter(patient=patient)
            serializer = ReviewSerializer(reviews, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # If the user is neither a doctor nor a patient
        return Response(
            {"detail": "Only doctors or patients can view reviews."},
            status=status.HTTP_403_FORBIDDEN,
        )

class ReplyAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, review_id, *args, **kwargs):
        # Check if the review exists
        try:
            review = Review.objects.get(id=review_id)
        except Review.DoesNotExist:
            return Response({"detail": "Review not found."}, status=status.HTTP_404_NOT_FOUND)
        user = request.user
        # Check if the user is the review owner (patient) or the associated doctor
        if hasattr(user, 'patient'):
            patient = user.patient
            # Check if the patient is the review owner
            if review.patient != patient:
                return Response(
                    {"detail": "Only the review owner or the associated doctor can reply."},
                    status=status.HTTP_403_FORBIDDEN
                )
        elif hasattr(user, 'doctor'):
            doctor = user.doctor
            # Check if the doctor associated with the review is replying
            if review.doctor != doctor:
                return Response(
                    {"detail": "Only the review owner or the associated doctor can reply."},
                    status=status.HTTP_403_FORBIDDEN
                )
        else:
            return Response(
                {"detail": "Only patients or doctors can reply."},
                status=status.HTTP_403_FORBIDDEN
            )
        # Reply for the review
        serializer = ReplySerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            reply = serializer.save(review=review, user=user)  # Save the reply under the review
            # Add the reply to the review's response
            review_data = ReviewSerializer(review).data
            review_data['replies'] = ReplySerializer(review.replies.all(), many=True).data
            # Return the review with the associated replies and user names
            return Response(review_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    # GET method to fetch reviews with replies and user details
    
    def get(self, request, *args, **kwargs):
        # Fetch all reviews
        reviews = Review.objects.all()

        # Serialize reviews and their replies
        reviews_data = []
        for review in reviews:
            review_data = ReviewSerializer(review).data
            replies_data = ReplySerializer(review.replies.all(), many=True).data

            # Add replies to each review's data
            review_data['replies'] = replies_data
            reviews_data.append(review_data)

        return Response(reviews_data, status=status.HTTP_200_OK)
    
    
class DoctorReviewsAPIView(generics.ListAPIView):
    serializer_class = ReviewSerializer

    def get_queryset(self):
        # using the Doctor id from the URL
        doctor_id = self.kwargs.get('doctor_id')
        # Filter reviews related to the specific doctor
        return Review.objects.filter(doctor_id=doctor_id)

    def list(self, request, *args, **kwargs):
        # Get the queryset (reviews related to the specified doctor)
        queryset = self.get_queryset()
        total_reviews = queryset.count()
        # Serialize the data
        serializer = self.get_serializer(queryset, many=True)
        response_data = {
            'total_reviews': total_reviews,
            'reviews': serializer.data
        }

        return Response(response_data)
