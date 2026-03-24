"""
Custom storage backend for tenant-specific media files
Each tenant's media files are stored in their own directory
"""
import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import connection
from pathlib import Path


class TenantMediaStorage(FileSystemStorage):
    """
    Storage backend that isolates media files per tenant
    Files are stored in: MEDIA_ROOT/tenant_schema_name/
    """
    
    def __init__(self, *args, **kwargs):
        # DON'T initialize location/base_url here
        # We'll do it in _get_tenant_paths() at runtime
        super().__init__(*args, **kwargs)
    
    def _get_tenant_paths(self):
        """Get tenant-specific paths at runtime"""
        tenant = getattr(connection, "tenant", None)
        
        if tenant and hasattr(tenant, 'schema_name') and tenant.schema_name != 'public':
            location = os.path.join(settings.MEDIA_ROOT, tenant.schema_name)
            base_url = f"{settings.MEDIA_URL}{tenant.schema_name}/"
            Path(location).mkdir(parents=True, exist_ok=True)
        else:
            location = os.path.join(settings.MEDIA_ROOT, 'public')
            base_url = f"{settings.MEDIA_URL}public/"
            Path(location).mkdir(parents=True, exist_ok=True)
        
        return location, base_url
    
    def path(self, name):
        location, _ = self._get_tenant_paths()
        self.location = location
        return super().path(name)
    
    def url(self, name):
        location, base_url = self._get_tenant_paths()
        self.location = location
        self.base_url = base_url
        return super().url(name)
    
    def _save(self, name, content):
        location, base_url = self._get_tenant_paths()
        self.location = location
        self.base_url = base_url
        return super()._save(name, content)


class TenantStaticStorage(FileSystemStorage):
    """
    Optional: Storage backend for tenant-specific static files
    Useful if tenants can upload custom CSS, logos, etc.
    """
    
    def __init__(self, *args, **kwargs):
        tenant = getattr(connection, "tenant", None)
        
        if tenant and hasattr(tenant, 'schema_name'):
            location = os.path.join(
                settings.STATIC_ROOT,
                'tenants',
                tenant.schema_name
            )
            base_url = f"{settings.STATIC_URL}tenants/{tenant.schema_name}/"
            
            # Ensure directory exists
            Path(location).mkdir(parents=True, exist_ok=True)
        else:
            location = settings.STATIC_ROOT
            base_url = settings.STATIC_URL
        
        super().__init__(location=location, base_url=base_url, *args, **kwargs)