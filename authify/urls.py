from django.urls import path
from .views import (
    SignUpView,
    SignInView,
    GoogleLoginView,
    AppleLoginView,
    OTPVerificationView,
    ForgotPasswordView,
    ResendOTPView,
    VerifyEmailAndGenerateTokensView,
    ChangePasswordView, UserProfileUpdateView,
)

urlpatterns = [
    # Define your URL patterns here, for example:
    path("signup/", SignUpView.as_view(), name="signup"),
    path("signin/", SignInView.as_view(), name="signin"),
    path("verify-otp/", OTPVerificationView.as_view(), name="verify-otp"),
    path("forget-password/", ForgotPasswordView.as_view(), name="forget-password"),
    path("verify-email/", VerifyEmailAndGenerateTokensView.as_view(), name="verify-email-forget-password"),
    path("change-password/", ChangePasswordView.as_view(), name="change-update-password"),
    path("resend-otp/", ResendOTPView.as_view(), name="resend-otp"),
    path("login/google/", GoogleLoginView.as_view(), name="google-login"),
    path("login/apple/", AppleLoginView.as_view(), name="apple-login"),
    path("profile/update/", UserProfileUpdateView.as_view(), name="profile-update"),

]
