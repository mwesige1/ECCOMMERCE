from django.urls import path
from. import views

app_name = 'cart'
urlpatterns = [
    path('', views.cart_summary, name='cart_summary'),
    path('add/', views.cart_add, name='cart_add'),
    path('update/', views.cart_update, name='cart_update'),
    # Add these two new URLs:
    path('increase/', views.cart_increase, name='cart_increase'),
    path('decrease/', views.cart_decrease, name='cart_decrease'),
    path('delete/', views.cart_delete, name='cart_delete'),
]