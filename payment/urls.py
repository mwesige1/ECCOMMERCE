from django.urls import path
from . import views

app_name = 'payment'

urlpatterns = [
    # Checkout Flow
    path('checkout/', views.checkout, name='checkout'),
    path('payment-method/', views.payment_method, name='payment_method'),  # ← Not needed with single-page checkout
    path('process-payment/', views.process_payment, name='process_payment'),
    
    # Mobile Money Payment
    path('mobile-money/<str:order_number>/', views.mobile_money_payment, name='mobile_money_payment'),
    path('api/initiate-mobile-money/', views.initiate_mobile_money, name='initiate_mobile_money'),
    path('api/verify-mobile-money/', views.verify_mobile_money, name='verify_mobile_money'),
    
    # Payment Results
    path('success/<str:order_number>/', views.payment_success, name='payment_success'),
    path('failed/', views.payment_failed, name='payment_failed'),
    
    # Webhooks
    path('callback/<str:gateway>/', views.payment_callback, name='payment_callback'),
    
    # Order Management
    path('orders/', views.order_history, name='order_history'),
    path('order/<str:order_number>/', views.order_detail, name='order_detail'),
    path('order/<str:order_number>/track/', views.track_order, name='track_order'),
    path('order/<str:order_number>/cancel/', views.cancel_order, name='cancel_order'),
    
    # Refunds
    path('order/<str:order_number>/refund/', views.request_refund, name='request_refund'),
]