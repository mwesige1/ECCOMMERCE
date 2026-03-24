from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def store_admin_required(view_func):
    """
    Decorator that grants access to the store management dashboard.
    
    Access levels:
    - admin  → full access to everything
    - staff  → access to orders, customers, products (no financials)
    - vendor → access only to their own products and sales
    - customer / unauthenticated → redirected away
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        
        # Not logged in at all
        if not request.user.is_authenticated:
            messages.info(request, 'Please log in to access the management dashboard.')
            return redirect('users:login')
        
        # Logged in but is a customer — send them home
        if request.user.user_type == 'customer':
            messages.warning(request, 'You do not have permission to access this area.')
            return redirect('eccommence:home')
        
        # Admin, staff, or vendor — allow through
        if request.user.user_type in ['admin', 'staff', 'vendor']:
            return view_func(request, *args, **kwargs)
        
        # Any other unknown type — send home
        messages.warning(request, 'Access denied.')
        return redirect('eccommence:home')
    
    return wrapper


def admin_only(view_func):
    """
    Stricter decorator — only allows admin user type.
    Used for sensitive views like financials, user management, settings.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        
        if not request.user.is_authenticated:
            messages.info(request, 'Please log in.')
            return redirect('users:login')
        
        if request.user.user_type != 'admin':
            messages.error(request, 'This area is restricted to administrators only.')
            return redirect('store_admin:dashboard')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def admin_or_staff_required(view_func):
    """
    Allows admin and staff — blocks vendors from sensitive data
    like full customer lists and financial reports.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        
        if not request.user.is_authenticated:
            messages.info(request, 'Please log in.')
            return redirect('users:login')
        
        if request.user.user_type not in ['admin', 'staff']:
            messages.warning(request, 'Access restricted.')
            return redirect('store_admin:dashboard')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def get_user_access_level(user):
    """
    Helper function that returns a dictionary describing
    exactly what the current user can see and do.
    Used in views and templates to show/hide sections.
    """
    if not user.is_authenticated:
        return {
            'can_view_revenue':    False,
            'can_view_customers':  False,
            'can_view_all_orders': False,
            'can_view_vendors':    False,
            'can_view_staff':      False,
            'can_edit_products':   False,
            'can_edit_settings':   False,
            'can_manage_users':    False,
            'access_level':        'none',
        }

    if user.user_type == 'admin':
        return {
            'can_view_revenue':    True,
            'can_view_customers':  True,
            'can_view_all_orders': True,
            'can_view_vendors':    True,
            'can_view_staff':      True,
            'can_edit_products':   True,
            'can_edit_settings':   True,
            'can_manage_users':    True,
            'access_level':        'admin',
        }

    if user.user_type == 'staff':
        return {
            'can_view_revenue':    False,
            'can_view_customers':  True,
            'can_view_all_orders': True,
            'can_view_vendors':    False,
            'can_view_staff':      False,
            'can_edit_products':   True,
            'can_edit_settings':   False,
            'can_manage_users':    False,
            'access_level':        'staff',
        }

    if user.user_type == 'vendor':
        return {
            'can_view_revenue':    False,
            'can_view_customers':  False,
            'can_view_all_orders': False,
            'can_view_vendors':    False,
            'can_view_staff':      False,
            'can_edit_products':   True,
            'can_edit_settings':   False,
            'can_manage_users':    False,
            'access_level':        'vendor',
        }

    # Fallback
    return {
        'can_view_revenue':    False,
        'can_view_customers':  False,
        'can_view_all_orders': False,
        'can_view_vendors':    False,
        'can_view_staff':      False,
        'can_edit_products':   False,
        'can_edit_settings':   False,
        'can_manage_users':    False,
        'access_level':        'none',
    }