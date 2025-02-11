from django.urls import path
from .views import (
    SignUpView,
    SignInView,
    GoogleLoginView,
    AppleLoginView,
    OTPVerificationView,
    ForgotPasswordView,
    ResendOTPView,
    ChangePasswordView,
    UpdateUserProfileAPIView,
    GetUserProfileAPIView,
    AccountDeactivateDeleteView,
)

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("signin/", SignInView.as_view(), name="signin"),
    path("verify-otp/", OTPVerificationView.as_view(), name="verify-otp"),
    path("forget-password/", ForgotPasswordView.as_view(), name="forget-password"),
    path("change-password/", ChangePasswordView.as_view(), name="change-update-password"),
    path('deactivate-account/', AccountDeactivateDeleteView.as_view(), name='deactivate-account'),
    path('delete-account/', AccountDeactivateDeleteView.as_view(), name='delete-account'),
    path("resend-otp/", ResendOTPView.as_view(), name="resend-otp"),
    path("login/google/", GoogleLoginView.as_view(), name="google-login"),
    path("login/apple/", AppleLoginView.as_view(), name="apple-login"),
    path("update-profile/", UpdateUserProfileAPIView.as_view(), name="update-profile"),
    path("view-profile/", GetUserProfileAPIView.as_view(), name="view-profile"),
]
