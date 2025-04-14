from django.urls import path
from .views import (
    SignUpView,
    SignInView,
    LogoutView,
    GoogleLoginView,
    AppleLoginView,
    OTPVerificationView,
    ForgotPasswordView,
    ResendOTPView,
    ChangePasswordView,
    ResetPasswordView,
    UpdateUserProfileAPIView,
    DeleteProfilePictureAPIView,
    GetUserProfileAPIView,
    AccountDeactivateDeleteView,
    UserDeviceTokenAPIView,
)

urlpatterns = [
    path("signup/", SignUpView.as_view(), name="signup"),
    path("signin/", SignInView.as_view(), name="signin"),
    path("logout/", LogoutView.as_view(), name="Logout"),
    # password reset
    path("forget-password/", ForgotPasswordView.as_view(), name="forget-password"),
    path("verify-otp/", OTPVerificationView.as_view(), name="verify-otp"),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    # update password
    path("change-password/", ChangePasswordView.as_view(), name="change-update-password"),
    path('deactivate-account/', AccountDeactivateDeleteView.as_view(), name='deactivate-account'),
    path('delete-account/', AccountDeactivateDeleteView.as_view(), name='delete-account'),
    path("resend-otp/", ResendOTPView.as_view(), name="resend-otp"),
    path("login/google/", GoogleLoginView.as_view(), name="google-login"),
    path("login/apple/", AppleLoginView.as_view(), name="apple-login"),
    path("update-profile/", UpdateUserProfileAPIView.as_view(), name="update-profile"),
    path('delete-profile-picture/', DeleteProfilePictureAPIView.as_view(), name='delete-profile-picture'),
    
    # firebase device token
    path('firebase-device-token/', UserDeviceTokenAPIView.as_view(), name='firebase-device-token'),

    path("view-profile/", GetUserProfileAPIView.as_view(), name="view-profile"),
]
