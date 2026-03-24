from django.urls import path, include
from . import views

app_name = 'eccommence'

# ============= MAIN SHOP URLs =============
shop_patterns = [
    path('', views.shop, name='shop'),
    path('search/', views.search, name='search'),
    path('deals/', views.deals, name='deals'),
    path('new-arrivals/', views.new_arrivals, name='new_arrivals'),
    path('best-sellers/', views.best_sellers, name='best_sellers'),
]

# ============= PRODUCT URLs =============
product_patterns = [
    path('<slug:slug>/', views.product_detail, name='product_detail'),
    path('<slug:slug>/quick-view/', views.product_quick_view, name='product_quick_view'),
    path('<slug:slug>/review/', views.submit_review, name='submit_review'),
    path('<slug:slug>/check-availability/', views.check_availability, name='check_availability'),
]

# ============= CATEGORY URLs =============
category_patterns = [
    path('', views.category_list, name='category_list'),
    path('<slug:slug>/', views.category_view, name='category_detail'),
]

# ============= CART URLs =============
cart_patterns = [
    path('', views.cart_view, name='cart'),
    path('add/', views.add_to_cart, name='add_to_cart'),
    path('update/', views.update_cart_item, name='update_cart_item'),
    path('remove/', views.remove_from_cart, name='remove_from_cart'),
    path('clear/', views.clear_cart, name='clear_cart'),
    path('count/', views.cart_count, name='cart_count'),  # For AJAX
]

