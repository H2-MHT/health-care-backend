# urls.py
from django.urls import path
from .views import (DoctorReviewsAPIView,
                    ReviewPIView,
                    ReplyAPIView,
                    ReportAPIView,
)

urlpatterns = [
    # create review
    path('review/', ReviewPIView.as_view(), name='review'),
    # update review
    path('review/', ReviewPIView.as_view(), name='review-update-delete'),
    # reply to the specific review
    path('replies/<int:review_id>/', ReplyAPIView.as_view(), name='reply-to-review'),
    # delete reply
    path('delete-update-reply/<int:reply_id>/', ReplyAPIView.as_view(), name='delete-update-reply'),
    # get a list of all the reviews and their replies
    path('replies/', ReplyAPIView.as_view(), name='view-all-reply-to-review'),
    # get a list of all the reviews related to the specific doctor
    path('doctor/', DoctorReviewsAPIView.as_view(), name='doctor-reviews'),
    path("report-sumbit/", ReportAPIView.as_view(), name="report-sumbit"),


]
