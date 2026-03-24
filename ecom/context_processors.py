"""
Context processors to add variables to all templates
"""
from django.conf import settings
from django.db import connection


def site_settings(request):
    """Add site-wide settings to context"""
    return {
        'SITE_NAME': getattr(settings, 'SITE_NAME', 'Homies'),
        'SITE_URL': getattr(settings, 'FRONTEND_URL', 'http://localhost:8000'),
        'DEBUG': settings.DEBUG,
    }


def tenant_context(request):
    """Add tenant information to context"""
    tenant = getattr(connection, 'tenant', None)
    
    if tenant and hasattr(tenant, 'schema_name'):
        return {
            'tenant': tenant,
            'tenant_name': tenant.name,
            'tenant_schema': tenant.schema_name,
            'is_tenant': True,
        }
    
    return {
        'tenant': None,
        'is_tenant': False,
    }