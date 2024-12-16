from django.urls import path
from .views import SignUpView, SignInView, GoogleLoginView, AppleLoginView, ResetPasswordView, OTPVerificationView

urlpatterns = [
    # Define your URL patterns here, for example:
    path('signup/', SignUpView.as_view(), name='signup'),
    path('signin/', SignInView.as_view(), name='signin'),
    path('verify-otp/', OTPVerificationView.as_view(), name='verify-otp'),
    path('login/google/', GoogleLoginView.as_view(), name='google-login'),
    path('login/apple/', AppleLoginView.as_view(), name='apple-login'),
    path('password-reset/', ResetPasswordView.as_view(), name='password_reset'),

]
