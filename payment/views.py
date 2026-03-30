from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from decimal import Decimal
import requests
import json
import logging

from cart.models import Cart, CartItem
from cart.views import get_or_create_cart
from .models import (
    Order, OrderItem, 
    PaymentTransaction, PaymentMethod, Refund
)
from .forms import ShippingForm, PaymentMethodForm, RefundRequestForm
from eccommence.models import Product, ProductVariant, Customer
from users.models import Address

logger = logging.getLogger(__name__)


# ============= SHIPPING CALCULATION =============

def calculate_shipping(subtotal):
    """
    Calculate shipping cost
    - UGX 3,000 flat rate
    - FREE for orders above UGX 100,000
    """
    FREE_SHIPPING_THRESHOLD = Decimal('100000.00')
    FLAT_SHIPPING_RATE = Decimal('3000.00')
    
    if subtotal >= FREE_SHIPPING_THRESHOLD:
        return Decimal('0.00')
    return FLAT_SHIPPING_RATE


# ============= SHIPPING CALCULATION =============

def calculate_shipping(subtotal):
    """
    Calculate shipping cost
    - UGX 3,000 flat rate
    - FREE for orders above UGX 100,000
    """
    FREE_SHIPPING_THRESHOLD = Decimal('100000.00')
    FLAT_SHIPPING_RATE = Decimal('3000.00')
    
    if subtotal >= FREE_SHIPPING_THRESHOLD:
        return Decimal('0.00')
    return FLAT_SHIPPING_RATE


# ============= CHECKOUT VIEWS =============
def checkout(request):
    """Checkout page with shipping information"""
    
    # Get cart using helper function
    cart = get_or_create_cart(request)
    
    # Get cart items
    cart_items = cart.items.select_related('product', 'variant').all()
    
    # Check if cart is empty
    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty')
        return redirect('cart:cart_detail')
    
    # Require login for checkout
    if not request.user.is_authenticated:
        messages.info(request, 'Please login to complete your order')
        return redirect('users:login')
    
    # Get default shipping address from Address model (users app)
    shipping_address = Address.objects.filter(
        user=request.user,
        address_type='shipping',
        is_default=True
    ).first()
    
    # If no default, get first shipping address
    if not shipping_address:
        shipping_address = Address.objects.filter(
            user=request.user,
            address_type='shipping'
        ).first()
    
    # Handle AJAX address save
    if request.method == 'POST' and 'save_address_only' in request.POST:
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Create form with POST data
        shipping_form = ShippingForm(request.POST)
        
        if shipping_form.is_valid():
            try:
                # Save address to Address model
                address = shipping_form.save(commit=False)
                address.user = request.user  # Use user, not customer
                address.address_type = 'shipping'
                
                # If this is the first address or user selected as default
                if not Address.objects.filter(user=request.user).exists() or request.POST.get('set_as_default'):
                    address.is_default = True
                
                address.save()
                
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': 'Address saved successfully',
                        'address': {
                            'full_name': address.full_name,
                            'email': address.email,
                            'phone': address.phone,
                            'address_line1': address.address_line1,
                            'address_line2': address.address_line2 or '',
                            'city': address.city,
                            'state': address.state,
                            'postal_code': address.postal_code,
                            'country': address.country,
                            'delivery_instructions': address.delivery_instructions,
                        }
                    })
                else:
                    messages.success(request, 'Address saved successfully!')
                    return redirect('payment:checkout')
                    
            except Exception as e:
                logger.error(f"Error saving address: {str(e)}")
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'message': f'Error saving address: {str(e)}'
                    }, status=500)
                else:
                    messages.error(request, 'Error saving address')
        else:
            if is_ajax:
                error_messages = []
                for field, errors in shipping_form.errors.items():
                    error_messages.extend(errors)
                return JsonResponse({
                    'success': False,
                    'message': error_messages[0] if error_messages else 'Please fix the errors in the form',
                    'errors': shipping_form.errors
                }, status=400)
            else:
                messages.error(request, 'Please fix the errors in the form')
    
    # Create form with existing address data if available
    if shipping_address:
        shipping_form = ShippingForm(instance=shipping_address)
    else:
        # Initial data for new address
        initial_data = {
            'full_name': request.user.get_full_name() or request.user.email,
            'email': request.user.email,
            'phone': request.user.phone or '',
            'city': 'Kampala',
            'state': 'Central',
            'country': 'Uganda',
        }
        shipping_form = ShippingForm(initial=initial_data)
    
    # Get cart products
    cart_products = []
    for item in cart_items:
        cart_products.append({
            'product': item.product,
            'quantity': item.quantity,
            'price': item.price,
            'total_price': item.total_price,
        })
    
    quantities = {str(item.product.id): item.quantity for item in cart_items}
    
    # Calculate totals
    subtotal = cart.subtotal
    shipping_cost = calculate_shipping(subtotal)
    tax_rate = getattr(settings, 'TAX_RATE', Decimal('0.00'))
    tax = subtotal * tax_rate
    total = subtotal + shipping_cost + tax
    
    context = {
        'cart_products': cart_products,
        'quantities': quantities,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'tax': tax,
        'total': total,
        'shipping_form': shipping_form,
        'free_shipping_threshold': Decimal('100000.00'),
    }
    
    return render(request, 'checkout.html', context)


