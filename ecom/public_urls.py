# ecom/public_urls.py
from django.urls import path
from django.http import HttpResponse
from django.contrib import admin


def landing_page(request):
    return HttpResponse("Welcome to our platform")

urlpatterns = [
    path('', landing_page),
    path('admin/', admin.site.urls),

]
