"""
Main project views for public schema
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.utils.text import slugify
import json

from tenants.models import Client, Domain
from users.models import User
from users.forms import CustomerRegistrationForm


# ============= LANDING & MARKETING PAGES =============

def landing_page(request):
    """Main landing page"""
    context = {
        'total_shops': Client.objects.filter(is_active=True).count(),
        'featured_shops': Client.objects.filter(
            is_active=True,
            is_verified=True
        )[:6],
    }
    return render(request, 'public/landing.html', context)


def about_page(request):
    """About page"""
    return render(request, 'public/about.html')


def pricing_page(request):
    """Pricing plans page"""
    plans = [
        {
            'name': 'Free',
            'price': 0,
            'period': 'forever',
            'features': [
                '100 Products',
                '1GB Storage',
                '1,000 Orders/month',
                'Basic Analytics',
                '3 Staff Accounts',
            ]
        },
        {
            'name': 'Basic',
            'price': 50000,
            'period': 'month',
            'features': [
                '500 Products',
                '5GB Storage',
                '5,000 Orders/month',
                'Advanced Analytics',
                '10 Staff Accounts',
                'Custom Domain',
                'API Access',
            ]
        },
        {
            'name': 'Premium',
            'price': 150000,
            'period': 'month',
            'features': [
                '2,000 Products',
                '20GB Storage',
                '20,000 Orders/month',
                'Advanced Analytics',
                '50 Staff Accounts',
                'Custom Domain',
                'API Access',
                'Priority Support',
            ],
            'popular': True
        },
        {
            'name': 'Enterprise',
            'price': 'Custom',
            'period': 'month',
            'features': [
                'Unlimited Products',
                'Unlimited Storage',
                'Unlimited Orders',
                'Advanced Analytics',
                'Unlimited Staff',
                'Custom Domain',
                'API Access',
                'Priority Support',
                'Custom Features',
            ]
        },
    ]
    
    context = {'plans': plans}
    return render(request, 'public/pricing.html', context)


def features_page(request):
    """Features page"""
    return render(request, 'public/features.html')


def contact_page(request):
    """Contact page"""
    if request.method == 'POST':
        # Handle contact form submission
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        
        # TODO: Send email or save to database
        
        messages.success(request, 'Thank you for contacting us! We will get back to you soon.')
        return redirect('contact')
    
    return render(request, 'public/contact.html')


# ============= SHOP CREATION =============

@transaction.atomic
def create_shop(request):
    """Create a new shop/tenant"""
    if request.method == 'POST':
        # Get form data
        shop_name = request.POST.get('shop_name')
        owner_email = request.POST.get('owner_email')
        owner_name = request.POST.get('owner_name')
        owner_phone = request.POST.get('owner_phone')
        password = request.POST.get('password')
        subdomain = request.POST.get('subdomain')
        
        # Validate
        if not all([shop_name, owner_email, owner_name, password, subdomain]):
            messages.error(request, 'All fields are required')
            return render(request, 'public/create_shop.html')
        
        # Check if subdomain is available
        subdomain = slugify(subdomain)
        domain_url = f"{subdomain}.localhost"  # Change to your domain in production
        
        if Domain.objects.filter(domain=domain_url).exists():
            messages.error(request, 'This subdomain is already taken')
            return render(request, 'public/create_shop.html')
        
        # Check if email already exists
        if User.objects.filter(email=owner_email).exists():
            messages.error(request, 'This email is already registered')
            return render(request, 'public/create_shop.html')
        
        try:
            # Create user
            user = User.objects.create_user(
                email=owner_email,
                password=password,
                first_name=owner_name.split()[0] if owner_name else '',
                last_name=' '.join(owner_name.split()[1:]) if len(owner_name.split()) > 1 else '',
                phone=owner_phone or '',
                user_type='vendor'
            )
            
            # Create tenant
            from datetime import date, timedelta
            schema_name = slugify(shop_name).replace('-', '_')
            
            tenant = Client.objects.create(
                name=shop_name,
                schema_name=schema_name,
                owner_name=owner_name,
                owner_email=owner_email,
                owner_phone=owner_phone or '',
                paid_until=date.today() + timedelta(days=14),  # 14-day trial
                on_trial=True,
                subscription_plan='free'
            )
            
            # Create domain
            Domain.objects.create(
                domain=domain_url,
                tenant=tenant,
                is_primary=True
            )
            
            # Log activity
            from tenants.models import TenantActivity
            TenantActivity.objects.create(
                tenant=tenant,
                activity_type='created',
                description=f'Shop created by {owner_name}',
                performed_by=owner_email
            )
            
            messages.success(request, 'Shop created successfully! You can now log in.')
            return redirect('shop_success')
        
        except Exception as e:
            messages.error(request, f'Error creating shop: {str(e)}')
            return render(request, 'public/create_shop.html')
    
    return render(request, 'public/create_shop.html')


def shop_success(request):
    """Shop creation success page"""
    return render(request, 'public/shop_success.html')


def find_shop(request):
    """Find a shop by name or subdomain"""
    query = request.GET.get('q', '')
    
    if query:
        shops = Client.objects.filter(
            is_active=True,
            name__icontains=query
        )[:10]
        
        results = [
            {
                'name': shop.name,
                'domain': shop.domains.filter(is_primary=True).first().domain if shop.domains.exists() else None,
                'description': shop.description
            }
            for shop in shops
        ]
        
        return JsonResponse({'results': results})
    
    return render(request, 'public/find_shop.html')


# ============= PLATFORM AUTHENTICATION =============

def platform_login(request):
    """Platform admin login"""
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, username=email, password=password)
        
        if user and user.is_staff:
            login(request, user)
            return redirect('/admin/')
        else:
            messages.error(request, 'Invalid credentials or unauthorized access')
    
    return render(request, 'public/platform_login.html')


def platform_register(request):
    """Platform registration"""
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('landing')
    else:
        form = CustomerRegistrationForm()
    
    return render(request, 'public/platform_register.html', {'form': form})


def platform_logout(request):
    """Platform logout"""
    logout(request)
    return redirect('landing')


# ============= UTILITY VIEWS =============

def health_check(request):
    """Health check endpoint for monitoring"""
    from django.db import connection
    
    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        return JsonResponse({
            'status': 'healthy',
            'database': 'connected'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=500)