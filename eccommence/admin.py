from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count, Avg
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from django.shortcuts import redirect
from django.contrib import messages
import csv
from django.http import HttpResponse

from .models import (
    Category, Product, ProductImage, ProductVariant,
    Customer, Vendor, Address,
    Review, Coupon
)

# Import Order and OrderItem from payment app
from payment.models import Order, OrderItem


# ============= CUSTOM ADMIN ACTIONS =============

def export_as_csv(modeladmin, request, queryset):
    """Export selected items as CSV"""
    meta = modeladmin.model._meta
    field_names = [field.name for field in meta.fields]

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename={meta}.csv'
    writer = csv.writer(response)

    writer.writerow(field_names)
    for obj in queryset:
        writer.writerow([getattr(obj, field) for field in field_names])

    return response

export_as_csv.short_description = "Export Selected as CSV"


def mark_as_active(modeladmin, request, queryset):
    """Mark selected items as active"""
    updated = queryset.update(is_active=True)
    modeladmin.message_user(request, f'{updated} items marked as active.')

mark_as_active.short_description = "Mark selected as active"


def mark_as_inactive(modeladmin, request, queryset):
    """Mark selected items as inactive"""
    updated = queryset.update(is_active=False)
    modeladmin.message_user(request, f'{updated} items marked as inactive.')

mark_as_inactive.short_description = "Mark selected as inactive"


# ============= INLINE ADMINS =============

class ProductImageInline(admin.TabularInline):
    """Inline admin for product images"""
    model = ProductImage
    extra = 1
    fields = ('image', 'image_preview', 'alt_text', 'is_primary', 'order')
    readonly_fields = ('image_preview',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" height="100" style="object-fit: cover;" />', obj.image.url)
        return "No image"
    
    image_preview.short_description = 'Preview'


class ProductVariantInline(admin.TabularInline):
    """Inline admin for product variants"""
    model = ProductVariant
    extra = 1
    fields = ('name', 'value', 'sku', 'price_adjustment', 'stock_quantity', 'is_active')


class OrderItemInline(admin.TabularInline):
    """Inline admin for order items"""
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'vendor', 'product_name', 'sku', 'quantity', 'price', 'total', 'vendor_payout', 'commission')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False



# ============= CATEGORY ADMIN =============

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'product_count', 'is_active', 'order', 'created_at')
    list_filter = ('is_active', 'parent', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('is_active', 'order')
    ordering = ('order', 'name')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'parent', 'description', 'image', 'order')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [mark_as_active, mark_as_inactive, export_as_csv]
    
    def product_count(self, obj):
        """Show number of products in category"""
        count = obj.products.filter(is_active=True).count()
        return format_html('<span style="color: #2271b1; font-weight: bold;">{}</span>', count)
    
    product_count.short_description = 'Products'


# ============= PRODUCT ADMIN =============

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'product_preview', 'name', 'vendor', 'category', 
        'price_display', 'stock_status', 'is_featured', 
        'rating_display', 'total_sales', 'is_active', 'created_at'
    )
    list_filter = (
        'is_active', 'is_featured', 'is_on_sale', 
        'category', 'vendor', 'created_at', 'track_inventory'
    )
    search_fields = ('name', 'sku', 'description', 'vendor__store_name')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('is_active', 'is_featured')
    readonly_fields = ('sku', 'views', 'rating', 'total_reviews', 'total_sales', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    inlines = [ProductImageInline, ProductVariantInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('vendor', 'name', 'slug', 'sku', 'category')
        }),
        ('Description', {
            'fields': ('short_description', 'description')
        }),
        ('Pricing', {
            'fields': ('price', 'compare_at_price', 'cost_per_item')
        }),
        ('Sale Settings', {
            'fields': ('is_on_sale', 'sale_price', 'sale_start_date', 'sale_end_date'),
            'classes': ('collapse',)
        }),
        ('Inventory', {
            'fields': ('track_inventory', 'stock_quantity', 'low_stock_threshold', 'allow_backorder')
        }),
        ('Physical Properties', {
            'fields': ('weight', 'length', 'width', 'height'),
            'classes': ('collapse',)
        }),
        ('Status & Features', {
            'fields': ('is_active', 'is_featured')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('views', 'rating', 'total_reviews', 'total_sales', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [mark_as_active, mark_as_inactive, 'mark_as_featured', 'remove_featured', export_as_csv]
    
    def product_preview(self, obj):
        """Show product image thumbnail"""
        primary_image = obj.images.filter(is_primary=True).first()
        if primary_image:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />',
                primary_image.image.url
            )
        return format_html('<div style="width:50px;height:50px;background:#ddd;border-radius:4px;"></div>')
    
    product_preview.short_description = ''
    
    def price_display(self, obj):
        """Display price with sale indication"""
        if obj.is_on_sale and obj.sale_price:
            return format_html(
                '<span style="color: #d63384; font-weight: bold;">${}</span> <s style="color: #999;">${}</s>',
                obj.sale_price, obj.price
            )
        return format_html('<span style="font-weight: bold;">${}</span>', obj.price)
    
    price_display.short_description = 'Price'
    
    def stock_status(self, obj):
        """Visual stock status indicator"""
        if not obj.track_inventory:
            return format_html('<span style="color: #0d6efd;">∞ No tracking</span>')
        
        if obj.stock_quantity <= 0:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">⚠ Out of Stock</span>'
            )
        elif obj.stock_quantity <= obj.low_stock_threshold:
            return format_html(
                '<span style="color: #fd7e14; font-weight: bold;">⚡ Low ({} left)</span>',
                obj.stock_quantity
            )
        else:
            return format_html(
                '<span style="color: #198754;">✓ In Stock ({})</span>',
                obj.stock_quantity
            )
    
    stock_status.short_description = 'Stock'
    
    def rating_display(self, obj):
        """Display rating with stars"""
        if obj.total_reviews > 0:
            stars = '★' * int(obj.rating) + '☆' * (5 - int(obj.rating))
            return format_html(
                '<span style="color: #ffc107;" title="{} stars">{}</span> ({})',
                obj.rating, stars, obj.total_reviews
            )
        return format_html('<span style="color: #999;">No reviews</span>')
    
    rating_display.short_description = 'Rating'
    
    def mark_as_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} products marked as featured.')
    
    mark_as_featured.short_description = "Mark as featured"
    
    def remove_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} products removed from featured.')
    
    remove_featured.short_description = "Remove from featured"
    
    class Media:
        css = {
            'all': ('admin/css/product_admin.css',)  # Custom CSS if needed
        }