def payment_method(request):
    """Payment method selection page"""
    
    # Get cart using helper function
    cart = get_or_create_cart(request)
    
    if not cart.items.exists():
        messages.warning(request, 'Your cart is empty')
        return redirect('cart:cart_detail')
    
    # Require login for checkout
    if not request.user.is_authenticated:
        messages.info(request, 'Please login to complete your order')
        return redirect('users:login')
    
    # Calculate totals
    subtotal = cart.subtotal
    shipping_cost = calculate_shipping(subtotal)
    tax_rate = getattr(settings, 'TAX_RATE', Decimal('0.00'))
    tax = subtotal * tax_rate
    total = subtotal + shipping_cost + tax
    
    # Define available payment methods
    payment_methods_list = [
        {
            'code': 'mtn_mobile_money',
            'name': 'MTN Mobile Money',
            'description': 'Pay with MTN Mobile Money',
            'icon': 'fas fa-mobile-alt',
        },
        {
            'code': 'airtel_money',
            'name': 'Airtel Money',
            'description': 'Pay with Airtel Money',
            'icon': 'fas fa-mobile-alt',
        },
        {
            'code': 'cash_on_delivery',
            'name': 'Cash on Delivery',
            'description': 'Pay when you receive your order',
            'icon': 'fas fa-money-bill-wave',
        },
    ]
    
    # Handle form submission
    if request.method == 'POST':
        payment_method_code = request.POST.get('payment_method')
        
        if payment_method_code in ['mtn_mobile_money', 'airtel_money', 'cash_on_delivery']:
            request.session['payment_method'] = payment_method_code
            return redirect('payment:process_payment')
        else:
            messages.error(request, 'Please select a valid payment method')
    
    context = {
        'payment_methods': payment_methods_list,
        'subtotal': subtotal,
        'shipping_cost': shipping_cost,
        'tax': tax,
        'total': total,
    }
    
    return render(request, 'payment_method.html', context)


