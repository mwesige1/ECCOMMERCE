from django.urls import path
from django.urls import reverse
from . import views

app_name = 'store_admin'

urlpatterns = [
    # ── Main Dashboard ──
    path('', views.dashboard, name='dashboard'),

    # ── Orders ──
    path('orders/', views.orders, name='orders'),
    path('orders/<str:order_number>/', views.order_detail, name='order_detail'),
    path('categories/add/', views.add_category, name='add_category'),

    # ── Products ──
    path('products/', views.products, name='products'),
    path('products/add/', views.product_add, name='add_product'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/preview/', views.preview_product, name='preview_product'),
        # Product Management URLs
    path('products/<int:product_id>/toggle-status/', views.toggle_product_status, name='toggle_product_status'),
    path('products/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    path('products/<int:product_id>/update-stock/', views.update_product_stock, name='update_product_stock'),
    path('products/bulk-activate/', views.bulk_activate_products, name='bulk_activate_products'),
    path('products/bulk-deactivate/', views.bulk_deactivate_products, name='bulk_deactivate_products'),
    path('products/bulk-delete/', views.bulk_delete_products, name='bulk_delete_products'),
path('products/set-primary/<int:image_id>/', views.set_primary_image, name='set_primary_image'),    path('products/preview/save/', views.save_preview, name='save_preview'),
    # ── Customers ──
    path('customers/', views.customers, name='customers'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),

    # ── Vendors ──
    path('vendors/', views.vendors, name='vendors'),

    # ── Staff ──
    path('staff/', views.staff, name='staff'),

    # ── Analytics ──
    path('analytics/', views.analytics, name='analytics'),

    # ── Promotions ──
    path('promotions/', views.promotions, name='promotions'),

    # ── Refunds ──
    path('refunds/', views.refunds, name='refunds'),
       # Refunds URLs
    path('refunds/', views.refunds, name='refunds'),
    path('refunds/<int:refund_id>/detail/', views.get_refund_detail, name='get_refund_detail'),
    path('refunds/<int:refund_id>/process/', views.process_refund, name='process_refund'),
    
    
   # Order detail JSON endpoint
    path('orders/<int:order_id>/detail-json/', views.get_order_detail_json, name='get_order_detail_json'),
    # ── Settings ──
    path('settings/', views.shop_settings, name='settings'),

    # ── Export ──
    path('export/', views.dashboard_export, name='dashboard_export'),

    # ── AJAX API ──
    path('api/order-stats/', views.get_order_stats, name='get_order_stats'),
    path('api/product-stats/', views.get_product_stats, name='get_product_stats'),


# Order Management URLs
    path('orders/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    path('orders/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('orders/<str:order_number>/print/', views.print_order, name='print_order'),
    path('orders/bulk-update/', views.bulk_update_orders, name='bulk_update_orders'),
    path('orders/export/', views.export_orders, name='export_orders'),
]