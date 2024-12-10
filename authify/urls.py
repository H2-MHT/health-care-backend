from django.urls import path
from .views import SignupView, SigninView

urlpatterns = [
    # Define your URL patterns here, for example:
    path('signup/', SignupView.as_view(), name='signup'),
    path('signin/', SigninView.as_view(), name='signin'),
]
