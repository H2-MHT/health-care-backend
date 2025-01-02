# urls.py
from django.urls import path
from .views import (DoctorReviewsAPIView,
                    ReviewPIView,
                    # ReplyAPIView,
)

urlpatterns = [
    path('doctor/<int:doctor_id>/', DoctorReviewsAPIView.as_view(), name='doctor-reviews'),
    path('create/', ReviewPIView.as_view(), name='review-create'),
    path('view-review/', ReviewPIView.as_view(), name='review-create'),
    # path('replies/<int:review_id>/', ReplyAPIView.as_view(), name='reply-to-review'),

]
