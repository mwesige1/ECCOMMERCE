# cart/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.db.models import Prefetch, Q
from django.conf import settings
from decimal import Decimal
import json
import logging

from eccommence.models import Product, ProductVariant, ProductImage, Customer, Coupon
from .models import Cart, CartItem, SavedForLater
from .cart import Cart as SessionCart

logger = logging.getLogger(__name__)

# ============= HELPER FUNCTIONS =============

def get_or_create_cart(request):
    """
    Helper function to get or create cart with proper customer handling
    This is the SINGLE source of truth for cart retrieval
    """
    try:
        if request.user.is_authenticated:
            # Get or create customer profile
            try:
                customer = request.user.customer_profile
            except (AttributeError, Customer.DoesNotExist):
                # Create customer profile if it doesn't exist
                customer = Customer.objects.create(
                    user=request.user,
                    phone='',
                    is_verified=False
                )
                messages.info(request, "Profile created automatically. Please complete your profile.")
            
            # Get or create cart for authenticated user
            cart, created = Cart.objects.get_or_create(
                customer=customer,
                defaults={'session_key': ''}
            )
            
            # Check if there's a session cart to merge (for users who added items before login)
            if created or request.session.get('has_guest_cart'):
                merge_guest_cart_to_user_cart(request, cart)
                if 'has_guest_cart' in request.session:
                    del request.session['has_guest_cart']
            
            return cart
        else:
            # For anonymous users
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key
                request.session['has_guest_cart'] = True
            
            cart, created = Cart.objects.get_or_create(
                session_key=session_key,
                defaults={'customer': None}
            )
            return cart
            
    except Exception as e:
        logger.error(f"Error in get_or_create_cart: {str(e)}")
        
        # Fallback: create a session-based cart
        if not request.session.session_key:
            request.session.create()
        cart, _ = Cart.objects.get_or_create(
            session_key=request.session.session_key,
            defaults={'customer': None}
        )
        return cart


def merge_guest_cart_to_user_cart(request, user_cart):
    """Merge guest cart items into user's cart after login"""
    session_key = request.session.get('_auth_user_id')
    if not session_key:
        return
    
    try:
        guest_cart = Cart.objects.filter(session_key=session_key, customer__isnull=True).first()
        if guest_cart:
            for item in guest_cart.items.all():
                cart_item, created = CartItem.objects.get_or_create(
                    cart=user_cart,
                    product=item.product,
                    variant=item.variant,
                    defaults={
                        'quantity': item.quantity,
                        'price': item.price
                    }
                )
                if not created:
                    cart_item.quantity += item.quantity
                    cart_item.save()
            
            guest_cart.delete()
    except Exception as e:
        logger.error(f"Error merging carts: {str(e)}")


# cart/views.py

def calculate_cart_totals(cart, coupon_code=None):
    """
    Calculate all cart totals in one place
    Returns dictionary with all calculated values
    """
    # Get subtotal from cart model
    subtotal = cart.subtotal  # This calls the @property method in Cart model
   
    # Dynamic shipping based on subtotal
    if subtotal >= Decimal('100000.00'):  # Free shipping over 100k UGX
        shipping = Decimal('0.00')
    else:
        total_items = cart.total_items
        if total_items > 5:
            shipping = Decimal('10000.00')
        else:
            shipping = Decimal('5000.00')
    
    # Tax (18% VAT for Uganda) - FIXED: Don't double calculate!
    tax_rate = getattr(settings, 'TAX_RATE', Decimal('0.18'))
    tax = subtotal * tax_rate  # This is correct: 230,000 × 0.18 = 41,400
    
    # Apply coupon if exists
    discount = Decimal('0.00')
    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code)
            if coupon.is_valid() and subtotal >= coupon.min_purchase_amount:
                if coupon.discount_type == 'percentage':
                    discount = subtotal * (coupon.discount_value / 100)
                    if coupon.max_discount_amount:
                        discount = min(discount, coupon.max_discount_amount)
                else:
                    discount = coupon.discount_value
                discount = min(discount, subtotal)
        except Coupon.DoesNotExist:
            coupon_code = None
    
    # Calculate total
    total = subtotal + shipping + tax - discount
    
    # Format to 2 decimal places
    return {
        'subtotal': subtotal.quantize(Decimal('0.01')),
        'shipping': shipping.quantize(Decimal('0.01')),
        'tax': tax.quantize(Decimal('0.01')),
        'discount': discount.quantize(Decimal('0.01')),
        'total': total.quantize(Decimal('0.01')),
        'coupon_code': coupon_code,
    }
