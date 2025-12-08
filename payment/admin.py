from django.contrib import admin
from .models import ShippingAddress,OrderItem,Order


# Register your models here.
admin.site.register(ShippingAddress)
admin.site.register(OrderItem)
admin.site.register(Order)

