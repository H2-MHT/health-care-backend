from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.fitbit_login, name='home'),
    path('fitbit-data/', views.fitbit_data, name='fitbit-data'),
    path("callback", views.fitbit_callback, name="fitbit_callback"),
]