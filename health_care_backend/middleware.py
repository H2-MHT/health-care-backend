import logging
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication

# Configure logger
logger = logging.getLogger(__name__)

class ActivityMiddleware(MiddlewareMixin):
    def process_request(self, request):
        user = None
        
        # Check SessionAuthentication
        if request.user.is_authenticated:
            user = request.user

        # Check JWTAuthentication
        else:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                jwt_auth = JWTAuthentication()
                try:
                    validated_user, _ = jwt_auth.authenticate(request)
                    user = validated_user
                except Exception as e:
                    logger.warning(f"JWT Authentication failed: {e}")

        # Update user activity if authenticated
        if user:
            user.last_activity = timezone.localtime().now()
            user.save(update_fields=['last_activity'])
            logger.info(f"User {user.username} activity updated at {user.last_activity}.")
