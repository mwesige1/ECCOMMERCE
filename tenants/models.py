from django.db import models
from django.core.validators import MinValueValidator
from django_tenants.models import TenantMixin, DomainMixin
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal


class Client(TenantMixin):
    """
    Tenant (Shop) model - Each tenant represents a separate shop/store
    """
    
    SUBSCRIPTION_PLANS = (
        ('free', 'Free Plan'),
        ('basic', 'Basic Plan'),
        ('premium', 'Premium Plan'),
        ('enterprise', 'Enterprise Plan'),
    )
    
    SUBSCRIPTION_STATUS = (
        ('active', 'Active'),
        ('trial', 'Trial'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
    )
    
    # Basic Information
    name = models.CharField(max_length=255, help_text="Shop/Store name")
    description = models.TextField(blank=True)
    
    # Owner Information
    owner_email = models.EmailField(blank=True)
    owner_phone = models.CharField(max_length=20, blank=True)
    owner_name = models.CharField(max_length=255, blank=True)
    
    # Subscription
    subscription_plan = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_PLANS,
        default='free'
    )
    subscription_status = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_STATUS,
        default='trial'
    )
    paid_until = models.DateField(
        help_text="Subscription end date"
    )
    on_trial = models.BooleanField(default=True)
    trial_end_date = models.DateField(null=True, blank=True)
    
    # Limits (based on plan)
    max_products = models.IntegerField(
        default=100,
        validators=[MinValueValidator(0)],
        help_text="Maximum number of products allowed"
    )
    max_storage_mb = models.IntegerField(
        default=1000,
        validators=[MinValueValidator(0)],
        help_text="Maximum storage in MB"
    )
    max_orders_per_month = models.IntegerField(
        default=1000,
        validators=[MinValueValidator(0)],
        help_text="Maximum orders per month"
    )
    
    # Features (based on plan)
    can_use_custom_domain = models.BooleanField(default=False)
    can_use_analytics = models.BooleanField(default=True)
    can_export_data = models.BooleanField(default=True)
    can_use_api = models.BooleanField(default=False)
    max_staff_accounts = models.IntegerField(default=3)
    
    # Business Information
    business_address = models.TextField(blank=True)
    business_phone = models.CharField(max_length=20, blank=True)
    business_email = models.EmailField(blank=True)
    business_registration_number = models.CharField(max_length=100, blank=True)
    tax_id = models.CharField(max_length=50, blank=True)
    
    # Branding
    logo = models.ImageField(upload_to='tenant_logos/', blank=True, null=True)
    primary_color = models.CharField(max_length=7, default='#007bff')
    secondary_color = models.CharField(max_length=7, default='#6c757d')
    
    # Status
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    
    # Statistics
    total_products = models.IntegerField(default=0)
    total_orders = models.IntegerField(default=0)
    total_revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    storage_used_mb = models.IntegerField(default=0)
    
    # Settings
    currency = models.CharField(max_length=3, default='UGX')
    timezone = models.CharField(max_length=50, default='Africa/Kampala')
    language = models.CharField(max_length=10, default='en')
    
    # Notifications
    email_notifications_enabled = models.BooleanField(default=True)
    sms_notifications_enabled = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_payment_date = models.DateTimeField(null=True, blank=True)
    
    # Django-tenants required field
    auto_create_schema = True
    auto_drop_schema = False  # Safety: don't auto-delete schemas
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Tenant (Shop)'
        verbose_name_plural = 'Tenants (Shops)'
    
    def __str__(self):
        return f"{self.name} ({self.schema_name})"
    
    def save(self, *args, **kwargs):
        # Set trial end date if on trial
        if self.on_trial and not self.trial_end_date:
            self.trial_end_date = timezone.now().date() + timedelta(days=14)
        
        # Update subscription status based on dates
        today = timezone.now().date()
        
        if self.on_trial:
            if self.trial_end_date and today > self.trial_end_date:
                self.subscription_status = 'expired'
                self.on_trial = False
            else:
                self.subscription_status = 'trial'
        elif today > self.paid_until:
            self.subscription_status = 'expired'
        else:
            self.subscription_status = 'active'
        
        super().save(*args, **kwargs)
    
    @property
    def is_subscription_active(self):
        """Check if subscription is active"""
        return self.subscription_status in ['active', 'trial']
    
    @property
    def days_until_expiry(self):
        """Days remaining until subscription expires"""
        if self.on_trial and self.trial_end_date:
            return (self.trial_end_date - timezone.now().date()).days
        return (self.paid_until - timezone.now().date()).days
    
    @property
    def products_remaining(self):
        """Remaining product slots"""
        return max(0, self.max_products - self.total_products)
    
    @property
    def storage_remaining_mb(self):
        """Remaining storage in MB"""
        return max(0, self.max_storage_mb - self.storage_used_mb)
    
    @property
    def is_at_product_limit(self):
        """Check if at product limit"""
        return self.total_products >= self.max_products
    
    @property
    def is_at_storage_limit(self):
        """Check if at storage limit"""
        return self.storage_used_mb >= self.max_storage_mb
    
    def extend_subscription(self, days=30):
        """Extend subscription by specified days"""
        if self.on_trial:
            self.paid_until = timezone.now().date() + timedelta(days=days)
            self.on_trial = False
        else:
            self.paid_until += timedelta(days=days)
        
        self.last_payment_date = timezone.now()
        self.subscription_status = 'active'
        self.save()
    
    def upgrade_plan(self, plan):
        """Upgrade subscription plan"""
        plan_limits = {
            'free': {
                'max_products': 100,
                'max_storage_mb': 1000,
                'max_orders_per_month': 1000,
                'max_staff_accounts': 3,
                'can_use_custom_domain': False,
                'can_use_api': False,
            },
            'basic': {
                'max_products': 500,
                'max_storage_mb': 5000,
                'max_orders_per_month': 5000,
                'max_staff_accounts': 10,
                'can_use_custom_domain': True,
                'can_use_api': True,
            },
            'premium': {
                'max_products': 2000,
                'max_storage_mb': 20000,
                'max_orders_per_month': 20000,
                'max_staff_accounts': 50,
                'can_use_custom_domain': True,
                'can_use_api': True,
            },
            'enterprise': {
                'max_products': -1,  # Unlimited
                'max_storage_mb': -1,  # Unlimited
                'max_orders_per_month': -1,  # Unlimited
                'max_staff_accounts': -1,  # Unlimited
                'can_use_custom_domain': True,
                'can_use_api': True,
            },
        }
        
        if plan in plan_limits:
            limits = plan_limits[plan]
            self.subscription_plan = plan
            
            for key, value in limits.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            
            self.save()
    
    def suspend(self, reason=''):
        """Suspend tenant"""
        self.subscription_status = 'suspended'
        self.is_active = False
        self.save()
    
    def reactivate(self):
        """Reactivate suspended tenant"""
        if self.days_until_expiry > 0:
            self.subscription_status = 'active'
            self.is_active = True
            self.save()


