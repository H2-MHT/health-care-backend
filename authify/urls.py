from django.urls import path
from .views import (
    SignUpView,
    SignInView,
    GoogleLoginView,
    AppleLoginView,
    OTPVerificationView,
    ForgotPasswordView,
    ResetPasswordView,
    ResendOTPView,
)

urlpatterns = [
    # Define your URL patterns here, for example:
    path("signup/", SignUpView.as_view(), name="signup"),
    path("signin/", SignInView.as_view(), name="signin"),
    path("verify-otp/", OTPVerificationView.as_view(), name="verify-otp"),
    path("forget-password/", ForgotPasswordView.as_view(), name="forget-password"),
    path("reset-password/", ResetPasswordView.as_view(), name="reset-password"),
    path("resend-otp/", ResendOTPView.as_view(), name="resend-otp"),
    path("login/google/", GoogleLoginView.as_view(), name="google-login"),
    path("login/apple/", AppleLoginView.as_view(), name="apple-login"),
]
