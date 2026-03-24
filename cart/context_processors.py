# cart/context_processors.py
from .views import get_or_create_cart, calculate_cart_totals
from .models import SavedForLater

def cart(request):
    """Cart context processor for templates"""
    try:
        cart = get_or_create_cart(request)
        totals = calculate_cart_totals(cart, request.session.get('coupon_code'))
        
        # Get wishlist count for authenticated users
        wishlist_count = 0
        if request.user.is_authenticated:
            try:
                customer = request.user.customer_profile
                wishlist_count = SavedForLater.objects.filter(customer=customer).count()
            except:
                wishlist_count = 0
        
        return {
            'cart': cart,
            'cart_total_items': cart.total_items,
            'cart_subtotal': totals['subtotal'],
            'cart_total': totals['total'],
            'wishlist_count': wishlist_count,
        }
    except Exception:
        return {
            'cart': None,
            'cart_total_items': 0,
            'cart_subtotal': 0,
            'cart_total': 0,
            'wishlist_count': 0,
        }