class Domain(DomainMixin):
    """
    Domain model - Manages domains/subdomains for tenants
    """
    
    # Additional fields beyond DomainMixin
    is_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=100, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # SSL Configuration
    ssl_enabled = models.BooleanField(default=False)
    ssl_certificate = models.TextField(blank=True)
    ssl_expires_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_primary', 'domain']
    
    def __str__(self):
        primary = " (Primary)" if self.is_primary else ""
        return f"{self.domain}{primary} - {self.tenant.name}"


class TenantSubscription(models.Model):
    """
    Subscription payment history
    """
    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )
    
    tenant = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='subscription_payments'
    )
    
    # Payment Details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='UGX')
    plan = models.CharField(max_length=20)
    billing_period = models.CharField(
        max_length=20,
        choices=[
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('annually', 'Annually'),
        ]
    )
    
    # Status
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    # Payment Gateway
    payment_method = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=200, blank=True)
    gateway_response = models.JSONField(blank=True, null=True)
    
    # Dates
    payment_date = models.DateTimeField(null=True, blank=True)
    subscription_start = models.DateField()
    subscription_end = models.DateField()
    
    # Metadata
    invoice_number = models.CharField(max_length=50, unique=True, blank=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.tenant.name} - {self.plan} - {self.invoice_number}"
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            import uuid
            self.invoice_number = f"INV-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class TenantActivity(models.Model):
    """
    Track tenant activities and events
    """
    ACTIVITY_TYPES = (
        ('created', 'Tenant Created'),
        ('subscription_renewed', 'Subscription Renewed'),
        ('subscription_upgraded', 'Subscription Upgraded'),
        ('subscription_cancelled', 'Subscription Cancelled'),
        ('suspended', 'Tenant Suspended'),
        ('reactivated', 'Tenant Reactivated'),
        ('domain_added', 'Domain Added'),
        ('domain_verified', 'Domain Verified'),
        ('plan_changed', 'Plan Changed'),
        ('payment_received', 'Payment Received'),
        ('payment_failed', 'Payment Failed'),
    )
    
    tenant = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    description = models.TextField()
    metadata = models.JSONField(blank=True, null=True)
    
    # User who performed action (if applicable)
    performed_by = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Tenant Activities'
    
    def __str__(self):
        return f"{self.tenant.name} - {self.get_activity_type_display()}"