# ecom/tenant_urls.py

from django.urls import path, include
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('eccommence.urls')),
    path('users/', include('users.urls')),  # ✅ ADD THIS
    path('cart/',include('cart.urls')),
    path('payment/',include('payment.urls')),


]


urlpatterns += static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT
)
