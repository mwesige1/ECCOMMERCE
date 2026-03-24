from django.urls import path
from . import views

app_name = 'eccommence'

urlpatterns = [
    path('', views.home, name='home'),
    path('categories/', views.category_list, name='category_list'),
    path('category/<slug:item>/', views.category, name='category'),
    path('category-view/<slug:slug>/', views.category_view, name='category_view'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    #path('toggle-wishlist/', views.toggle_wishlist, name='toggle_wishlist'),

    # ... other URLs
]