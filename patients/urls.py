from django.urls import path
from .views import (
    PatientListView,
    AddToFavouriteView,
    MedicalDocumentUploadView,
    MedicalDocumentUploadView,
    AddFamilyMemberView,
    VerifyFamilyMemberOTPAPIView,
    UpdateFamilyMemberView,
    ListFavouriteDoctors,
    ListFavouriteClinics,
    GetFamilyMembersView,
    AllergyDocumentUploadView,
)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', PatientListView.as_view()),
    path("favourite/", AddToFavouriteView.as_view(), name="add-to-favourites"),
    path('fav-doctor/', ListFavouriteDoctors.as_view(), name='fav_doc'),
    path('fav-clinic/', ListFavouriteClinics.as_view(), name='fav_clinic'),
    path("upload/medical-document/", MedicalDocumentUploadView.as_view(), name="upload-medical-document"),
    path("upload/medical-document/<int:pk>/", MedicalDocumentUploadView.as_view(), name="upload-medical-document"),
    path("upload/allergy-document/",AllergyDocumentUploadView.as_view(), name="upload-allergy-document"),
    path("upload/allergy-document/<int:pk>/", AllergyDocumentUploadView.as_view(), name="upload-allergy-document"),
    path("add-family-member/", AddFamilyMemberView.as_view(), name="add-family-member"),
    path("verify-family-member/", VerifyFamilyMemberOTPAPIView.as_view(), name="verify-family-member"),
    path('update-family-member/', UpdateFamilyMemberView.as_view(), name='update-family-member'),
    path('get-family-members/', GetFamilyMembersView.as_view(), name='get-family-members'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)