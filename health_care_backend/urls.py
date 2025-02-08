"""health_care_backend URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # This includes the URLs from the 'authify' app
    path('auth/', include('authify.urls')),
    # Include the urls from the review app
    path('reviews/', include('reviews.urls')),
    # Include the urls from the dashboard app
    path('dashboard/', include('dashboard.urls')),
    # Include the urls from the doctors app
    path('doctors/', include('doctors.urls')),
    # Include the urls from the appointments app
    path('appointments/', include('appointments.urls')),
    # Include the urls from the payments app
    path('payment/', include('payments.urls')),
    # Include the urls from the user details
    path('user/', include('users.urls')),
    # Include the urls from the clinic details
    path('clinics/', include('clinics.urls'))

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
