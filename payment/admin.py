from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum
from decimal import Decimal
from .models import (
    ShippingAddress, Order, OrderItem, 
    PaymentTransaction, PaymentMethod, Refund
)


# ============= INLINE ADMINS =============

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = (
        'product', 'product_variant', 'vendor', 'product_name',
        'product_sku', 'quantity', 'price', 'total',
        'commission', 'vendor_payout'
    )
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


# ============= SHIPPING ADDRESS ADMIN =============

@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = (
        'shipping_full_name', 'user', 'shipping_email',
        'shipping_city', 'shipping_country', 'is_default', 'created_at'
    )
    list_filter = ('is_default', 'shipping_country', 'created_at')
    search_fields = (
        'shipping_full_name', 'shipping_email', 'shipping_phone',
        'user__email', 'shipping_city'
    )
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Contact Information', {
            'fields': ('shipping_full_name', 'shipping_email', 'shipping_phone')
        }),
        ('Address', {
            'fields': (
                'shipping_address1', 'shipping_address2', 'shipping_city',
                'shipping_state', 'shipping_zipcode', 'shipping_country'
            )
        }),
        ('Additional', {
            'fields': ('delivery_instructions', 'is_default'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# ============= ORDER ADMIN =============

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number', 'full_name', 'email', 'status_badge',
        'is_paid', 'total_display', 'items_count', 'created_at'
    )
    list_filter = ('status', 'is_paid', 'payment_method', 'created_at')
    search_fields = (
        'order_number', 'full_name', 'email', 'phone',
        'user__email'
    )
    readonly_fields = (
        'order_number', 'subtotal', 'shipping_cost', 'tax',
        'discount', 'total', 'created_at', 'updated_at'
    )
    date_hierarchy = 'created_at'
    
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'status', 'created_at')
        }),
        ('Customer Details', {
            'fields': ('full_name', 'email', 'phone')
        }),
        ('Addresses', {
            'fields': ('shipping_address', 'billing_address')
        }),
        ('Pricing', {
            'fields': ('subtotal', 'shipping_cost', 'tax', 'discount', 'total')
        }),
        ('Payment', {
            'fields': ('payment_method', 'is_paid', 'paid_at')
        }),
        ('Shipping', {
            'fields': ('tracking_number', 'shipped_at', 'delivered_at'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('customer_note', 'admin_note', 'coupon_code'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_paid', 'mark_as_processing', 'mark_as_shipped', 'mark_as_delivered']
    
    def status_badge(self, obj):
        colors = {
            'pending': '#6c757d',
            'payment_failed': '#dc3545',
            'paid': '#198754',
            'processing': '#0d6efd',
            'shipped': '#fd7e14',
            'delivered': '#198754',
            'cancelled': '#dc3545',
            'refunded': '#6f42c1',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#999'),
            obj.get_status_display()
        )
    
    status_badge.short_description = 'Status'
    
    def total_display(self, obj):
        """Display total amount with proper formatting"""
        try:
            # Get the raw field value from the database
            total_value = obj.__dict__.get('total', obj.total)
            
            # Convert to Decimal if it's a string or SafeString
            if isinstance(total_value, (str, type(format_html('')))):
                # Remove formatting if present
                clean_value = str(total_value).replace('UGX', '').replace(',', '').strip()
                total_value = Decimal(clean_value) if clean_value else Decimal('0')
            
            # Ensure it's a Decimal
            if not isinstance(total_value, Decimal):
                total_value = Decimal(str(total_value))
            
            return format_html(
                '<strong style="color: #059669; font-size: 14px;">UGX {:,.0f}</strong>',
                total_value
            )
        except (ValueError, TypeError, AttributeError):
            return format_html('<strong>UGX 0</strong>')
    
    total_display.short_description = 'Total'
    
    def items_count(self, obj):
        return obj.items.count()
    
    items_count.short_description = 'Items'
    
    def mark_as_paid(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(is_paid=True, paid_at=timezone.now(), status='paid')
        self.message_user(request, f'{updated} orders marked as paid.')
    
    mark_as_paid.short_description = "Mark as paid"
    
    def mark_as_processing(self, request, queryset):
        updated = queryset.update(status='processing')
        self.message_user(request, f'{updated} orders marked as processing.')
    
    mark_as_processing.short_description = "Mark as processing"
    
    def mark_as_shipped(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status='shipped', shipped_at=timezone.now())
        self.message_user(request, f'{updated} orders marked as shipped.')
    
    mark_as_shipped.short_description = "Mark as shipped"
    
    def mark_as_delivered(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status='delivered', delivered_at=timezone.now())
        self.message_user(request, f'{updated} orders marked as delivered.')
    
    mark_as_delivered.short_description = "Mark as delivered"


# ============= ORDER ITEM ADMIN =============

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = (
        'order', 'product_name', 'vendor', 'quantity',
        'price', 'total_display', 'commission_display', 'vendor_payout_display'
    )
    list_filter = ('vendor', 'created_at')
    search_fields = ('product_name', 'product_sku', 'order__order_number')
    readonly_fields = ('total', 'commission', 'vendor_payout', 'created_at', 'updated_at')
    
    def total_display(self, obj):
        """Display total with proper formatting"""
        try:
            total_value = obj.__dict__.get('total', obj.total)
            if isinstance(total_value, (str, type(format_html('')))):
                clean_value = str(total_value).replace('UGX', '').replace(',', '').strip()
                total_value = Decimal(clean_value) if clean_value else Decimal('0')
            if not isinstance(total_value, Decimal):
                total_value = Decimal(str(total_value))
            return format_html('<strong>UGX {:,.0f}</strong>', total_value)
        except (ValueError, TypeError, AttributeError):
            return format_html('<strong>UGX 0</strong>')
    
    total_display.short_description = 'Total'
    
    def commission_display(self, obj):
        """Display commission with proper formatting"""
        try:
            commission_value = obj.__dict__.get('commission', obj.commission)
            if isinstance(commission_value, (str, type(format_html('')))):
                clean_value = str(commission_value).replace('UGX', '').replace(',', '').strip()
                commission_value = Decimal(clean_value) if clean_value else Decimal('0')
            if not isinstance(commission_value, Decimal):
                commission_value = Decimal(str(commission_value))
            return format_html('<span style="color: #dc3545;">UGX {:,.0f}</span>', commission_value)
        except (ValueError, TypeError, AttributeError):
            return format_html('<span style="color: #dc3545;">UGX 0</span>')
    
    commission_display.short_description = 'Commission'
    
    def vendor_payout_display(self, obj):
        """Display vendor payout with proper formatting"""
        try:
            payout_value = obj.__dict__.get('vendor_payout', obj.vendor_payout)
            if isinstance(payout_value, (str, type(format_html('')))):
                clean_value = str(payout_value).replace('UGX', '').replace(',', '').strip()
                payout_value = Decimal(clean_value) if clean_value else Decimal('0')
            if not isinstance(payout_value, Decimal):
                payout_value = Decimal(str(payout_value))
            return format_html('<span style="color: #198754;">UGX {:,.0f}</span>', payout_value)
        except (ValueError, TypeError, AttributeError):
            return format_html('<span style="color: #198754;">UGX 0</span>')
    
    vendor_payout_display.short_description = 'Vendor Payout'


# ============= PAYMENT TRANSACTION ADMIN =============

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'transaction_id', 'order', 'payment_gateway',
        'amount_display', 'status_badge', 'customer_email', 'initiated_at'
    )
    list_filter = ('status', 'payment_gateway', 'initiated_at')
    search_fields = (
        'transaction_id', 'order__order_number', 'customer_email',
        'gateway_transaction_id', 'gateway_reference'
    )
    readonly_fields = (
        'transaction_id', 'gateway_response', 'initiated_at',
        'completed_at', 'created_at', 'updated_at'
    )
    date_hierarchy = 'initiated_at'
    
    fieldsets = (
        ('Transaction Info', {
            'fields': ('transaction_id', 'order', 'status', 'initiated_at', 'completed_at')
        }),
        ('Payment Details', {
            'fields': (
                'payment_gateway', 'gateway_transaction_id', 'gateway_reference',
                'amount', 'currency'
            )
        }),
        ('Customer Details', {
            'fields': ('customer_email', 'customer_phone', 'customer_name', 'ip_address')
        }),
        ('Response', {
            'fields': ('gateway_response', 'error_message'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': '#6c757d',
            'processing': '#0d6efd',
            'successful': '#198754',
            'failed': '#dc3545',
            'cancelled': '#6c757d',
            'refunded': '#6f42c1',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#999'),
            obj.get_status_display()
        )
    
    status_badge.short_description = 'Status'
    
    def amount_display(self, obj):
        """Display amount with proper formatting"""
        try:
            amount_value = obj.__dict__.get('amount', obj.amount)
            if isinstance(amount_value, (str, type(format_html('')))):
                clean_value = str(amount_value).replace(obj.currency, '').replace(',', '').strip()
                amount_value = Decimal(clean_value) if clean_value else Decimal('0')
            if not isinstance(amount_value, Decimal):
                amount_value = Decimal(str(amount_value))
            return format_html('<strong>{} {:,.0f}</strong>', obj.currency, amount_value)
        except (ValueError, TypeError, AttributeError):
            return format_html('<strong>{} 0</strong>', obj.currency)
    
    amount_display.short_description = 'Amount'


# ============= PAYMENT METHOD ADMIN =============

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'code', 'is_active', 'is_default',
        'has_transaction_fee', 'order'
    )
    list_filter = ('is_active', 'is_default', 'has_transaction_fee')
    search_fields = ('name', 'code')
    list_editable = ('is_active', 'order')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'description', 'icon')
        }),
        ('Status', {
            'fields': ('is_active', 'is_default', 'order')
        }),
        ('Configuration', {
            'fields': ('api_config', 'supported_countries', 'supported_currencies'),
            'classes': ('collapse',)
        }),
        ('Fees', {
            'fields': (
                'has_transaction_fee', 'transaction_fee_percentage',
                'transaction_fee_fixed'
            ),
            'classes': ('collapse',)
        }),
    )


# ============= REFUND ADMIN =============

@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = (
        'refund_id', 'order', 'reason', 'refund_amount_display',
        'status_badge', 'requested_at'
    )
    list_filter = ('status', 'reason', 'requested_at')
    search_fields = ('refund_id', 'order__order_number', 'description')
    readonly_fields = ('refund_id', 'requested_at', 'processed_at', 'created_at', 'updated_at')
    date_hierarchy = 'requested_at'
    
    fieldsets = (
        ('Refund Information', {
            'fields': ('refund_id', 'order', 'order_item', 'reason', 'description')
        }),
        ('Amount', {
            'fields': ('refund_amount',)
        }),
        ('Status', {
            'fields': ('status', 'requested_at', 'processed_at')
        }),
        ('Admin Response', {
            'fields': ('admin_notes', 'rejection_reason'),
            'classes': ('collapse',)
        }),
        ('Evidence', {
            'fields': ('image1', 'image2', 'image3'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_refunds', 'reject_refunds']
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ffc107',
            'approved': '#198754',
            'rejected': '#dc3545',
            'processing': '#0d6efd',
            'completed': '#198754',
        }
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.status, '#999'),
            obj.get_status_display()
        )
    
    status_badge.short_description = 'Status'
    
    def refund_amount_display(self, obj):
        """Display refund amount with proper formatting"""
        try:
            amount_value = obj.__dict__.get('refund_amount', obj.refund_amount)
            if isinstance(amount_value, (str, type(format_html('')))):
                clean_value = str(amount_value).replace('UGX', '').replace(',', '').strip()
                amount_value = Decimal(clean_value) if clean_value else Decimal('0')
            if not isinstance(amount_value, Decimal):
                amount_value = Decimal(str(amount_value))
            return format_html('<strong>UGX {:,.0f}</strong>', amount_value)
        except (ValueError, TypeError, AttributeError):
            return format_html('<strong>UGX 0</strong>')
    
    refund_amount_display.short_description = 'Refund Amount'
    
    def approve_refunds(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status='approved', processed_at=timezone.now())
        self.message_user(request, f'{updated} refund requests approved.')
    
    approve_refunds.short_description = "Approve refund requests"
    
    def reject_refunds(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(status='rejected', processed_at=timezone.now())
        self.message_user(request, f'{updated} refund requests rejected.')
    
    reject_refunds.short_description = "Reject refund requests"