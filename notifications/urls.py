from django.urls import path
from .views import NotificationListView, MarkNotificationAsReadView, DeleteNotificationView

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    path("notification-read/<int:pk>/", MarkNotificationAsReadView.as_view(), name="notification-mark-read"),
    path("notification-delete/<int:pk>/", DeleteNotificationView.as_view(), name="notification-delete"),
]