# ============= VENDOR ADMIN =============

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = (
        'logo_preview', 'store_name', 'user', 'business_email', 
        'business_phone', 'is_verified', 'is_active', 
        'product_count', 'rating_display', 'commission_rate', 'created_at'
    )
    list_filter = ('is_active', 'is_verified', 'created_at')
    search_fields = ('store_name', 'business_email', 'user__username', 'user__email')
    prepopulated_fields = {'slug': ('store_name',)}
    list_editable = ('is_active', 'is_verified', 'commission_rate')
    readonly_fields = ('rating', 'total_reviews', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Store Information', {
            'fields': ('user', 'store_name', 'slug', 'description', 'logo', 'banner')
        }),
        ('Business Details', {
            'fields': ('business_email', 'business_phone', 'business_address', 'tax_id')
        }),
        ('Status & Verification', {
            'fields': ('is_active', 'is_verified', 'verification_date')
        }),
        ('Commission', {
            'fields': ('commission_rate',)
        }),
        ('Statistics', {
            'fields': ('rating', 'total_reviews', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = [mark_as_active, mark_as_inactive, 'verify_vendors', export_as_csv]
    
    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 50%;" />',
                obj.logo.url
            )
        return "No logo"
    
    logo_preview.short_description = ''
    
    def product_count(self, obj):
        count = obj.products.filter(is_active=True).count()
        url = reverse('admin:eccommence_product_changelist') + f'?vendor__id__exact={obj.id}'
        return format_html('<a href="{}" style="color: #2271b1; font-weight: bold;">{} products</a>', url, count)
    
    product_count.short_description = 'Products'
    
    def rating_display(self, obj):
        if obj.total_reviews > 0:
            stars = '★' * int(obj.rating) + '☆' * (5 - int(obj.rating))
            return format_html(
                '<span style="color: #ffc107;">{}</span> ({} reviews)',
                stars, obj.total_reviews
            )
        return "No reviews"
    
    rating_display.short_description = 'Rating'
    
    def verify_vendors(self, request, queryset):
        updated = queryset.update(is_verified=True, verification_date=timezone.now())
        self.message_user(request, f'{updated} vendors verified.')
    
    verify_vendors.short_description = "Verify selected vendors"


# ============= CUSTOMER ADMIN =============

# ============= CUSTOMER ADMIN =============

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('profile_pic', 'full_name', 'user_email', 'phone', 'is_verified', 'order_count', 'created_at')
    list_filter = ('is_verified', 'newsletter_subscription', 'created_at')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'phone')
    readonly_fields = ('created_at', 'updated_at', 'user')
    
    fieldsets = (
        ('User Account', {
            'fields': ('user',)
        }),
        ('Profile Information', {
            'fields': ('phone', 'date_of_birth', 'profile_picture', 'is_verified')
        }),
        ('Preferences', {
            'fields': ('newsletter_subscription', 'sms_notifications'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def profile_pic(self, obj):
        if obj.profile_picture:
            return format_html(
                '<img src="{}" width="40" height="40" style="object-fit: cover; border-radius: 50%;" />',
                obj.profile_picture.url
            )
        return format_html('<div style="width:40px;height:40px;background:#ddd;border-radius:50%;"></div>')
    
    profile_pic.short_description = ''
    
    def user_email(self, obj):
        return obj.user.email
    
    user_email.short_description = 'Email'
    user_email.admin_order_field = 'user__email'
    
    def order_count(self, obj):
        from payment.models import Order
        # Use user field instead of customer
        count = Order.objects.filter(user=obj.user).count()
        if count > 0:
            url = reverse('admin:payment_order_changelist') + f'?user__id__exact={obj.user.id}'
            return format_html('<a href="{}" style="color: #2271b1; font-weight: bold;">{} order{}</a>', url, count, 's' if count != 1 else '')
        return format_html('<span style="color: #94a3b8;">0 orders</span>')
    
    order_count.short_description = 'Orders'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

# ============= REVIEW ADMIN =============

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        'product', 'customer_name', 'rating_stars', 
        'is_verified_purchase', 'is_approved', 
        'helpful_count', 'created_at'
    )
    list_filter = ('rating', 'is_approved', 'is_verified_purchase', 'created_at')
    search_fields = ('product__name', 'customer__user__email', 'title', 'comment')
    readonly_fields = ('created_at', 'updated_at', 'helpful_count')
    list_editable = ('is_approved',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Review Information', {
            'fields': ('product', 'customer', 'order_item', 'rating', 'title', 'comment')
        }),
        ('Status', {
            'fields': ('is_verified_purchase', 'is_approved', 'helpful_count')
        }),
        ('Vendor Response', {
            'fields': ('vendor_response', 'vendor_responded_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_reviews', 'disapprove_reviews']
    
    def customer_name(self, obj):
        return obj.customer.full_name
    
    customer_name.short_description = 'Customer'
    
    def rating_stars(self, obj):
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return format_html('<span style="color: #ffc107; font-size: 16px;">{}</span>', stars)
    
    rating_stars.short_description = 'Rating'
    
    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f'{updated} reviews approved.')
    
    approve_reviews.short_description = "Approve selected reviews"
    
    def disapprove_reviews(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f'{updated} reviews disapproved.')
    
    disapprove_reviews.short_description = "Disapprove selected reviews"


# ============= COUPON ADMIN =============

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'discount_display', 'usage_display', 
        'validity_period', 'is_active', 'times_used'
    )
    list_filter = ('discount_type', 'is_active', 'valid_from', 'valid_to')
    search_fields = ('code', 'description')
    readonly_fields = ('times_used', 'created_at', 'updated_at')
    list_editable = ('is_active',)
    
    fieldsets = (
        ('Coupon Details', {
            'fields': ('code', 'description')
        }),
        ('Discount', {
            'fields': ('discount_type', 'discount_value', 'max_discount_amount')
        }),
        ('Restrictions', {
            'fields': ('min_purchase_amount', 'usage_limit', 'usage_limit_per_customer')
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_to', 'is_active')
        }),
        ('Usage Statistics', {
            'fields': ('times_used',),
            'classes': ('collapse',)
        }),
    )
    
    def discount_display(self, obj):
        if obj.discount_type == 'percentage':
            return format_html('<strong>{}%</strong> off', obj.discount_value)
        return format_html('<strong>${}</strong> off', obj.discount_value)
    
    discount_display.short_description = 'Discount'
    
    def usage_display(self, obj):
        if obj.usage_limit:
            percentage = (obj.times_used / obj.usage_limit) * 100
            color = '#198754' if percentage < 70 else '#fd7e14' if percentage < 90 else '#dc3545'
            return format_html(
                '<span style="color: {};">{} / {}</span>',
                color, obj.times_used, obj.usage_limit
            )
        return f'{obj.times_used} / ∞'
    
    usage_display.short_description = 'Usage'
    
    def validity_period(self, obj):
        now = timezone.now()
        if now < obj.valid_from:
            return format_html('<span style="color: #0dcaf0;">Starts {}</span>', obj.valid_from.strftime('%Y-%m-%d'))
        elif now > obj.valid_to:
            return format_html('<span style="color: #dc3545;">Expired</span>')
        else:
            return format_html('<span style="color: #198754;">Active until {}</span>', obj.valid_to.strftime('%Y-%m-%d'))
    
    validity_period.short_description = 'Validity'


# ============= OTHER MODEL ADMINS =============

class AddressAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'customer', 'address_type', 'city', 'country', 'is_default')
    list_filter = ('address_type', 'country', 'is_default')
    search_fields = ('full_name', 'customer__user__email', 'city', 'postal_code')
    list_editable = ('is_default',)



@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('image_preview', 'product', 'is_primary', 'order', 'created_at')
    list_filter = ('is_primary', 'created_at')
    search_fields = ('product__name', 'alt_text')
    list_editable = ('is_primary', 'order')
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="80" height="80" style="object-fit: cover; border-radius: 4px;" />',
                obj.image.url
            )
        return "No image"
    
    image_preview.short_description = 'Preview'


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'name', 'value', 'sku', 'price_adjustment', 'stock_quantity', 'is_active')
    list_filter = ('is_active', 'name')
    search_fields = ('product__name', 'sku', 'value')
    list_editable = ('is_active', 'stock_quantity')


# ============= CUSTOM ADMIN SITE CONFIGURATION =============

admin.site.site_header = "eccommence Admin Dashboard"
admin.site.site_title = "eccommence Admin"
admin.site.index_title = "Welcome to eccommence Management"