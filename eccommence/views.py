from django.shortcuts import render,redirect
from .models import Category,Customer ,Order ,Product
from django.contrib.auth .forms import AuthenticationForm
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect



# Create your views here.
def home(request):
    products = Product.objects.all()
    return render(request,'grok/amazon.html',{'products':products})


def product(request,pk):
    product = Product.objects.get(id=pk)
    return render(request,'grok/product-detail.html',{'product':product})




def category(request, item):
    # item is the slug from the URL
    category = get_object_or_404(Category, slug=item)
    products = Product.objects.filter(category=category)
    return render(request, 'grok/category-detail.html', {'products': products, 'category': category})

def category_summary(request):
     return render(request,'grok/category.html')

