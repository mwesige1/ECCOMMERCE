from django.contrib import admin
from django.utils.html import format_html
from .models import Cart, CartItem, SavedForLater


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('product', 'variant', 'quantity', 'price', 'total_price', 'created_at')
    can_delete = True
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'customer_info', 'items_count', 
        'subtotal_display', 'discount_display', 'updated_at'
    )
    list_filter = ('created_at', 'updated_at')
    search_fields = ('customer__user__email', 'session_key', 'coupon_code')
    readonly_fields = ('created_at', 'updated_at', 'total_items', 'subtotal', 'total')
    inlines = [CartItemInline]
    
    def customer_info(self, obj):
        if obj.customer:
            return obj.customer.full_name
        return f'Guest ({obj.session_key[:15]}...)'
    
    customer_info.short_description = 'Customer'
    
    def items_count(self, obj):
        return obj.total_items
    
    items_count.short_description = 'Items'
    
    def subtotal_display(self, obj):
        return f'${obj.subtotal:,.2f}'
    
    subtotal_display.short_description = 'Subtotal'
    
    def discount_display(self, obj):
        if obj.discount_amount > 0:
            return f'-${obj.discount_amount:,.2f}'
        return '-'
    
    discount_display.short_description = 'Discount'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('product', 'variant', 'cart', 'quantity', 'price', 'total_price', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('product__name', 'cart__customer__user__email')
    readonly_fields = ('total_price', 'created_at', 'updated_at')


@admin.register(SavedForLater)
class SavedForLaterAdmin(admin.ModelAdmin):
    list_display = ('customer', 'product', 'variant', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('customer__user__email', 'product__name')
    readonly_fields = ('created_at',)