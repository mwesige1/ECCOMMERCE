
# cart/urls.py
from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    # Main cart views
    path('', views.cart_detail, name='cart_detail'),
    path('summary/', views.cart_summary, name='cart_summary'),
    
    # Cart actions
    path('add/', views.cart_add, name='cart_add'),
    path('update/', views.cart_update, name='cart_update'),
    path('remove/', views.cart_remove, name='cart_remove'),
    path('clear/', views.cart_clear, name='cart_clear'),
    
    # Wishlist
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/', views.wishlist_toggle, name='wishlist_toggle'),
    path('wishlist/add-to-cart/', views.wishlist_add_to_cart, name='wishlist_add_to_cart'),
    
    # Coupons
    path('coupon/apply/', views.apply_coupon, name='apply_coupon'),
    path('coupon/remove/', views.remove_coupon, name='remove_coupon'),
]