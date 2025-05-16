from rest_framework import generics
from rest_framework.response import Response
from .models import Review, Reply, Report
from .serializers import ReviewSerializer, ReplySerializer, ReviewUpdateSerializer, ReportSerializer
from rest_framework.views import APIView
from rest_framework import status, permissions
from doctors.models import Doctor, BookedAppointment
from appointments.models import Appointment
from rest_framework.generics import get_object_or_404
from patients.models import Patient
from utils.pagination import pagination_view, create_paginated_response
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
# Create your views here.

class ReviewPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    # Create a new review
    def post(self, request, *args, **kwargs):
        # Ensure the user is logged in and is a patient
        if not hasattr(request.user, 'patient_profile'):
            return Response(
                {"detail": "Only patients can create reviews."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        patient = request.user.patient_profile
        doctor_id = request.data.get('doctor_user_id')  # doctor ID is passed in the request data

        if not doctor_id:
            return Response(
                {"detail": "Doctor ID is required to create a review."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        appointment_id = request.data.get('appointment_id')
        try:
            appointment = BookedAppointment.objects.get(pk=appointment_id)
        except BookedAppointment.DoesNotExist:
            return Response(
                {"detail": "The specified appointment does not exist."},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        appointment_in_review = Review.objects.filter(
           appointment=appointment
        )
        
        if appointment_in_review.exists():
            return Response(
                {"detail": "You have already reviewed this appointment."},
                status=status.HTTP_400_BAD_REQUEST,
            )


        try:
            # Verify if the doctor exists
            doctor = Doctor.objects.get(user__id=doctor_id)

            # Check if the patient has any appointment with this doctor
            has_any_appointment = BookedAppointment.objects.filter(
            patient=request.user.id,  # patient is saved as user.id
            doctor=doctor.user.id,    # doctor is also saved as user.id
            status="Completed"
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
            
        data = request.data.copy()
        data.pop('doctor', None)
        
        # Proceed with review creation
        serializer = ReviewSerializer(data=data, context={'request': request})

        if serializer.is_valid():
            serializer.save(patient=patient, doctor=doctor, appointment=appointment)
            return Response(
                {"message": "Review added successfully!", "data": serializer.data},
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
       
        if not hasattr(request.user, 'patient_profile'):
            return Response({'message': 'Only patient can view reviews'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            patient = request.user.patient_profile          
            search_key = request.query_params.get("search_key", "").strip()
            if search_key:
                search_words = search_key.split()

                if len(search_words) == 2:
                    first_name, last_name = search_words
                    reviews = Review.objects.filter(
                        patient=patient,
                        doctor__user__first_name__istartswith=first_name,
                        doctor__user__last_name__istartswith=last_name
                    )
                else:
                    reviews = Review.objects.filter(patient=patient, status__in=["Pending", "Approved"], doctor__user__first_name__istartswith=search_key) | \
                              Review.objects.filter(patient=patient, status__in=["Pending", "Approved"], doctor__user__last_name__istartswith=search_key)

            else:
                reviews = Review.objects.filter(patient=patient, is_deleted=False, status__in=["Pending", "Approved"]).order_by('-created_at')
            paginated_data, headers = pagination_view(reviews, request)
            serializer = ReviewSerializer(paginated_data, many=True)
            return create_paginated_response("Review retrieved successfully!", serializer.data, headers)
        except Exception as e:
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        review_id = request.query_params.get("review_id")

        if not review_id:
            return Response({'message': 'Review ID is required in query parameters'}, status=status.HTTP_400_BAD_REQUEST)
        
        if request.user.role != 'Patient':
            return Response({'message': 'only patients can update the review'}, status=status.HTTP_403_FORBIDDEN)

        try:
            review = Review.objects.get(id=review_id)
        except Review.DoesNotExist:
            return Response({'message': 'Review does not exist'}, status=status.HTTP_404_NOT_FOUND)

        patient = request.user.patient_profile
        if review.patient != patient:
            return Response({'message': 'review does not belong to the requested user'},
                            status=status.HTTP_403_FORBIDDEN)
        
        if review.status == "Approved":
            return Response({'message': "You can't update this review as it is published"}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = ReviewUpdateSerializer(review, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Review updated successfully!", "data": serializer.data},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_200_OK)

    def delete(self, request):
        if request.user.role != 'Patient':
            return Response({'message': 'only patients can update the review'}, status=status.HTTP_403_FORBIDDEN)
        
        review_id = request.data.get("review_id")
        if not review_id:
            return Response({'message': 'Review ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            review = Review.objects.get(id=review_id)
        except Review.DoesNotExist:
            return Response({'message': 'Review does not exist'}, status=status.HTTP_404_NOT_FOUND)

        patient = request.user.patient_profile
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
            return Review.objects.filter(doctor_id=doctor_id, is_deleted=False, status='Approved').order_by('-created_at')
        except Exception as e:
            return Response(
                {"message": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def list(self, request, *args, **kwargs):
        try:
            # Ensure only the associated doctor can view reviews
            if hasattr(request.user, 'Doctor'):
                return Response({'message': 'Only associated doctor can view reviews'},
                                status=status.HTTP_403_FORBIDDEN)

            doctor_id = request.user.doctor.id
            queryset = self.get_queryset(doctor_id)

            search_query = request.query_params.get("search")
            if search_query:
                queryset = queryset.filter(title__istartswith=search_query)

            # Pagination Parameters
            if 'limit' not in request.query_params:
                raise ValidationError({"error": "The 'limit' query parameter is required."})
            if 'page' not in request.query_params:
                raise ValidationError({"error": "The 'page' query parameter is required."})

            try:
                per_page_results = int(request.query_params.get('limit'))
                page = int(request.query_params.get('page'))
                if page < 1:
                    raise ValidationError({"error": "'page' must be 1 or greater."})
            except ValueError:
                raise ValidationError({"error": "'limit' and 'page' must be valid integers."})

            # Apply pagination
            paginated_data, headers = pagination_view(queryset, request)

            # Serialize paginated results
            serializer = self.get_serializer(paginated_data, many=True)

            response_data = {
                'total_reviews': queryset.count(),
                'reviews': serializer.data
            }

            return create_paginated_response("Retrieved successfully!", response_data, headers)

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
            user = request.user
            try:
                review = Review.objects.get(id=review_id)
            except Review.DoesNotExist:
                    return Response({"detail": "Review not found."}, status=status.HTTP_404_NOT_FOUND)
            
            if review.is_closed:
                return Response(
                    {"detail": "This discussion has been closed by an admin."},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            patient = getattr(user, 'patient_profile', None)
            doctor = Doctor.objects.filter(user=user).first()
            if patient:
                if review.patient != patient:
                    return Response(
                        {"detail": "Only the review owner or the associated doctor can reply."},
                        status=status.HTTP_403_FORBIDDEN
                    )

            elif doctor:
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

            # Check if user is a patient
            patient = getattr(user, 'patient_profile', None)
            doctor = Doctor.objects.filter(user=user).first()

            if patient:
                if review.patient != patient:
                    return Response(
                        {"detail": "You do not have access to this review."},
                                    status=status.HTTP_403_FORBIDDEN
                                    )
                
                # Check if user is a doctor
            elif doctor:
                if review.doctor != doctor:
                    return Response(
                        {"detail": "You do not have access to this review."},
                                    status=status.HTTP_403_FORBIDDEN
                                )
            else:
                return Response(
                    {"detail": "Only patients or doctors can get replies."},
                    status=status.HTTP_403_FORBIDDEN
                )

            review_data = ReviewSerializer(review).data
            review_data['replies'] = ReplySerializer(review.replies.all(), many=True).data



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
        
        if reply.is_approved:
            return Response({"detail": "You can not update approved reply."}, status=status.HTTP_403_FORBIDDEN)

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

class ReportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            data = request.data.copy()
            review_id = data.get("review_id")
            
            try:
                review = Review.objects.get(id=review_id)
            except Review.DoesNotExist:
                return Response({"detail": "Review not found"}, status=status.HTTP_404_NOT_FOUND)

            report = Report.objects.create(
                review=review,
                reported_by=request.user,
                reason=data.get("reason")
            )

            serializer = ReportSerializer(report)
            return Response({"message": "Report submitted successfully", "report": serializer.data}, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    def get(self, request):
        try:
            report = Report.objects.filter(reported_by=request.user)
            serializer = ReportSerializer(report, many=True)
            return Response({"data": serializer.data}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)