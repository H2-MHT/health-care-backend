from django.urls import path
from .views import(
    PatientListView,
    AddToFavouriteView,
    MedicalDocumentUploadView,
    MedicalDocumentUploadView,
)

urlpatterns = [
    path('', PatientListView.as_view()),
    path("favourite/", AddToFavouriteView.as_view(), name="add-to-favourites"),
    path("upload/medical-document/", MedicalDocumentUploadView.as_view(), name="upload-medical-document"),
    path("upload/allergy-document/", MedicalDocumentUploadView.as_view(), name="upload-allergy-document"),
]