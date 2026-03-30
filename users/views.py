from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
import json
from django.contrib.auth.views import PasswordResetView
from django.urls import reverse_lazy

from .models import User, VendorProfile, Address
from .forms import (
    CustomerRegistrationForm, UserUpdateForm,
    ChangePasswordForm, AddressForm,CustomerUpdateForm
)
from cart.cart import Cart
from eccommence.models import Customer  # Add this for customer profile


# ============= AUTHENTICATION VIEWS =============

def login_view(request):
    """User login view"""
    # Redirect if already logged in
    if request.user.is_authenticated:
        return redirect('eccommence:home')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')
        
        # Authenticate user
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            login(request, user)
            
            # Handle remember me
            if not remember_me:
                request.session.set_expiry(0)
            
            # Cart restoration - using Customer model instead of Profile
            try:
                customer = Customer.objects.get(user=user)
                # Note: cart_info was in Profile, you may need to migrate this to Customer
                # or handle it differently
                pass
            except Customer.DoesNotExist:
                pass
            
            # Redirect to next or home
            next_url = request.GET.get('next', 'eccommence:home')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid email or password.')
    
    return render(request, 'users/login.html')


def logout_view(request):
    """User logout view"""
    logout(request)
    return redirect('eccommence:home')


def register_view(request):
    """Customer registration view"""
    if request.user.is_authenticated:
        return redirect('users:login')
    
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        
        if form.is_valid():
            # Create user
            user = form.save()
            
            # Create customer profile in eccommence
            Customer.objects.create(user=user)
            
            # Auto login
            login(request, user)
            
            messages.success(request, 'Registration successful! Welcome to our store.')
            return redirect('eccommence:home')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomerRegistrationForm()
    
    return render(request, 'users/register.html', {'form': form})




# ============= PROFILE VIEWS =============

@login_required
def profile_view(request):
    """View user profile"""
    # Get or create customer profile
    customer, created = Customer.objects.get_or_create(user=request.user)
    
    # Get user's addresses from the Address model
    addresses = []
    default_address = None
    
    if hasattr(request.user, 'customer_profile'):
        customer = request.user.customer_profile
        addresses = customer.addresses.all()
        default_address = addresses.filter(is_default=True).first()
    
    context = {
        'user': request.user,
        'customer': customer,
        'addresses': addresses,
        'default_address': default_address,
    }
    
    return render(request, 'users/profile.html', context)


@login_required
def profile_edit(request):
    """Edit user profile"""
    # Get or create customer profile
    customer, created = Customer.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        customer_form = CustomerUpdateForm(request.POST, instance=customer)
        
        if user_form.is_valid() and customer_form.is_valid():
            user_form.save()
            customer_form.save()
            
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('users:profile_view')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        user_form = UserUpdateForm(instance=request.user)
        customer_form = CustomerUpdateForm(instance=customer)
    
    context = {
        'user_form': user_form,
        'customer_form': customer_form,
    }
    
    return render(request, 'users/profile_edit.html', context)


@login_required
def profile_setup(request):
    """Initial profile setup after registration"""
    # This view might need updating based on your requirements
    # For now, redirect to profile edit
    return redirect('users:profile_edit')


@login_required
@require_http_methods(["POST"])
def upload_profile_picture(request):
    """Upload profile picture via AJAX"""
    customer, created = Customer.objects.get_or_create(user=request.user)
    
    if 'profile_picture' in request.FILES:
        customer.profile_picture = request.FILES['profile_picture']
        customer.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Profile picture updated successfully!',
            'image_url': customer.profile_picture.url
        })
    
    return JsonResponse({
        'success': False,
        'message': 'No image provided'
    }, status=400)


@login_required
@require_http_methods(["POST"])
def remove_profile_picture(request):
    """Remove profile picture"""
    customer = get_object_or_404(Customer, user=request.user)
    
    if customer.profile_picture:
        customer.profile_picture.delete()
        customer.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Profile picture removed successfully!'
        })
    
    return JsonResponse({
        'success': False,
        'message': 'No profile picture to remove'
    }, status=400)


# ============= PASSWORD MANAGEMENT =============

