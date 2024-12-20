from django.shortcuts import render
from rest_framework.response import Response

# Create your views here.
from rest_framework import generics
from rest_framework.response import Response
from .models import Review
from .serializers import ReviewSerializer

class DoctorReviewsAPIView(generics.ListAPIView):
    serializer_class = ReviewSerializer

    def get_queryset(self):
        # using the the Doctor id from the URL
        doctor_id = self.kwargs.get('doctor_id')
        print(doctor_id,"--------------------")
        # Filter reviews related to the specific doctor
        return Review.objects.filter(doctor_id=doctor_id)

    def list(self, request, *args, **kwargs):
        # Get the queryset (reviews related to the specified doctor)
        queryset = self.get_queryset()
        print(queryset,"------------------")
        total_reviews = queryset.count()
        # Serialize the data
        serializer = self.get_serializer(queryset, many=True)
        print(serializer,"----------------------------------")
        response_data = {
            'total_reviews': total_reviews,
            'reviews': serializer.data
        }

        return Response(response_data)
