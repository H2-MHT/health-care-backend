from django.utils.deprecation import MiddlewareMixin

class ActivityMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated:
            request.user.update_activity()
