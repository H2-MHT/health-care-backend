from rest_framework import generics, permissions
from rest_framework.response import Response
from .models import Notification
from .serializers import NotificationSerializer
from django.core.paginator import Paginator
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

class NotificationListView(APIView):
    """
    Retrieves notifications for the logged-in user.
    Supports filtering unread notifications and pagination.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user  # Get the logged-in user
            unread_only = request.GET.get("unread", "false").lower() == "true"  # Filter unread notifications
            page = request.GET.get("page", 1)  # Pagination

            # Get notifications (filter unread if requested)
            notifications = Notification.objects.filter(user=user, is_deleted=False).order_by("-created_at")
            if unread_only:
                notifications = notifications.filter(is_read=False)

            # Paginate results (10 notifications per page)
            paginator = Paginator(notifications, 10)
            page_obj = paginator.get_page(page)

            # Convert to JSON response
            data = [
                {
                    "id": notif.id,
                    "message": notif.message,
                    "created_at": notif.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "is_read": notif.is_read
                }
                for notif in page_obj
            ]

            return Response({
                "notifications": data,
                "page": page_obj.number,
                "total_pages": paginator.num_pages,
                "total_notifications": paginator.count
            }, status=200)

        except Exception as e:
            return Response({"error": str(e)}, status=400)


class MarkNotificationAsReadView(generics.UpdateAPIView):
    """
    API to mark a notification as read.
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        notification_id = kwargs.get("pk")
        notification = Notification.objects.filter(id=notification_id, user=request.user).first()

        if notification:
            notification.is_read = True
            notification.save()
            return Response({"success": True, "message": "Notification marked as read."})

        return Response({"success": False, "error": "Notification not found."}, status=404)

class DeleteNotificationView(generics.DestroyAPIView):
    """
    API to delete a notification.
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        notification_id = kwargs.get("pk")
        notification = Notification.objects.filter(id=notification_id, user=request.user).first()

        if notification:
            notification.is_deleted = True
            notification.save()
            return Response({"success": True, "message": "Notification deleted successfully."})

        return Response({"success": False, "error": "Notification not found."}, status=404)
