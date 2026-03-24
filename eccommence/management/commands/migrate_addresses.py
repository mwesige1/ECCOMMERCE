# eccommence/management/commands/migrate_addresses.py
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.db import connection
from django_tenants.utils import get_tenant_model
from eccommence.models import Customer, Address
from users.models import Profile, User

User = get_user_model()

class Command(BaseCommand):
    help = 'Migrate addresses from Profile model to Address model for all tenants'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting address migration for all tenants...'))
        
        # Get all tenants
        tenants = get_tenant_model().objects.all()
        self.stdout.write(f"Found {tenants.count()} tenants")
        
        total_migrated = 0
        total_skipped = 0
        total_errors = 0
        
        # Run migration for each tenant
        for tenant in tenants:
            self.stdout.write(self.style.SUCCESS(f"\nProcessing tenant: {tenant.schema_name}"))
            
            # Switch to this tenant's schema
            connection.set_tenant(tenant)
            
            # Run the migration for this tenant
            migrated, skipped, errors = self.migrate_tenant()
            
            total_migrated += migrated
            total_skipped += skipped
            total_errors += errors
            
            self.stdout.write(f"  Tenant {tenant.schema_name}: {migrated} migrated, {skipped} skipped, {errors} errors")
        
        self.stdout.write(self.style.SUCCESS(
            f'\nMigration complete! Total: {total_migrated} addresses migrated, {total_skipped} skipped, {total_errors} errors.'
        ))
    
    def migrate_tenant(self):
        """Run migration for current tenant schema"""
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        # Get all users in this tenant
        users = User.objects.filter(is_active=True)
        
        for user in users:
            try:
                # Check if user has profile and customer profile
                if not hasattr(user, 'profile'):
                    skipped_count += 1
                    continue
                    
                profile = user.profile
                
                if not hasattr(user, 'customer_profile'):
                    skipped_count += 1
                    continue
                    
                customer = user.customer_profile
                
                # Check if profile has address data
                if profile.address1 or profile.city:
                    # Check if address already exists to avoid duplicates
                    existing = Address.objects.filter(
                        customer=customer,
                        address_type='shipping',
                        is_default=True
                    ).exists()
                    
                    if not existing:
                        # Create new address
                        address = Address.objects.create(
                            customer=customer,
                            address_type='shipping',
                            full_name=user.get_full_name() or user.email,
                            phone=user.phone or '',
                            address_line1=profile.address1 or '',
                            address_line2=profile.address2 or '',
                            city=profile.city or '',
                            state=profile.state or '',
                            postal_code=profile.zipcode or '',
                            country=profile.country or 'Uganda',
                            is_default=True
                        )
                        migrated_count += 1
                        self.stdout.write(self.style.SUCCESS(f"  ✓ Migrated address for {user.email}"))
                    else:
                        skipped_count += 1
                else:
                    skipped_count += 1
                        
            except Exception as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f"  ✗ Error for {user.email}: {str(e)}"))
        
        return migrated_count, skipped_count, error_count