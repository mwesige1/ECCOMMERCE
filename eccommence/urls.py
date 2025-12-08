from django.urls import path
from. import views

app_name = 'eccommence'
urlpatterns = [
    path('',views.home,name='home'),
    path('product/<int:pk>/',views.product,name='product'),
    path('category/<str:item>/',views.category,name='category'),
    path('category_summary/',views.category_summary,name='category_summary'),



]
