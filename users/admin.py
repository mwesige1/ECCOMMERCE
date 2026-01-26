from django.contrib import admin
from .forms import ShopAdminForm
from django.contrib.auth.models import User
from .models import Shop
from.services import create_shop_tenant




# Register your models here.
@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    form = ShopAdminForm
    list_display=('name','owner','created_at','is_active')
    

    def save_model(self,request,obj,form,change):
        if not change:
            create_shop_tenant(
                shop_name=form.cleaned_data['name'],
                owner=form.cleaned_data['owner'],
                domain_url=form.cleaned_data['domain']
            )
        else:
            super().save_model(request,obj,form,change)