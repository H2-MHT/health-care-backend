from django.urls import path
from .views import(
    PatientListView,
    AddToFavouriteView,
    MedicalDocumentUploadView,
    MedicalDocumentUploadView,
    AddFamilyMemberView,
    VerifyFamilyMemberOTPAPIView,
    ListFavouriteDoctors,
    ListFavouriteClinics
)

urlpatterns = [
    path('', PatientListView.as_view()),
    path("favourite/", AddToFavouriteView.as_view(), name="add-to-favourites"),
    path('fav-doctor/', ListFavouriteDoctors.as_view(), name='fav_doc'),
    path('fav-clinic/', ListFavouriteClinics.as_view(), name='fav_clinic'),
    path("upload/medical-document/", MedicalDocumentUploadView.as_view(), name="upload-medical-document"),
    path("upload/allergy-document/", MedicalDocumentUploadView.as_view(), name="upload-allergy-document"),
    
    path("add-family-member/", AddFamilyMemberView.as_view(), name="add-family-member"),
    path("verify-family-member/", VerifyFamilyMemberOTPAPIView.as_view(), name="verify-family-member"),

]