@login_required
def change_password(request):
    """Change user password"""
    if request.method == 'POST':
        form = ChangePasswordForm(request.user, request.POST)
        
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            
            messages.success(request, 'Your password has been changed successfully!')
            return redirect('eccommence:home')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ChangePasswordForm(request.user)
    
    return render(request, 'users/change_password.html', {'form': form})


# ============= ADDRESS MANAGEMENT =============

@login_required
def address_list(request):
    addresses = Address.objects.filter(user=request.user)
    default_count = addresses.filter(is_default=True).count()
    
    context = {
        'addresses': addresses,
        'default_count': default_count,
    }
    
    return render(request, 'users/address_list.html', context)

@login_required
def address_add(request):
    """Add new address"""
    if request.method == 'POST':
        form = AddressForm(request.POST)
        
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            
            messages.success(request, 'Address added successfully!')
            return redirect('users:address_list')
    else:
        form = AddressForm()
    
    return render(request, 'users/address_form.html', {'form': form, 'action': 'Add'})


@login_required
def address_edit(request, pk):
    """Edit existing address"""
    address = get_object_or_404(Address, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        
        if form.is_valid():
            form.save()
            
            messages.success(request, 'Address updated successfully!')
            return redirect('users:address_list')
    else:
        form = AddressForm(instance=address)
    
    context = {
        'form': form,
        'action': 'Edit',
        'address': address,  # ← MAKE SURE THIS LINE EXISTS
    }
    
    return render(request, 'users/address_form.html', context)
@login_required
def address_delete(request, pk):
    """Delete address"""
    address = get_object_or_404(Address, pk=pk, user=request.user)
    
    if request.method == 'POST':
        address.delete()
        messages.success(request, 'Address deleted successfully!')
        return redirect('users:address_list')
    
    return render(request, 'users/address_confirm_delete.html', {'address': address})


@login_required
@require_http_methods(["POST"])
def address_set_default(request, pk):
    """Set address as default"""
    address = get_object_or_404(Address, pk=pk, user=request.user)
    
    # Remove default from all addresses
    Address.objects.filter(user=request.user, address_type=address.address_type).update(is_default=False)
    
    # Set this as default
    address.is_default = True
    address.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Default address updated!'
    })


# ============= ACCOUNT SETTINGS =============

@login_required
def account_settings(request):
    """Account settings page"""
    customer, created = Customer.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Update notification preferences
        customer.newsletter_subscription = request.POST.get('newsletter_subscription') == 'on'
        customer.sms_notifications = request.POST.get('sms_notifications') == 'on'
        customer.email_notifications = request.POST.get('email_notifications') == 'on'
        customer.save()
        
        messages.success(request, 'Settings updated successfully!')
        return redirect('users:account_settings')
    
    return render(request, 'users/account_settings.html', {'customer': customer})


@login_required
def delete_account(request):
    """Delete user account"""
    if request.method == 'POST':
        password = request.POST.get('password')
        
        # Verify password
        if request.user.check_password(password):
            user = request.user
            logout(request)
            user.delete()
            
            messages.success(request, 'Your account has been deleted.')
            return redirect('eccommence:home')
        else:
            messages.error(request, 'Incorrect password.')
    
    return render(request, 'users/delete_account.html')


# ============= LEGACY SUPPORT (Keep for backward compatibility) =============

@login_required
def update_user(request):
    """Legacy view - redirect to profile_edit"""
    return redirect('users:profile_edit')


@login_required
def user_info(request):
    """Legacy view - redirect to profile_view"""
    return redirect('users:profile_view')


@login_required
def update_password(request):
    """Legacy view - redirect to change_password"""
    return redirect('users:change_password')


@login_required
def change_profile_picture(request):
    """Legacy view - redirect to profile_edit"""
    return redirect('users:profile_edit')


class CustomPasswordResetView(PasswordResetView):
    template_name = 'users/password_reset.html'
    email_template_name = 'users/password_reset_email.html'
    subject_template_name = 'users/password_reset_subject.txt'
    success_url = reverse_lazy('users:password_reset_done')

    def form_valid(self, form):
        # Store the email in session to display on the done page
        self.request.session['reset_email'] = form.cleaned_data['email']
        return super().form_valid(form)