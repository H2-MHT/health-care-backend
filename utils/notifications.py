from notifications.models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()

def send_notification(user_id, message):
    """
    Sends an in-app notification to a user.
    """
    user = User.objects.filter(id=user_id).first()
    if user:
        Notification.objects.create(user=user, message=message)
        return True
    return False