@transaction.atomic
def process_payment(request):
    """Process payment and create order"""
    
    if request.method != 'POST':
        return redirect('payment:checkout')
    
    # Get cart using helper function
    cart = get_or_create_cart(request)
    
    if not cart.items.exists():
        messages.warning(request, 'Your cart is empty')
        return redirect('cart:cart_detail')
    
    # Require login
    if not request.user.is_authenticated:
        messages.info(request, 'Please login to complete your order')
        return redirect('users:login')
    
    # Get payment method from POST data
    payment_method = request.POST.get('payment_method')
    
    if not payment_method or payment_method not in ['mtn_mobile_money', 'airtel_money', 'cash_on_delivery']:
        messages.error(request, 'Please select a valid payment method')
        return redirect('payment:checkout')
    
    # Calculate totals
    subtotal = cart.subtotal
    shipping_cost = calculate_shipping(subtotal)
    tax_rate = getattr(settings, 'TAX_RATE', Decimal('0.00'))
    tax = subtotal * tax_rate
    total = subtotal + shipping_cost + tax
    
    # Get shipping information from Address model (users app)
    shipping_address = Address.objects.filter(
        user=request.user,
        address_type='shipping'
    ).first()
    
    # If no shipping address exists, redirect back to checkout to enter address
    if not shipping_address:
        messages.error(request, 'Please provide your shipping address')
        return redirect('payment:checkout')
    
    full_name = shipping_address.full_name
    email = shipping_address.email
    phone = shipping_address.phone
    address = shipping_address.full_address
    delivery_instructions = shipping_address.delivery_instructions
    
    try:
        # Create order
        order = Order.objects.create(
            user=request.user,
            full_name=full_name,
            email=email,
            phone=phone,
            shipping_address=address,
            billing_address=address,
            subtotal=subtotal,
            shipping_cost=shipping_cost,
            tax=tax,
            total=total,
            payment_method=payment_method,
            status='pending',
            customer_note=delivery_instructions,
        )
        
        # Create order items from cart items
        for cart_item in cart.items.all():
            product = cart_item.product
            quantity = cart_item.quantity
            price = cart_item.price
            variant = cart_item.variant
            
            # Check stock availability
            if product.track_inventory:
                available_stock = variant.stock_quantity if variant else product.stock_quantity
                
                if available_stock < quantity:
                    raise ValueError(f'Insufficient stock for {product.name}')
            
            # Get product image
            product_image = ''
            if product.images.exists():
                product_image = product.images.first().image.url
            
            # Create order item
            OrderItem.objects.create(
                order=order,
                product=product,
                product_variant=variant,
                vendor=product.vendor,
                product_name=product.name,
                product_sku=variant.sku if variant else (product.sku or ''),
                product_image=product_image,
                quantity=quantity,
                price=price,
                commission_rate=getattr(product.vendor, 'commission_rate', Decimal('10.00'))
            )
            
            # Update stock
            if product.track_inventory:
                if variant:
                    variant.stock_quantity -= quantity
                    variant.save()
                else:
                    product.stock_quantity -= quantity
                    product.save()
        
        # Clear database cart
        cart.items.all().delete()
        
        # Process payment based on method
        if payment_method == 'cash_on_delivery':
            order.status = 'processing'
            order.save()
            
            PaymentTransaction.objects.create(
                order=order,
                payment_gateway='cash_on_delivery',
                amount=total,
                currency='UGX',
                customer_email=email,
                customer_phone=phone,
                customer_name=full_name,
                ip_address=get_client_ip(request),
                status='pending'
            )
            
            messages.success(request, f'Order {order.order_number} placed successfully!')
            return redirect('payment:payment_success', order_number=order.order_number)
        
        elif payment_method in ['mtn_mobile_money', 'airtel_money']:
            # Redirect to mobile money payment page
            return redirect('payment:mobile_money_payment', order_number=order.order_number)
        
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('cart:cart_detail')
    
    except Exception as e:
        logger.error(f"Order creation error: {str(e)}")
        messages.error(request, 'An error occurred while processing your order')
        return redirect('payment:checkout')

def mobile_money_payment(request, order_number):
    """Mobile money payment page"""
    order = get_object_or_404(Order, order_number=order_number)
    
    if order.is_paid:
        return redirect('payment:payment_success', order_number=order_number)
    
    context = {
        'order': order,
    }
    
    return render(request, 'mobile_money_payment.html', context)


