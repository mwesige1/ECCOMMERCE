import logging

logger = logging.getLogger(__name__)


class ForceTenantURLConfMiddleware:
    """Force tenant URLconf to be used"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # If tenant is detected, force the tenant URLconf
        if hasattr(request, 'tenant'):
            from django.conf import settings
            request.urlconf = settings.TENANT_URLCONF
            print(f"🔧 FORCED urlconf to: {request.urlconf}")
        
        return self.get_response(request)

class DebugTenantMiddleware:
    """Debug middleware to track tenant detection"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        print(f"🔍 REQUEST HOST: {request.get_host()}")
        
        response = self.get_response(request)
        
        if hasattr(request, 'tenant'):
            print(f"✅ TENANT DETECTED: {request.tenant.schema_name}")
            print(f"📂 request.urlconf: {getattr(request, 'urlconf', 'Not set')}")
            
            # Check what URLconf is actually being used
            from django.urls import get_urlconf
            print(f"🔗 get_urlconf(): {get_urlconf()}")
            
            # Check settings
            from django.conf import settings
            print(f"⚙️  ROOT_URLCONF: {settings.ROOT_URLCONF}")
            print(f"⚙️  TENANT_URLCONF: {settings.TENANT_URLCONF}")
        else:
            print(f"❌ NO TENANT DETECTED")
        
        print("---")
        return response


class TenantSubscriptionMiddleware:
    """Placeholder for subscription checking"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        return self.get_response(request)


class TenantLimitMiddleware:
    """Placeholder for limit checking"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        return self.get_response(request)
