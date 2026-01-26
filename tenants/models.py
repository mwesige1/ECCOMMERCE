from django.db import models
from django_tenants.models import TenantMixin,DomainMixin

# Create your models here.

class Client(TenantMixin):
    name = models.CharField(max_length=255) # shop name
    paid_until = models.DateField() # subscription end 
    on_trial = models.BooleanField(default=True) # Trial status
    created_at= models.DateTimeField(auto_now_add=True) # creation date/joined date
    auto_create_schema = True # automatically create a schema after creation

    def __str__(self):
        return self.name
    
class Domain(DomainMixin):
    pass

