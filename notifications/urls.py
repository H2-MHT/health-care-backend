from django.urls import path
from .views import NotificationListView, MarkNotificationAsReadView, DeleteNotificationView

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification-list"),
    # path("notifications/<int:pk>/read/", MarkNotificationAsReadView.as_view(), name="notification-mark-read"),
    # path("notifications/<int:pk>/delete/", DeleteNotificationView.as_view(), name="notification-delete"),
]