# ============= CART VIEWS =============

@never_cache
def cart_detail(request):
    """Cart page - main view for cart"""
    cart = get_or_create_cart(request)
    
    # Sync with session cart if needed
    if request.user.is_authenticated:
        session_cart = SessionCart(request)
        if len(session_cart) > 0:
            merge_guest_cart_to_user_cart(request, cart)
    
    # Get cart items with optimized queries
    cart_items = cart.items.select_related(
        'product', 
        'variant',
        'product__vendor',
        'product__category'
    ).prefetch_related(
        Prefetch('product__images', 
                queryset=ProductImage.objects.filter(is_primary=True))
    ).all()
    
    # Check stock availability
    out_of_stock_items = []
    for item in cart_items:
        available_stock = item.available_stock
        if item.product.track_inventory and item.quantity > available_stock:
            out_of_stock_items.append({
                'item': item,
                'available': available_stock
            })
    
    # Get coupon from session
    coupon_code = request.session.get('coupon_code')
    
    # Calculate totals
    totals = calculate_cart_totals(cart, coupon_code)
    
    # Get recommended products
    recommended_products = []
    if cart_items:
        category_ids = cart_items.values_list('product__category', flat=True).distinct()
        recommended_products = Product.objects.filter(
            category__in=category_ids,
            is_active=True
        ).exclude(
            id__in=cart_items.values_list('product_id', flat=True)
        ).select_related('vendor').prefetch_related(
            Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
        )[:6]
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'out_of_stock_items': out_of_stock_items,
        'recommended_products': recommended_products,
        'cart_total_items': cart.total_items,
        **totals,  # Unpacks subtotal, shipping, tax, discount, total, coupon_code
    }
    
    return render(request, 'cart_detail.html', context)