@require_POST
def initiate_mobile_money(request):
    """Initiate mobile money payment"""
    try:
        data = json.loads(request.body)
        order_number = data.get('order_number')
        phone_number = data.get('phone_number')
        
        order = get_object_or_404(Order, order_number=order_number)
        
        network = 'MTN' if order.payment_method == 'mtn_mobile_money' else 'AIRTEL'
        
        payment_transaction = PaymentTransaction.objects.create(
            order=order,
            payment_gateway='flutterwave',
            amount=order.total,
            currency='UGX',
            customer_email=order.email,
            customer_phone=phone_number,
            customer_name=order.full_name,
            ip_address=get_client_ip(request),
        )
        
        flutterwave_key = getattr(settings, 'FLUTTERWAVE_SECRET_KEY', '')
        
        if not flutterwave_key:
            # Test mode
            payment_transaction.status = 'successful'
            payment_transaction.save()
            
            order.is_paid = True
            order.paid_at = timezone.now()
            order.status = 'paid'
            order.save()
            
            # Clear database cart
            if request.user.is_authenticated:
                cart = get_or_create_cart(request)
                cart.items.all().delete()
            
            if 'payment_method' in request.session:
                del request.session['payment_method']
            if 'pending_order' in request.session:
                del request.session['pending_order']
            
            return JsonResponse({
                'success': True,
                'message': 'Payment successful (Test Mode)',
                'redirect_url': f'/payment/success/{order.order_number}/'
            })
        
        # Real Flutterwave integration
        url = "https://api.flutterwave.com/v3/charges?type=mobile_money_uganda"
        
        payload = {
            "tx_ref": payment_transaction.transaction_id,
            "amount": str(order.total),
            "currency": "UGX",
            "network": network,
            "email": order.email,
            "phone_number": phone_number,
            "fullname": order.full_name,
        }
        
        headers = {
            "Authorization": f"Bearer {flutterwave_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()
        
        payment_transaction.gateway_response = response_data
        payment_transaction.gateway_reference = response_data.get('data', {}).get('flw_ref', '')
        payment_transaction.save()
        
        if response_data.get('status') == 'success':
            return JsonResponse({
                'success': True,
                'transaction_id': payment_transaction.transaction_id,
                'message': 'Payment initiated. Please check your phone to complete payment.'
            })
        else:
            payment_transaction.status = 'failed'
            payment_transaction.error_message = response_data.get('message', 'Payment failed')
            payment_transaction.save()
            
            return JsonResponse({
                'success': False,
                'error': response_data.get('message', 'Payment failed')
            })
        
    except Exception as e:
        logger.error(f"Mobile money error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_POST
def verify_mobile_money(request):
    """Verify mobile money payment status"""
    try:
        data = json.loads(request.body)
        transaction_id = data.get('transaction_id')
        
        transaction = get_object_or_404(PaymentTransaction, transaction_id=transaction_id)
        
        if transaction.status == 'successful':
            # Clear database cart
            if request.user.is_authenticated:
                cart = get_or_create_cart(request)
                cart.items.all().delete()
            
            if 'payment_method' in request.session:
                del request.session['payment_method']
            if 'pending_order' in request.session:
                del request.session['pending_order']
            
            return JsonResponse({
                'success': True,
                'status': 'successful',
                'redirect_url': f'/payment/success/{transaction.order.order_number}/'
            })
        
        # In production, check with Flutterwave API here
        
        return JsonResponse({
            'success': True,
            'status': transaction.status
        })
        
    except Exception as e:
        logger.error(f"Verification error: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_POST
def payment_callback(request, gateway):
    """Payment gateway callback"""
    try:
        payload = json.loads(request.body)
        tx_ref = payload.get('data', {}).get('tx_ref')
        status = payload.get('data', {}).get('status')
        
        if tx_ref:
            transaction = PaymentTransaction.objects.filter(transaction_id=tx_ref).first()
            
            if transaction:
                if status == 'successful':
                    transaction.mark_as_successful()
                elif status == 'failed':
                    transaction.mark_as_failed()
                
                transaction.gateway_response = payload
                transaction.save()
        
        return JsonResponse({'status': 'success'})
    
    except Exception as e:
        logger.error(f"Callback error: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)})


def payment_success(request, order_number):
    """Payment success page"""
    try:
        order = Order.objects.get(order_number=order_number)
        
        if request.user.is_authenticated:
            if order.user and order.user != request.user:
                messages.error(request, 'Order not found')
                return redirect('eccommence:home')
        
        context = {
            'order': order,
        }
        
        return render(request, 'payment_success.html', context)
    
    except Order.DoesNotExist:
        messages.error(request, 'Order not found')
        return redirect('eccommence:home')


def payment_failed(request):
    """Payment failed page"""
    return render(request, 'payment_failed.html')


# ============= ORDER MANAGEMENT VIEWS =============

@login_required
def order_history(request):
    """Display user's order history with optional filtering"""
    
    # Get filter parameter from URL
    status_filter = request.GET.get('status', 'all')
    
    # Base queryset
    orders = Order.objects.filter(user=request.user).select_related('user')
    
    # Apply filters
    if status_filter == 'pending':
        orders = orders.filter(status__in=['pending', 'paid'])
    elif status_filter == 'processing':
        orders = orders.filter(status='processing')
    elif status_filter == 'shipped':
        orders = orders.filter(status='shipped')
    elif status_filter == 'delivered':
        orders = orders.filter(status='delivered')
    elif status_filter == 'cancelled':
        orders = orders.filter(status='cancelled')
    elif status_filter == 'refunded':
        orders = orders.filter(status='refunded')
    
    orders = orders.order_by('-created_at')
    
    context = {
        'orders': orders,
        'current_filter': status_filter,
    }
    
    return render(request, 'order_history.html', context)


@login_required
def order_detail(request, order_number):
    """Order detail page"""
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product'),
        order_number=order_number,
        user=request.user
    )
    
    context = {
        'order': order,
    }
    
    return render(request, 'order_detail.html', context)


@login_required
def track_order(request, order_number):
    """Track order page"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    context = {
        'order': order,
    }
    
    return render(request, 'track_order.html', context)


@login_required
@require_POST
def cancel_order(request, order_number):
    """Cancel order"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    if order.status in ['pending', 'paid', 'processing']:
        order.status = 'cancelled'
        order.save()
        
        for item in order.items.all():
            if item.product.track_inventory:
                if item.product_variant:
                    item.product_variant.stock_quantity += item.quantity
                    item.product_variant.save()
                else:
                    item.product.stock_quantity += item.quantity
                    item.product.save()
        
        messages.success(request, f'Order {order_number} has been cancelled')
    else:
        messages.error(request, 'This order cannot be cancelled')
    
    return redirect('payment:order_detail', order_number=order_number)


# ============= REFUND VIEWS =============

@login_required
def request_refund(request, order_number):
    """Request refund for order"""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    
    if order.status != 'delivered':
        messages.error(request, 'Refund can only be requested for delivered orders')
        return redirect('payment:order_detail', order_number=order_number)
    
    if request.method == 'POST':
        form = RefundRequestForm(request.POST, request.FILES)
        
        if form.is_valid():
            refund = form.save(commit=False)
            refund.order = order
            refund.refund_amount = order.total
            refund.save()
            
            messages.success(request, 'Refund request submitted successfully')
            return redirect('payment:order_detail', order_number=order_number)
    else:
        form = RefundRequestForm()
    
    context = {
        'form': form,
        'order': order,
    }
    
    return render(request, 'request_refund.html', context)


# ============= UTILITY FUNCTIONS =============

def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip