import os
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import connection

class TenantMediaStorage(FileSystemStorage):
    def __init__(self, *args, **kwargs):
        tenant = getattr(connection, "tenant", None)

        if tenant:
            location = os.path.join(
                settings.MEDIA_ROOT,
                tenant.schema_name
            )
            base_url = f"{settings.MEDIA_URL}{tenant.schema_name}/"
        else:
            location = settings.MEDIA_ROOT
            base_url = settings.MEDIA_URL

        super().__init__(location=location, base_url=base_url)



