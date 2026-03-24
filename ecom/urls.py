"""
Main URL Configuration
This is the ROOT_URLCONF - routes to either public or tenant URLs
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# This will be overridden by TENANT_URLCONF in settings
# But good to have as fallback
urlpatterns = [
    path('admin/', admin.site.urls),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)