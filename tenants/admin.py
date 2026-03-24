from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum
from django_tenants.admin import TenantAdminMixin
from .models import Client, Domain, TenantSubscription, TenantActivity


# ============= INLINE ADMINS =============

class DomainInline(admin.TabularInline):
    model = Domain
    extra = 1
    fields = ('domain', 'is_primary', 'is_verified', 'ssl_enabled')
    readonly_fields = ('is_verified',)


class TenantSubscriptionInline(admin.TabularInline):
    model = TenantSubscription
    extra = 0
    fields = ('invoice_number', 'plan', 'amount', 'status', 'payment_date')
    readonly_fields = ('invoice_number', 'plan', 'amount', 'status', 'payment_date')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


# ============= CLIENT (TENANT) ADMIN =============

@admin.register(Client)
class ClientAdmin(TenantAdminMixin, admin.ModelAdmin):
    list_display = (
        'name', 'schema_name', 'subscription_badge',
        'plan_badge', 'products_usage', 'storage_usage',
        'is_active', 'days_remaining', 'created_at'
    )
    list_filter = (
        'subscription_status', 'subscription_plan',
        'on_trial', 'is_active', 'is_verified', 'created_at'
    )
    search_fields = (
        'name', 'schema_name', 'owner_email',
        'owner_name', 'business_email'
    )
    readonly_fields = (
        'schema_name', 'created_at', 'updated_at',
        'total_products', 'total_orders', 'total_revenue',
        'storage_used_mb', 'days_until_expiry'
    )
    
    inlines = [DomainInline, TenantSubscriptionInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name', 'schema_name', 'description',
                'is_active', 'is_verified'
            )
        }),
        ('Owner Information', {
            'fields': (
                'owner_name', 'owner_email', 'owner_phone'
            )
        }),
        ('Subscription', {
            'fields': (
                'subscription_plan', 'subscription_status',
                'on_trial', 'trial_end_date', 'paid_until',
                'last_payment_date', 'days_until_expiry'
            )
        }),
        ('Limits & Features', {
            'fields': (
                'max_products', 'max_storage_mb', 'max_orders_per_month',
                'max_staff_accounts', 'can_use_custom_domain',
                'can_use_analytics', 'can_export_data', 'can_use_api'
            ),
            'classes': ('collapse',)
        }),
        ('Business Information', {
            'fields': (
                'business_address', 'business_phone', 'business_email',
                'business_registration_number', 'tax_id'
            ),
            'classes': ('collapse',)
        }),
        ('Branding', {
            'fields': (
                'logo', 'primary_color', 'secondary_color'
            ),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': (
                'total_products', 'total_orders', 'total_revenue',
                'storage_used_mb'
            ),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': (
                'currency', 'timezone', 'language',
                'email_notifications_enabled', 'sms_notifications_enabled'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [
        'activate_tenants', 'suspend_tenants',
        'extend_trial', 'upgrade_to_basic', 'upgrade_to_premium'
    ]
    
    def subscription_badge(self, obj):
        colors = {
            'active': '#198754',
            'trial': '#0dcaf0',
            'expired': '#dc3545',
            'suspended': '#6c757d',
            'cancelled': '#dc3545',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            colors.get(obj.subscription_status, '#999'),
            obj.get_subscription_status_display()
        )
    
    subscription_badge.short_description = 'Status'
    
    def plan_badge(self, obj):
        colors = {
            'free': '#6c757d',
            'basic': '#0d6efd',
            'premium': '#fd7e14',
            'enterprise': '#6f42c1',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.subscription_plan, '#999'),
            obj.get_subscription_plan_display()
        )
    
    plan_badge.short_description = 'Plan'
    
    def products_usage(self, obj):
        if obj.max_products == -1:
            percentage = 0
            text = f'{obj.total_products} / Unlimited'
        else:
            percentage = (obj.total_products / obj.max_products * 100) if obj.max_products > 0 else 0
            text = f'{obj.total_products} / {obj.max_products}'
        
        color = '#dc3545' if percentage >= 90 else '#fd7e14' if percentage >= 75 else '#198754'
        
        return format_html(
            '<span style="color: {};">{}</span>',
            color, text
        )
    
    products_usage.short_description = 'Products'
    
    def storage_usage(self, obj):
        if obj.max_storage_mb == -1:
            percentage = 0
            text = f'{obj.storage_used_mb} MB / Unlimited'
        else:
            percentage = (obj.storage_used_mb / obj.max_storage_mb * 100) if obj.max_storage_mb > 0 else 0
            text = f'{obj.storage_used_mb} / {obj.max_storage_mb} MB'
        
        color = '#dc3545' if percentage >= 90 else '#fd7e14' if percentage >= 75 else '#198754'
        
        return format_html(
            '<span style="color: {};">{}</span>',
            color, text
        )
    
    storage_usage.short_description = 'Storage'
    
    def days_remaining(self, obj):
        days = obj.days_until_expiry
        
        if days < 0:
            return format_html('<span style="color: #dc3545;">Expired</span>')
        elif days <= 7:
            return format_html('<span style="color: #fd7e14;">{} days</span>', days)
        else:
            return format_html('<span style="color: #198754;">{} days</span>', days)
    
    days_remaining.short_description = 'Days Left'
    
    # Actions
    def activate_tenants(self, request, queryset):
        queryset.update(is_active=True, subscription_status='active')
        self.message_user(request, f'{queryset.count()} tenants activated.')
    
    activate_tenants.short_description = "Activate selected tenants"
    
    def suspend_tenants(self, request, queryset):
        queryset.update(is_active=False, subscription_status='suspended')
        self.message_user(request, f'{queryset.count()} tenants suspended.')
    
    suspend_tenants.short_description = "Suspend selected tenants"
    
    def extend_trial(self, request, queryset):
        from django.utils import timezone
        from datetime import timedelta
        
        for tenant in queryset:
            tenant.trial_end_date = timezone.now().date() + timedelta(days=14)
            tenant.paid_until = timezone.now().date() + timedelta(days=14)
            tenant.save()
        
        self.message_user(request, f'Trial extended for {queryset.count()} tenants.')
    
    extend_trial.short_description = "Extend trial by 14 days"
    
    def upgrade_to_basic(self, request, queryset):
        for tenant in queryset:
            tenant.upgrade_plan('basic')
        
        self.message_user(request, f'{queryset.count()} tenants upgraded to Basic.')
    
    upgrade_to_basic.short_description = "Upgrade to Basic Plan"
    
    def upgrade_to_premium(self, request, queryset):
        for tenant in queryset:
            tenant.upgrade_plan('premium')
        
        self.message_user(request, f'{queryset.count()} tenants upgraded to Premium.')
    
    upgrade_to_premium.short_description = "Upgrade to Premium Plan"


