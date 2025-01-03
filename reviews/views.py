from rest_framework import generics
from rest_framework.response import Response
from .models import Review, Reply
from .serializers import ReviewSerializer, ReplySerializer
from rest_framework.views import APIView
from rest_framework import status, permissions
from appointments.models import Appointment
# Create your views here.

class ReviewPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

# create new review
    def post(self, request, *args, **kwargs):
        # Ensure the user is logged in and is a patient
        if not hasattr(request.user, 'patient'):
            # print(request.user,"--------------->>>>> request.user.patient")
            return Response(
                {"detail": "Only patients can create reviews."},
                status=status.HTTP_403_FORBIDDEN,
            )

        patient = request.user.patient
        # print(patient,"--------------->>>>>")
        serializer = ReviewSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            serializer.save(patient=patient)  # Automatically associate the patient
            # print(serializer.data,"--------------->>>>> serializer.data")
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
# view all reviews
    def get(self, request):
        user = self.request.user

        # If the user is a doctor, fetch all reviews for the doctor
        if hasattr(user, 'doctor'):
            doctor = user.doctor
            # print(doctor,"--------------->>>>> doctor")
            # Fetch all reviews for the doctor, including those created by other patients
            reviews = Review.objects.filter(doctor=doctor)
            serializer = ReviewSerializer(reviews, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # If the user is a patient, fetch all reviews created by the patient
        elif hasattr(user, 'patient'):
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
        # Ensure the review exists
        try:
            review = Review.objects.get(id=review_id)
        except Review.DoesNotExist:
            return Response({"detail": "Review not found."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        # Check if the user is a patient or doctor
        if hasattr(user, 'patient'):
            # Patient can reply if they have an active appointment with the doctor
            patient = user.patient
            doctor = review.doctor
            appointment = Appointment.objects.filter(patient=patient, doctor=doctor, status="Confirmed").exists()
            if not appointment:
                return Response(
                    {"detail": "You must have an active appointment with the doctor to reply."},
                    status=status.HTTP_403_FORBIDDEN
                )
        elif hasattr(user, 'doctor'):
            doctor = user.doctor
        else:
            return Response(
                {"detail": "Only doctors or patients can reply."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Create a reply for the review
        serializer = ReplySerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(review=review, user=user)  # Save the reply under the review
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, review_id, *args, **kwargs):
        # Fetch all replies for the review
        try:
            review = Review.objects.get(id=review_id)
        except Review.DoesNotExist:
            return Response({"detail": "Review not found."}, status=status.HTTP_404_NOT_FOUND)
        
        # Get the reviewer's name
        if hasattr(review, 'patient'):
            reviewer_name = review.patient.user.first_name
        elif hasattr(review, 'doctor'):
            reviewer_name = review.doctor.user.first_name
        else:
            reviewer_name = "Unknown"
            
        # Get all replies to the review
        replies = Reply.objects.filter(review=review).order_by('-created_at')
        serializer = ReplySerializer(replies, many=True)
        total_replies = replies.count()
        response_data = {
            'reviewer_name': reviewer_name,
            'total_replies': total_replies,
            'replies': serializer.data
            }
        return Response(response_data, status=status.HTTP_200_OK)    
    
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