# ============= CHECKOUT URLs =============
checkout_patterns = [
    path('', views.checkout, name='checkout'),
    path('payment/', views.payment, name='payment'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
    path('success/<str:order_number>/', views.order_confirmation, name='order_confirmation'),
]

# ============= WISHLIST URLs =============
wishlist_patterns = [
    path('', views.wishlist_view, name='wishlist'),
    path('toggle/', views.toggle_wishlist, name='toggle_wishlist'),
    path('add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('remove/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
]

# ============= USER ACCOUNT URLs =============
account_patterns = [
    # Dashboard
    path('dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('profile/', views.customer_profile, name='customer_profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    
    # Orders
    path('orders/', views.customer_orders, name='customer_orders'),
    path('orders/<str:order_number>/', views.order_detail, name='order_detail'),
    path('orders/<str:order_number>/track/', views.track_order, name='track_order'),
    path('orders/<str:order_number>/cancel/', views.cancel_order, name='cancel_order'),
    path('orders/<str:order_number>/invoice/', views.download_invoice, name='download_invoice'),
    
    # Addresses
    path('addresses/', views.address_list, name='address_list'),
    path('addresses/add/', views.add_address, name='add_address'),
    path('addresses/<int:address_id>/edit/', views.edit_address, name='edit_address'),
    path('addresses/<int:address_id>/delete/', views.delete_address, name='delete_address'),
    path('addresses/<int:address_id>/set-default/', views.set_default_address, name='set_default_address'),
    
    # Reviews
    path('reviews/', views.customer_reviews, name='customer_reviews'),
    path('reviews/<int:review_id>/edit/', views.edit_review, name='edit_review'),
    path('reviews/<int:review_id>/delete/', views.delete_review, name='delete_review'),
    
    # Settings
    path('settings/', views.account_settings, name='account_settings'),
    path('change-password/', views.change_password, name='change_password'),
    path('notifications/', views.notification_settings, name='notification_settings'),
]

# ============= VENDOR URLs =============
vendor_patterns = [
    # Public vendor pages
    path('<slug:slug>/', views.vendor_store, name='vendor_store'),
    path('<slug:slug>/about/', views.vendor_about, name='vendor_about'),
    path('<slug:slug>/reviews/', views.vendor_reviews, name='vendor_reviews'),
    path('<slug:slug>/contact/', views.contact_vendor, name='contact_vendor'),
    
    # Vendor dashboard (requires vendor login)
    path('dashboard/home/', views.vendor_dashboard, name='vendor_dashboard'),
    path('dashboard/analytics/', views.vendor_analytics, name='vendor_analytics'),
    
    # Product management
    path('dashboard/products/', views.vendor_products, name='vendor_products'),
    path('dashboard/products/add/', views.vendor_add_product, name='vendor_add_product'),
    path('dashboard/products/<int:product_id>/edit/', views.vendor_edit_product, name='vendor_edit_product'),
    path('dashboard/products/<int:product_id>/delete/', views.vendor_delete_product, name='vendor_delete_product'),
    path('dashboard/products/<int:product_id>/images/', views.vendor_manage_images, name='vendor_manage_images'),
    path('dashboard/products/<int:product_id>/variants/', views.vendor_manage_variants, name='vendor_manage_variants'),
    path('dashboard/products/bulk-upload/', views.vendor_bulk_upload, name='vendor_bulk_upload'),
    
    # Order management
    path('dashboard/orders/', views.vendor_orders, name='vendor_orders'),
    path('dashboard/orders/<str:order_number>/', views.vendor_order_detail, name='vendor_order_detail'),
    path('dashboard/orders/<str:order_number>/update-status/', views.vendor_update_order_status, name='vendor_update_order_status'),
    path('dashboard/orders/<str:order_number>/add-tracking/', views.vendor_add_tracking, name='vendor_add_tracking'),
    
    # Reviews management
    path('dashboard/reviews/', views.vendor_reviews_management, name='vendor_reviews_management'),
    path('dashboard/reviews/<int:review_id>/respond/', views.vendor_respond_review, name='vendor_respond_review'),
    
    # Store settings
    path('dashboard/store-settings/', views.vendor_store_settings, name='vendor_store_settings'),
    path('dashboard/profile/', views.vendor_profile, name='vendor_profile'),
    path('dashboard/payouts/', views.vendor_payouts, name='vendor_payouts'),
]

# ============= COUPON URLs =============
coupon_patterns = [
    path('apply/', views.apply_coupon, name='apply_coupon'),
    path('remove/', views.remove_coupon, name='remove_coupon'),
    path('validate/', views.validate_coupon, name='validate_coupon'),
]

# ============= COMPARISON & TOOLS URLs =============
tools_patterns = [
    path('compare/', views.product_compare, name='product_compare'),
    path('compare/add/<int:product_id>/', views.add_to_compare, name='add_to_compare'),
    path('compare/remove/<int:product_id>/', views.remove_from_compare, name='remove_from_compare'),
]

# ============= AUTHENTICATION URLs (if not using separate auth app) =============
auth_patterns = [
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/<str:token>/', views.reset_password, name='reset_password'),
    
    # Vendor registration
    path('vendor/register/', views.vendor_register, name='vendor_register'),
    path('vendor/verify/<str:token>/', views.vendor_verify, name='vendor_verify'),
]

# ============= AJAX/API URLs =============
api_patterns = [
    # Product APIs
    path('products/filter/', views.api_filter_products, name='api_filter_products'),
    path('products/<int:product_id>/variants/', views.api_get_variants, name='api_get_variants'),
    path('products/autocomplete/', views.api_product_autocomplete, name='api_product_autocomplete'),
    
    # Location APIs
    path('locations/cities/', views.api_get_cities, name='api_get_cities'),
    path('locations/shipping-cost/', views.api_calculate_shipping, name='api_calculate_shipping'),
    
    # Cart APIs
    path('cart/update-quantity/', views.api_update_cart_quantity, name='api_update_cart_quantity'),
    path('cart/summary/', views.api_cart_summary, name='api_cart_summary'),
    
    # Wishlist APIs
    path('wishlist/check/<int:product_id>/', views.api_check_wishlist, name='api_check_wishlist'),
    
    # Review APIs
    path('reviews/helpful/<int:review_id>/', views.api_mark_review_helpful, name='api_mark_review_helpful'),
]

# ============= MAIN URL PATTERNS =============
urlpatterns = [
    # Homepage
    path('', views.home, name='home'),
    
    # Shop
    path('shop/', include(shop_patterns)),
    
    # Products
    path('product/', include(product_patterns)),
    
    # Categories
    path('categories/', include(category_patterns)),
    
    # Cart
    path('cart/', include(cart_patterns)),
    
    # Checkout
    path('checkout/', include(checkout_patterns)),
    
    # Wishlist
    path('wishlist/', include(wishlist_patterns)),
    
    # User Account
    path('account/', include(account_patterns)),
    
    # Vendors
    path('vendor/', include(vendor_patterns)),
    
    # Coupons
    path('coupon/', include(coupon_patterns)),
    
    # Tools
    path('tools/', include(tools_patterns)),
    
    # Authentication
    path('auth/', include(auth_patterns)),
    
    # API/AJAX endpoints
    path('api/', include(api_patterns)),
    
    # Static pages
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('faq/', views.faq, name='faq'),
    path('terms/', views.terms, name='terms'),
    path('privacy/', views.privacy, name='privacy'),
    path('shipping-policy/', views.shipping_policy, name='shipping_policy'),
    path('return-policy/', views.return_policy, name='return_policy'),
]