from django.urls import path
from . import views

app_name = 'store_admin'

urlpatterns = [
    # ── Main Dashboard ──
    path('', views.dashboard, name='dashboard'),

    # ── Orders ──
    path('orders/', views.orders, name='orders'),
    path('orders/<str:order_number>/', views.order_detail, name='order_detail'),

    # ── Products ──
    path('products/', views.products, name='products'),
    path('products/add/', views.product_add, name='add_product'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),

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

    # ── Settings ──
    path('settings/', views.shop_settings, name='settings'),

    # ── Export ──
    path('export/', views.dashboard_export, name='dashboard_export'),

    # ── AJAX API ──
    path('api/order-stats/', views.get_order_stats, name='get_order_stats'),
    path('api/product-stats/', views.get_product_stats, name='get_product_stats'),
]