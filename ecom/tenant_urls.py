print("🎯 TENANT_URLS LOADED!")

"""
Tenant Schema URLs
These URLs are accessible within each tenant's schema (individual shops)
Each shop has its own isolated environment
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView


urlpatterns = [
    # Admin (Tenant-specific)
    path('admin/', admin.site.urls),
    
    # Main eccommence App (Fixed typo: eccommence -> eccommence)
    path('', include('eccommence.urls', namespace='eccommence')),
    
    # Cart
    path('cart/', include('cart.urls', namespace='cart')),
    
    # Payment & Orders
    path('payment/', include('payment.urls', namespace='payment')),

    #path('orders/', include('orders.urls', namespace='orders')),
    
    #Users (Authentication, Profile, Vendor Dashboard)
    path('users/', include('users.urls', namespace='users')),
    
    # API Endpoints (if you add REST API)
    # path('api/', include('api.urls', namespace='api')),
    
    # Wishlist shortcut
    path('wishlist/', RedirectView.as_view(url='/users/wishlist/', permanent=False)),
    
    # Search shortcut
    path('search/', RedirectView.as_view(url='/?q=', permanent=False)),

    # Shop Management Dashboard
    path('manage/', include('store_admin.urls', namespace='store_admin')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
