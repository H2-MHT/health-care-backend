from rest_framework import generics
from rest_framework.response import Response
from .models import Review, Reply
from .serializers import ReviewSerializer, ReplySerializer, ReviewUpdateSerializer
from rest_framework.views import APIView
from rest_framework import status, permissions
from doctors.models import Doctor
from appointments.models import Appointment
from rest_framework.generics import get_object_or_404
from patients.models import Patient
# Create your views here.

class ReviewPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    # Create a new review
    def post(self, request, *args, **kwargs):
        # Ensure the user is logged in and is a patient
        if not hasattr(request.user, 'patient'):
            return Response(
                {"detail": "Only patients can create reviews."},
                status=status.HTTP_400_BAD_REQUEST,
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
            return Response(
                {"message": "Review added successfully!", "data": serializer.data},
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        review_id = request.query_params.get('review_id')
        doctor_id = request.query_params.get('doctor_id')

        # If a specific review ID is provided, return that review
        if review_id:
            try:
                review = Review.objects.get(id=review_id)
                return Response(
                    {"message": "Review retrieved successfully!", "data": ReviewSerializer(review).data},
                    status=status.HTTP_200_OK
                )
            except Review.DoesNotExist:
                return Response({"detail": "Review not found"}, status=status.HTTP_404_NOT_FOUND)

        # If a doctor ID is provided, return all reviews for that doctor
        if doctor_id:
            reviews = Review.objects.filter(doctor__id=doctor_id)
            if not reviews:
                return Response({'message':' Does not have any review'}, status=status.HTTP_404_NOT_FOUND)
            serializer = ReviewSerializer(reviews, many=True)
            return Response(
                {"message": "Review retrieved successfully!", "data": serializer.data},
                status=status.HTTP_200_OK
            )

        # If the user is a patient, return all reviews they have written for different doctors
        if hasattr(request.user, 'patient'):
            patient = request.user.patient
            reviews = Review.objects.filter(patient=patient)
            serializer = ReviewSerializer(reviews, many=True)
            return Response(
                {"message": "Review retrieved successfully!", "data": serializer.data},
                status=status.HTTP_200_OK
            )

        # If the user is a doctor, return all reviews they have received from different patients
        if hasattr(request.user, 'doctor'):
            doctor = request.user.doctor
            reviews = Review.objects.filter(doctor=doctor)
            serializer = ReviewSerializer(reviews, many=True)
            return Response(
                {"message": "Review retrieved successfully!", "data": serializer.data},
                status=status.HTTP_200_OK
            )

        return Response({"detail": "Invalid request"}, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, review_id):
        if request.user.role != 'Patient':
            return Response({'message': 'only patients can update the review'}, status=status.HTTP_403_FORBIDDEN)

        try:
            review = Review.objects.get(id=review_id)
        except Review.DoesNotExist:
            return Response({'message': 'Review does not exist'}, status=status.HTTP_404_NOT_FOUND)

        patient = request.user.patient
        if review.patient != patient:
            return Response({'message': 'review does not belong to the requested user'},
                            status=status.HTTP_403_FORBIDDEN)
        serializer = ReviewUpdateSerializer(review, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Review updated successfully!", "data": serializer.data},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, review_id):
        if request.user.role != 'Patient':
            return Response({'message': 'only patients can update the review'}, status=status.HTTP_403_FORBIDDEN)

        try:
            review = Review.objects.get(id=review_id)
        except Review.DoesNotExist:
            return Response({'message': 'Review does not exist'}, status=status.HTTP_404_NOT_FOUND)

        patient = request.user.patient
        if review.patient != patient:
            return Response({'message': 'review does not belong to the requested user'}, status=status.HTTP_403_FORBIDDEN)

        review.delete()
        return Response({'message': 'Review deleted successfully'}, status=status.HTTP_200_OK)


class DoctorReviewsAPIView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReviewSerializer

    def get_queryset(self, doctor_id):
        try:
            # Filter reviews related to the specific doctor
            return Review.objects.filter(doctor_id=doctor_id)
        except Exception as e:
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def list(self, request, *args, **kwargs):
        try:

            if hasattr(request.user, 'Doctor'):
                return Response({'message': 'only associated doctor can view reviews'})

            doctor_id = request.user.doctor.id
            queryset = self.get_queryset(doctor_id)
            total_reviews = queryset.count()
            # Serialize the data
            serializer = self.get_serializer(queryset, many=True)
            response_data = {
                'total_reviews': total_reviews,
                'reviews': serializer.data
            }
            return Response(
                {"message": "Retrived successfully!", "data": response_data},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
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
        try:
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
                serializer.save(review=review, user=user)  # Save the reply under the review
                # Add the reply to the review's response
                review_data = ReviewSerializer(review).data
                review_data['replies'] = ReplySerializer(review.replies.all(), many=True).data
                # Return the review with the associated replies and user names

                return Response(
                    {"message": "Reply added!", "data": review_data},
                    status=status.HTTP_201_CREATED
                )

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # GET method to fetch reviews with replies and user details
    def get(self, request, *args, **kwargs):
        try:
            # Fetch all reviews
            review_id = request.query_params.get('review_id')
            if not review_id:
               return Response({'message': 'review id is missing'}, status=status.HTTP_400_BAD_REQUEST)

            try:
               review = Review.objects.get(id=review_id)
            except Review.DoesNotExist:
                return Response({'message': 'Review does not exist'}, status=status.HTTP_404_NOT_FOUND)

            user = request.user
            if hasattr(user, 'patient'):
                patient = user.patient
                # Check if the patient is the review owner
                if review.patient != patient:
                    return Response(
                        {"detail": "You do not have access for this"},
                        status=status.HTTP_403_FORBIDDEN
                    )

            elif hasattr(user, 'doctor'):
                doctor = user.doctor
                if review.doctor != doctor:
                    return Response(
                        {"detail": "You do not have access for this."},
                        status=status.HTTP_403_FORBIDDEN
                    )
            else:
                return Response(
                    {"detail": "Only patients or doctors can get replies."},
                    status=status.HTTP_403_FORBIDDEN
                )

            reviews_data = []
            review_data = ReviewSerializer(review).data
            replies_data = ReplySerializer(review.replies.all(), many=True).data
            # Add replies to each review's data
            review_data['replies'] = replies_data
            reviews_data.append(review_data)
            return Response(
                {"message": "Review retrieved successfully!", "data": review_data},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def put(self, request, reply_id):
        try:
            reply = Reply.objects.get(id=reply_id)
        except Reply.DoesNotExist:
            return Response({"detail": "Reply not found."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user

        # Ensure only the reply owner (doctor or patient) can update their own reply
        if reply.user != user:
            return Response({"detail": "You can only update your own reply."}, status=status.HTTP_403_FORBIDDEN)

        serializer = ReplySerializer(reply, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Reply updated successfully.", "data": serializer.data},
                            status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, reply_id):
        try:
            reply = Reply.objects.get(id=reply_id)
        except Reply.DoesNotExist:
            return Response({"detail": "Reply not found."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user

        # Ensure only the reply owner (doctor or patient) can delete their own reply
        if reply.user != user:
            return Response({"detail": "You can only delete your own reply."}, status=status.HTTP_403_FORBIDDEN)

        reply.delete()
        return Response({"message": "Reply deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