@require_POST
def cart_add(request):
    """Add item to cart - AJAX endpoint - handles both JSON and form data"""

    try:
        # Check if request is JSON or form data
        content_type = request.META.get('CONTENT_TYPE', '')
        
        if 'application/json' in content_type:
            # Handle JSON data (from cart_detail.html recommended products)
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = int(data.get('quantity', 1))
            variant_id = data.get('variant_id')
        else:
            # Handle form data (from home page, product detail)
            product_id = request.POST.get('product_id')
            quantity = int(request.POST.get('product_qty', request.POST.get('quantity', 1)))
            variant_id = request.POST.get('variant_id')
        
        if not product_id:
            return JsonResponse({'success': False, 'error': 'Product ID required'}, status=400)
            
        if quantity < 1:
            return JsonResponse({'success': False, 'error': 'Invalid quantity'}, status=400)
        
        # Get product
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Product not found'}, status=404)
        
        # Get variant if provided
        variant = None
        if variant_id:
            try:
                variant = ProductVariant.objects.get(id=variant_id, product=product, is_active=True)
                available_stock = variant.stock_quantity
            except ProductVariant.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Variant not found'}, status=404)
        else:
            available_stock = product.stock_quantity if product.track_inventory else 999999
        
        # Check stock
        if product.track_inventory and available_stock < quantity:
            return JsonResponse({
                'success': False, 
                'error': f'Only {available_stock} items available'
            }, status=400)
        
        # Get or create cart
        cart = get_or_create_cart(request)
        
        # Add to database cart
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            variant=variant,
            defaults={
                'quantity': quantity,
                'price': product.current_price + (variant.price_adjustment if variant else 0)
            }
        )
        
        if not created:
            new_quantity = cart_item.quantity + quantity
            if product.track_inventory and available_stock < new_quantity:
                return JsonResponse({
                    'success': False,
                    'error': f'Only {available_stock} items available'
                }, status=400)
            cart_item.quantity = new_quantity
            cart_item.save()
        
        """ # Also add to session cart for consistency
        try:
            session_cart = SessionCart(request)
            session_cart.add(product, quantity, variant, update_quantity=False)
        except Exception as e:
            logger.error(f"Error adding to session cart: {str(e)}")
        """
        # Calculate updated totals
        totals = calculate_cart_totals(cart, request.session.get('coupon_code'))
        
        return JsonResponse({
            'success': True,
            'message': 'Product added to cart',
            'qty': cart.total_items,  # For jQuery compatibility
            'cart_count': cart.total_items,
            'cart_subtotal': str(totals['subtotal']),
            'cart_total': str(totals['total']),
            'item_id': cart_item.id,
        })
        
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Invalid data in cart_add: {str(e)}")
        return JsonResponse({'success': False, 'error': 'Invalid request data'}, status=400)
    except Exception as e:
        logger.error(f"Error in cart_add: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@require_POST
def cart_update(request):
    """Update cart item quantity - AJAX endpoint"""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        quantity = int(data.get('quantity', 1))
        
        if quantity < 0:
            return JsonResponse({'success': False, 'error': 'Invalid quantity'}, status=400)
        
        cart = get_or_create_cart(request)
        
        try:
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
        except CartItem.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Cart item not found'}, status=404)
        
        # If quantity is 0, remove item
        if quantity == 0:
            cart_item.delete()
            message = 'Item removed from cart'
        else:
            # Check stock
            if cart_item.product.track_inventory:
                available_stock = cart_item.available_stock
                if quantity > available_stock:
                    return JsonResponse({
                        'success': False,
                        'error': f'Only {available_stock} items available'
                    }, status=400)
            
            cart_item.quantity = quantity
            cart_item.save()
            message = 'Cart updated successfully'
        
        # Update session cart
        try:
            session_cart = SessionCart(request)
            if quantity == 0:
                session_cart.remove(cart_item.product, cart_item.variant)
            else:
                session_cart.update_quantity(cart_item.product, quantity, cart_item.variant)
        except Exception as e:
            logger.error(f"Error updating session cart: {str(e)}")
        
        # Calculate updated totals
        totals = calculate_cart_totals(cart, request.session.get('coupon_code'))
        
        response_data = {
            'success': True,
            'message': message,
            'cart_count': cart.total_items,
            'cart_subtotal': str(totals['subtotal']),
            'cart_total': str(totals['total']),
        }
        
        if quantity > 0:
            response_data['item_total'] = str(cart_item.total_price)
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)
    except Exception as e:
        logger.error(f"Error in cart_update: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_POST
def cart_remove(request):
    """Remove item from cart - AJAX endpoint"""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        
        cart = get_or_create_cart(request)
        
        try:
            cart_item = CartItem.objects.get(id=item_id, cart=cart)
        except CartItem.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Cart item not found'}, status=404)
        
        # Remove from session cart
        try:
            session_cart = SessionCart(request)
            session_cart.remove(cart_item.product, cart_item.variant)
        except Exception as e:
            logger.error(f"Error removing from session cart: {str(e)}")
        
        # Remove from database
        cart_item.delete()
        
        # Calculate updated totals
        totals = calculate_cart_totals(cart, request.session.get('coupon_code'))
        
        return JsonResponse({
            'success': True,
            'message': 'Item removed from cart',
            'cart_count': cart.total_items,
            'cart_subtotal': str(totals['subtotal']),
            'cart_total': str(totals['total']),
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)
    except Exception as e:
        logger.error(f"Error in cart_remove: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_POST
def cart_clear(request):
    """Clear entire cart"""
    try:
        cart = get_or_create_cart(request)
        cart.clear()
        
        # Clear session cart
        try:
            session_cart = SessionCart(request)
            session_cart.clear()
        except Exception as e:
            logger.error(f"Error clearing session cart: {str(e)}")
        
        # Clear coupon from session
        if 'coupon_code' in request.session:
            del request.session['coupon_code']
        
        messages.success(request, 'Your cart has been cleared.')
        return redirect('cart:cart_detail')
        
    except Exception as e:
        logger.error(f"Error in cart_clear: {str(e)}")
        messages.error(request, 'Error clearing cart.')
        return redirect('cart:cart_detail')


def cart_summary(request):
    """Get cart summary for AJAX calls (header updates)"""
    cart = get_or_create_cart(request)
    totals = calculate_cart_totals(cart, request.session.get('coupon_code'))
    
    return JsonResponse({
        'total_items': cart.total_items,
        'subtotal': str(totals['subtotal']),
        'total': str(totals['total']),
        'shipping': str(totals['shipping']),
        'discount': str(totals['discount']),
    })


# ============= WISHLIST VIEWS =============

@login_required
@require_POST
def wishlist_toggle(request):
    """Add or remove from wishlist"""
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        
        # Get or create customer profile
        try:
            customer = request.user.customer_profile
        except (AttributeError, Customer.DoesNotExist):
            customer = Customer.objects.create(
                user=request.user,
                phone='',
                is_verified=False
            )
        
        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Product not found'}, status=404)
        
        wishlist_item = SavedForLater.objects.filter(customer=customer, product=product).first()
        
        if wishlist_item:
            wishlist_item.delete()
            in_wishlist = False
            message = 'Removed from wishlist'
        else:
            SavedForLater.objects.create(customer=customer, product=product)
            in_wishlist = True
            message = 'Added to wishlist'
        
        wishlist_count = SavedForLater.objects.filter(customer=customer).count()
        
        return JsonResponse({
            'success': True,
            'in_wishlist': in_wishlist,
            'message': message,
            'wishlist_count': wishlist_count
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)
    except Exception as e:
        logger.error(f"Error in wishlist_toggle: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def wishlist_view(request):
    """Wishlist page"""
    try:
        customer = request.user.customer_profile
    except (AttributeError, Customer.DoesNotExist):
        customer = Customer.objects.create(
            user=request.user,
            phone='',
            is_verified=False
        )
    
    wishlist_items = SavedForLater.objects.filter(
        customer=customer
    ).select_related('product').prefetch_related(
        Prefetch('product__images', 
                queryset=ProductImage.objects.filter(is_primary=True))
    )
    
    context = {
        'wishlist_items': wishlist_items,
    }
    
    return render(request, 'wishlist.html', context)


@login_required
@require_POST
def wishlist_add_to_cart(request):
    """Move item from wishlist to cart"""
    try:
        data = json.loads(request.body)
        item_id = data.get('item_id')
        
        customer = request.user.customer_profile
        
        wishlist_item = get_object_or_404(
            SavedForLater, 
            id=item_id, 
            customer=customer
        )
        
        # Add to cart
        cart = get_or_create_cart(request)
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=wishlist_item.product,
            variant=wishlist_item.variant,
            defaults={
                'quantity': 1,
                'price': wishlist_item.product.current_price
            }
        )
        
        if not created:
            cart_item.quantity += 1
            cart_item.save()
        
        # Remove from wishlist
        wishlist_item.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Item moved to cart',
        })
        
    except Exception as e:
        logger.error(f"Error in wishlist_add_to_cart: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ============= COUPON VIEWS =============

@require_POST
def apply_coupon(request):
    """Apply discount coupon"""
    try:
        data = json.loads(request.body)
        code = data.get('code', '').strip().upper()
        
        try:
            coupon = Coupon.objects.get(code=code)
        except Coupon.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Invalid coupon code'}, status=404)
        
        if not coupon.is_valid():
            return JsonResponse({'success': False, 'error': 'This coupon is no longer valid'}, status=400)
        
        cart = get_or_create_cart(request)
        subtotal = cart.subtotal
        
        if subtotal < coupon.min_purchase_amount:
            return JsonResponse({
                'success': False,
                'error': f'Minimum purchase amount is {coupon.min_purchase_amount} UGX'
            }, status=400)
        
        # Store in session
        request.session['coupon_code'] = code
        
        # Calculate discount
        totals = calculate_cart_totals(cart, code)
        
        return JsonResponse({
            'success': True,
            'message': 'Coupon applied successfully',
            'discount': str(totals['discount']),
            'cart_total': str(totals['total']),
            'cart_subtotal': str(totals['subtotal']),
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)
    except Exception as e:
        logger.error(f"Error in apply_coupon: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_POST
def remove_coupon(request):
    """Remove applied coupon"""
    if 'coupon_code' in request.session:
        del request.session['coupon_code']
    
    cart = get_or_create_cart(request)
    totals = calculate_cart_totals(cart, None)
    
    return JsonResponse({
        'success': True,
        'message': 'Coupon removed',
        'cart_total': str(totals['total']),
        'discount': '0.00',
    })