# ============= DOMAIN ADMIN =============

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = (
        'domain', 'tenant', 'is_primary', 'is_verified',
        'ssl_enabled', 'created_at'
    )
    list_filter = ('is_primary', 'is_verified', 'ssl_enabled', 'created_at')
    search_fields = ('domain', 'tenant__name')
    readonly_fields = ('created_at', 'updated_at', 'verified_at')
    
    fieldsets = (
        ('Domain Information', {
            'fields': ('tenant', 'domain', 'is_primary')
        }),
        ('Verification', {
            'fields': ('is_verified', 'verification_code', 'verified_at')
        }),
        ('SSL Configuration', {
            'fields': ('ssl_enabled', 'ssl_certificate', 'ssl_expires_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# ============= TENANT SUBSCRIPTION ADMIN =============

@admin.register(TenantSubscription)
class TenantSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'invoice_number', 'tenant', 'plan', 'amount_display',
        'status_badge', 'payment_date', 'subscription_period'
    )
    list_filter = ('status', 'plan', 'billing_period', 'payment_date')
    search_fields = ('invoice_number', 'tenant__name', 'transaction_id')
    readonly_fields = ('invoice_number', 'created_at', 'updated_at')
    date_hierarchy = 'payment_date'
    
    fieldsets = (
        ('Tenant', {
            'fields': ('tenant',)
        }),
        ('Payment Details', {
            'fields': (
                'invoice_number', 'amount', 'currency',
                'plan', 'billing_period', 'status'
            )
        }),
        ('Payment Gateway', {
            'fields': (
                'payment_method', 'transaction_id',
                'gateway_response', 'payment_date'
            )
        }),
        ('Subscription Period', {
            'fields': ('subscription_start', 'subscription_end')
        }),
        ('Additional', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    def amount_display(self, obj):
        return format_html(
            '<strong>{} {:,.2f}</strong>',
            obj.currency, obj.amount
        )
    
    amount_display.short_description = 'Amount'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'completed': '#198754',
            'failed': '#dc3545',
            'refunded': '#6f42c1',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.status, '#999'),
            obj.get_status_display()
        )
    
    status_badge.short_description = 'Status'
    
    def subscription_period(self, obj):
        return f"{obj.subscription_start} to {obj.subscription_end}"
    
    subscription_period.short_description = 'Period'


# ============= TENANT ACTIVITY ADMIN =============

@admin.register(TenantActivity)
class TenantActivityAdmin(admin.ModelAdmin):
    list_display = (
        'tenant', 'activity_type', 'description_short',
        'performed_by', 'created_at'
    )
    list_filter = ('activity_type', 'created_at')
    search_fields = ('tenant__name', 'description', 'performed_by')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    
    def description_short(self, obj):
        return obj.description[:100] + '...' if len(obj.description) > 100 else obj.description
    
    description_short.short_description = 'Description'