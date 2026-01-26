from datetime import date, timedelta
from tenants.models import Client, Domain
from django.utils.text import slugify
from django.db import transaction

def create_shop_tenant(*, shop_name, owner, domain_url):
    from users.models import Shop

    with transaction.atomic():
        # 1️⃣ Create shop (public)
        shop = Shop.objects.create(
            name=shop_name,
            owner=owner
        )

        # 2️⃣ Create tenant
        schema_name = slugify(shop_name).replace('-', '_')

        tenant = Client.objects.create(
            name=shop_name,
            schema_name=schema_name,
            paid_until=date.today() + timedelta(days=14),  # ✅ FIX
            on_trial=True
        )

        # 3️⃣ Create domain
        Domain.objects.create(
            domain=domain_url,
            tenant=tenant,
            is_primary=True
        )

    return shop
