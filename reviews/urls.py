# urls.py
from django.urls import path
from .views import (DoctorReviewsAPIView,
                    AddReviewPIView,
                    ReplyAPIView,
)

urlpatterns = [
    path('doctor/<int:doctor_id>/', DoctorReviewsAPIView.as_view(), name='doctor-reviews'),
    # path('create/', AddReviewPIView.as_view(), name='review-create'),
    path('view-review/', AddReviewPIView.as_view(), name='review-view'),
    # reply to the specific review 
    path('replies/<int:review_id>/', ReplyAPIView.as_view(), name='reply-to-review'),
    # get a list of all the reviews and their replies 
    path('replies/', ReplyAPIView.as_view(), name='view-all-reply-to-review'),
    
]
