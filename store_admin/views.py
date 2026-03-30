from django.shortcuts import render, get_object_or_404,redirect
from django.contrib.auth.decorators import login_required
from django.db.models import (
    Sum, Count, Q, F, Avg, DecimalField,
    ExpressionWrapper, FloatField
)
from django.db.models.functions import TruncDate, TruncMonth, TruncDay, Coalesce
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta, datetime
from decimal import Decimal

from .decorators import store_admin_required, admin_only, admin_or_staff_required, get_user_access_level
from eccommence.models import Product, Vendor, Category, ProductVariant, Customer
from payment.models import Order, OrderItem, PaymentTransaction
from users.models import User, Address
from cart.models import Cart as CartModel, CartItem
from django.contrib import messages
from django.db import transaction
from eccommence.models import Category, Product, ProductImage, ProductVariant
from django.urls import reverse


from django.views.decorators.csrf import csrf_exempt
import json
    

# ============= PRODUCTS ADD / EDIT =============
@login_required
@store_admin_required
def product_add(request):
    """Add new product"""
    access = get_user_access_level(request.user)
    

    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Get the vendor for this user
                vendor = request.user.vendor_profile
                
                # Create the product
                product = Product()
                product.vendor = vendor
                product.name = request.POST.get('name')
                product.slug = request.POST.get('slug') or product.name.lower().replace(' ', '-')
                product.sku = request.POST.get('sku') or None
                
                # Get category
                category_id = request.POST.get('category')
                if category_id:
                    product.category_id = category_id
                
                product.short_description = request.POST.get('short_description', '')
                product.description = request.POST.get('description', '')
                
                # Pricing
                product.price = Decimal(request.POST.get('price', 0))
                product.compare_at_price = Decimal(request.POST.get('compare_at_price', 0)) if request.POST.get('compare_at_price') else None
                product.cost_per_item = Decimal(request.POST.get('cost_per_item', 0)) if request.POST.get('cost_per_item') else None
                
                # Sale settings
                product.is_on_sale = request.POST.get('is_on_sale') == 'on'
                if product.is_on_sale and request.POST.get('sale_price'):
                    product.sale_price = Decimal(request.POST.get('sale_price'))
                if request.POST.get('sale_end_date'):
                    product.sale_end_date = request.POST.get('sale_end_date')
                
                # Inventory
                product.track_inventory = request.POST.get('track_inventory') == 'on'
                product.stock_quantity = int(request.POST.get('stock_quantity', 0))
                product.low_stock_threshold = int(request.POST.get('low_stock_threshold', 10))
                product.allow_backorder = request.POST.get('allow_backorder') == 'on'
                
                # Physical properties
                if request.POST.get('weight'):
                    product.weight = Decimal(request.POST.get('weight'))
                if request.POST.get('length'):
                    product.length = Decimal(request.POST.get('length'))
                if request.POST.get('width'):
                    product.width = Decimal(request.POST.get('width'))
                if request.POST.get('height'):
                    product.height = Decimal(request.POST.get('height'))
                
                # Status
                product.is_active = request.POST.get('is_active') == 'on'
                product.is_featured = request.POST.get('is_featured') == 'on'
                
                # SEO
                product.meta_title = request.POST.get('meta_title', '')
                product.meta_description = request.POST.get('meta_description', '')
                product.meta_keywords = request.POST.get('meta_keywords', '')
                
                # Save the product
                product.save()
                
                # Handle images - Get images from request.FILES
                images = request.FILES.getlist('images')
                print(f"Number of images received: {len(images)}")  # Debug
                
                for i, image in enumerate(images):
                    ProductImage.objects.create(
                        product=product,
                        image=image,
                        is_primary=(i == 0),  # First image is primary
                        order=i
                    )
                
                # Handle variants
                variant_names = request.POST.getlist('variant_name[]')
                variant_values = request.POST.getlist('variant_value[]')
                variant_skus = request.POST.getlist('variant_sku[]')
                variant_price_adjustments = request.POST.getlist('variant_price_adjustment[]')
                variant_stocks = request.POST.getlist('variant_stock[]')
                
                for i in range(len(variant_names)):
                    if variant_names[i] and variant_values[i]:
                        ProductVariant.objects.create(
                            product=product,
                            name=variant_names[i],
                            value=variant_values[i],
                            sku=variant_skus[i] if i < len(variant_skus) else '',
                            price_adjustment=Decimal(variant_price_adjustments[i]) if i < len(variant_price_adjustments) else 0,
                            stock_quantity=int(variant_stocks[i]) if i < len(variant_stocks) else 0,
                            is_active=True
                        )
                
                # ALWAYS return JSON for AJAX requests
                return JsonResponse({
                    'success': True,
                    'message': f'Product "{product.name}" has been added successfully!',
                    'redirect_url': reverse('store_admin:products')
                })
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    # GET request - show form
    categories = Category.objects.filter(is_active=True)
    context = {
        'access': access,
        'categories': categories,
        'product': None,
    }
    return render(request, 'store_admin/product_form.html', context)


@login_required
@store_admin_required
def product_edit(request, pk):
    """Edit existing product"""
    access = get_user_access_level(request.user)
    product = get_object_or_404(Product, pk=pk)

    # Vendors can only edit their own products
    if not access['can_edit_products'] or (
        request.user.user_type == 'vendor'
        and product.vendor.user != request.user
    ):
        messages.error(request, "You don't have permission to edit this product.")
        return redirect('store_admin:products')

    from eccommence.models import Category, ProductImage, ProductVariant
    from django.urls import reverse
    
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        try:
            with transaction.atomic():
                # Update product fields
                product.name = request.POST.get('name')
                if request.POST.get('slug'):
                    product.slug = request.POST.get('slug')
                
                category_id = request.POST.get('category')
                if category_id:
                    product.category_id = category_id
                
                product.short_description = request.POST.get('short_description', '')
                product.description = request.POST.get('description', '')
                
                # Pricing
                product.price = Decimal(request.POST.get('price', 0))
                product.compare_at_price = Decimal(request.POST.get('compare_at_price', 0)) if request.POST.get('compare_at_price') else None
                product.cost_per_item = Decimal(request.POST.get('cost_per_item', 0)) if request.POST.get('cost_per_item') else None
                
                # Sale settings
                product.is_on_sale = request.POST.get('is_on_sale') == 'on'
                if product.is_on_sale and request.POST.get('sale_price'):
                    product.sale_price = Decimal(request.POST.get('sale_price'))
                else:
                    product.sale_price = None
                if request.POST.get('sale_end_date'):
                    product.sale_end_date = request.POST.get('sale_end_date')
                
                # Inventory
                product.track_inventory = request.POST.get('track_inventory') == 'on'
                product.stock_quantity = int(request.POST.get('stock_quantity', 0))
                product.low_stock_threshold = int(request.POST.get('low_stock_threshold', 10))
                product.allow_backorder = request.POST.get('allow_backorder') == 'on'
                
                # Physical properties
                if request.POST.get('weight'):
                    product.weight = Decimal(request.POST.get('weight'))
                if request.POST.get('length'):
                    product.length = Decimal(request.POST.get('length'))
                if request.POST.get('width'):
                    product.width = Decimal(request.POST.get('width'))
                if request.POST.get('height'):
                    product.height = Decimal(request.POST.get('height'))
                
                # Status
                product.is_active = request.POST.get('is_active') == 'on'
                product.is_featured = request.POST.get('is_featured') == 'on'
                
                # SEO
                product.meta_title = request.POST.get('meta_title', '')
                product.meta_description = request.POST.get('meta_description', '')
                product.meta_keywords = request.POST.get('meta_keywords', '')
                
                # Save the product
                product.save()
                
                # Handle new images - ONLY add new images, don't delete existing
                new_images = request.FILES.getlist('images')
                for i, image in enumerate(new_images):
                    ProductImage.objects.create(
                        product=product,
                        image=image,
                        is_primary=False,  # Don't set as primary automatically
                        order=product.images.count() + i
                    )
                
                # ============================================
                # PRIMARY IMAGE HANDLING - NEW CODE ADDED
                # ============================================
                primary_image_id = request.POST.get('primary_image_id')
                if primary_image_id and primary_image_id != 'new':
                    try:
                        # First, ensure there's at least one image
                        if product.images.exists():
                            # Set all images to not primary first
                            product.images.all().update(is_primary=False)
                            # Set the selected image as primary
                            primary_image = product.images.get(id=primary_image_id)
                            primary_image.is_primary = True
                            primary_image.save()
                            print(f"Primary image set to: {primary_image_id}")
                    except ProductImage.DoesNotExist:
                        print(f"Primary image {primary_image_id} not found")
                    except Exception as e:
                        print(f"Error setting primary image: {e}")
                elif not product.images.filter(is_primary=True).exists() and product.images.exists():
                    # If no primary image is set and there are images, set the first as primary
                    first_image = product.images.first()
                    first_image.is_primary = True
                    first_image.save()
                    print(f"Auto-set first image as primary: {first_image.id}")
                # ============================================
                
                # Handle variants - clear existing and recreate
                product.variants.all().delete()
                
                variant_names = request.POST.getlist('variant_name[]')
                variant_values = request.POST.getlist('variant_value[]')
                variant_skus = request.POST.getlist('variant_sku[]')
                variant_price_adjustments = request.POST.getlist('variant_price_adjustment[]')
                variant_stocks = request.POST.getlist('variant_stock[]')
                
                for i in range(len(variant_names)):
                    if variant_names[i] and variant_values[i]:
                        ProductVariant.objects.create(
                            product=product,
                            name=variant_names[i],
                            value=variant_values[i],
                            sku=variant_skus[i] if i < len(variant_skus) else '',
                            price_adjustment=Decimal(variant_price_adjustments[i]) if i < len(variant_price_adjustments) else 0,
                            stock_quantity=int(variant_stocks[i]) if i < len(variant_stocks) else 0,
                            is_active=True
                        )
                
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': f'Product "{product.name}" has been updated successfully!',
                        'redirect_url': reverse('store_admin:products')
                    })
                else:
                    messages.success(request, f'Product "{product.name}" has been updated successfully!')
                    return redirect('store_admin:products')
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            
            if is_ajax:
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=400)
            else:
                messages.error(request, f'Error updating product: {str(e)}')
                return redirect('store_admin:product_edit', pk=pk)
    
    # GET request - show form
    categories = Category.objects.filter(is_active=True)
    context = {
        'access': access,
        'product': product,
        'categories': categories,
    }
    return render(request, 'store_admin/product_form.html', context)
# ============= PROMOTIONS =============

@login_required
@admin_only
def promotions(request):
    """Promotions / Coupons management (Admin only)"""
    access = get_user_access_level(request.user)

    from eccommence.models import Coupon
    coupons = Coupon.objects.all().order_by('-created_at')

    search = request.GET.get('search')
    if search:
        coupons = coupons.filter(
            Q(code__icontains=search) |
            Q(description__icontains=search)
        )

    context = {
        'access': access,
        'coupons': coupons,
        'search': search,
    }
    return render(request, 'store_admin/promotions.html', context)


# ============= REFUNDS =============

@login_required
@admin_or_staff_required
def refunds(request):
    """Refunds management"""
    access = get_user_access_level(request.user)

    from payment.models import Refund
    from django.db.models import Sum
    
    refunds_qs = Refund.objects.select_related(
        'order', 'order__user'
    ).order_by('-created_at')

    status = request.GET.get('status')
    if status and status != 'all':
        refunds_qs = refunds_qs.filter(status=status)

    search = request.GET.get('search')
    if search:
        refunds_qs = refunds_qs.filter(
            Q(refund_id__icontains=search) |
            Q(order__order_number__icontains=search)
        )

    # Calculate stats for the cards
    total_count = Refund.objects.count()
    pending_count = Refund.objects.filter(status='pending').count()
    approved_count = Refund.objects.filter(status='approved').count()
    rejected_count = Refund.objects.filter(status='rejected').count()
    
    # Calculate amounts
    total_amount = Refund.objects.aggregate(total=Sum('refund_amount'))['total'] or 0
    pending_amount = Refund.objects.filter(status='pending').aggregate(total=Sum('refund_amount'))['total'] or 0
    approved_amount = Refund.objects.filter(status='approved').aggregate(total=Sum('refund_amount'))['total'] or 0
    rejected_amount = Refund.objects.filter(status='rejected').aggregate(total=Sum('refund_amount'))['total'] or 0

    context = {
        'access': access,
        'refunds': refunds_qs,
        'status_filter': status or 'all',
        'search': search,
        # Stats for cards
        'total_count': total_count,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'total_amount': total_amount,
        'pending_amount': pending_amount,
        'approved_amount': approved_amount,
        'rejected_amount': rejected_amount,
    }
    return render(request, 'store_admin/refunds.html', context)
@login_required
@admin_or_staff_required
def get_refund_detail(request, refund_id):
    """Get refund details via AJAX"""
    from payment.models import Refund
    from django.http import JsonResponse
    
    try:
        refund = Refund.objects.select_related('order', 'order__user').get(id=refund_id)
        
        data = {
            'id': refund.id,
            'refund_id': refund.refund_id,
            'order_number': refund.order.order_number,
            'status': refund.status,
            'status_display': refund.get_status_display(),
            'reason': refund.reason,
            'reason_display': refund.get_reason_display(),
            'description': refund.description,
            'refund_amount': float(refund.refund_amount),
            'requested_at': refund.requested_at.strftime('%Y-%m-%d %H:%M:%S'),
            'processed_at': refund.processed_at.strftime('%Y-%m-%d %H:%M:%S') if refund.processed_at else None,
            'admin_notes': refund.admin_notes,
            'rejection_reason': refund.rejection_reason,
            # Order info
            'order_total': float(refund.order.total),
            'payment_method': refund.order.get_payment_method_display(),
            # Customer info
            'customer_name': refund.order.full_name,
            'customer_email': refund.order.email,
            'customer_phone': refund.order.phone,
            # Images
            'images': []
        }
        
        # Add images if they exist
        if refund.image1:
            data['images'].append({'url': refund.image1.url})
        if refund.image2:
            data['images'].append({'url': refund.image2.url})
        if refund.image3:
            data['images'].append({'url': refund.image3.url})
        
        return JsonResponse(data)
        
    except Refund.DoesNotExist:
        return JsonResponse({'error': 'Refund not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@admin_or_staff_required
def process_refund(request, refund_id):
    """Process refund (approve/reject) via AJAX"""
    from payment.models import Refund
    from django.http import JsonResponse
    import json
    from django.utils import timezone
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)
    
    try:
        data = json.loads(request.body)
        action = data.get('action')
        rejection_reason = data.get('rejection_reason', '')
        
        refund = Refund.objects.get(id=refund_id)
        
        if action == 'approve':
            refund.status = 'approved'
            refund.processed_at = timezone.now()
            refund.save()
            
            # Here you would also process the actual refund payment
            # This would involve calling your payment gateway API
            
        elif action == 'reject':
            refund.status = 'rejected'
            refund.processed_at = timezone.now()
            refund.rejection_reason = rejection_reason
            refund.save()
            
        elif action == 'processing':
            refund.status = 'processing'
            refund.processed_at = timezone.now()
            refund.save()
            
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
        
        return JsonResponse({
            'success': True,
            'message': f'Refund {action}ed successfully'
        })
        
    except Refund.DoesNotExist:
        return JsonResponse({'error': 'Refund not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
@login_required
@admin_or_staff_required
def get_order_detail_json(request, order_id):
    """Get order details via AJAX"""
    from payment.models import Order
    from django.http import JsonResponse
    
    try:
        order = Order.objects.get(id=order_id)
        
        # Get order items
        items = []
        for item in order.items.all():
            items.append({
                'product_name': item.product_name,
                'sku': item.product_sku,
                'quantity': item.quantity,
                'price': float(item.price),
                'total': float(item.total),
            })
        
        # Get payment method display - handle both possible method names
        payment_method_display = order.payment_method
        if hasattr(order, 'get_payment_method_display'):
            payment_method_display = order.get_payment_method_display()
        elif order.payment_method == 'mobile_money':
            payment_method_display = 'Mobile Money'
        elif order.payment_method == 'cash_on_delivery':
            payment_method_display = 'Cash on Delivery'
        elif order.payment_method == 'card':
            payment_method_display = 'Card Payment'
        
        data = {
            'success': True,
            'order_number': order.order_number,
            'created_at': order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'status': order.status,
            'status_display': order.get_status_display() if hasattr(order, 'get_status_display') else order.status,
            'payment_method': payment_method_display,
            'payment_status': 'Paid' if order.is_paid else 'Pending',
            'customer_name': order.full_name,
            'customer_email': order.email,
            'customer_phone': order.phone or 'N/A',
            'shipping_address': order.shipping_address,
            'items': items,
            'subtotal': float(order.subtotal),
            'shipping_cost': float(order.shipping_cost),
            'tax': float(order.tax),
            'discount': float(order.discount),
            'total': float(order.total),
        }
        
        return JsonResponse(data)
        
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found'}, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# ============= DASHBOARD EXPORT =============

@login_required
@admin_only
def dashboard_export(request):
    """Export dashboard data as CSV or PDF"""
    import csv
    from django.http import HttpResponse

    export_format = request.GET.get('export', 'csv')
    today         = timezone.now().date()

    if export_format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename="dashboard_export_{today}.csv"'
        )

        writer = csv.writer(response)

        # ── Orders section ──
        writer.writerow(['=== ORDERS ==='])
        writer.writerow([
            'Order Number', 'Customer', 'Email', 'Date',
            'Total (UGX)', 'Status', 'Payment Method'
        ])
        orders_qs = Order.objects.select_related('user').order_by('-created_at')

        date_from = request.GET.get('date_from')
        date_to   = request.GET.get('date_to')
        date_range = request.GET.get('range')

        if date_from and date_to:
            orders_qs = orders_qs.filter(
                created_at__date__gte=date_from,
                created_at__date__lte=date_to
            )
        elif date_range == 'today':
            orders_qs = orders_qs.filter(created_at__date=today)
        elif date_range == '7days':
            orders_qs = orders_qs.filter(
                created_at__date__gte=today - timedelta(days=7)
            )
        elif date_range == '30days':
            orders_qs = orders_qs.filter(
                created_at__date__gte=today - timedelta(days=30)
            )

        for order in orders_qs[:500]:  # Cap at 500 rows
            writer.writerow([
                order.order_number,
                order.full_name or (order.user.get_full_name() if order.user else ''),
                order.email or (order.user.email if order.user else ''),
                order.created_at.strftime('%Y-%m-%d %H:%M'),
                order.total,
                order.get_status_display(),
                order.payment_method,
            ])

        writer.writerow([])  # blank row separator

        # ── Revenue summary ──
        writer.writerow(['=== REVENUE SUMMARY ==='])
        writer.writerow(['Period', 'Revenue (UGX)', 'Orders'])

        summary_qs = orders_qs.filter(status='delivered')
        total_rev  = summary_qs.aggregate(rev=Sum('total'))['rev'] or 0
        writer.writerow(['Selected Period', total_rev, summary_qs.count()])

        return response

    # PDF export — return a helpful message until a PDF library is wired up
    from django.http import HttpResponse
    return HttpResponse(
        "PDF export requires a library like WeasyPrint or ReportLab. "
        "Install with: pip install weasyprint",
        status=501
    )

def _safe_rate(numerator, denominator):
    """Safely compute a percentage 0.0–100.0"""
    try:
        if not denominator:
            return 0.0
        return round((float(numerator) / float(denominator)) * 100, 2)
    except (TypeError, ZeroDivisionError):
        return 0.0


def _build_insights(data):
    """Rules-based insight engine for the Smart Insights panel."""
    insights = []

    if data.get('low_stock_count', 0) > 0:
        insights.append({
            'type': 'danger', 'icon': 'exclamation-triangle',
            'title': 'Stock Alert',
            'message': f"{data['low_stock_count']} product(s) are running low on stock.",
            'action_url': '#low-stock-section', 'action_label': 'View products',
        })

    rate = data.get('cart_abandonment_rate', 0)
    if rate > 70:
        insights.append({
            'type': 'warning', 'icon': 'shopping-cart',
            'title': 'High Cart Abandonment',
            'message': (
                f"Cart abandonment is at {rate:.1f}%. "
                "Consider recovery emails or discount incentives."
            ),
            'action_url': None, 'action_label': None,
        })

    psr = data.get('payment_success_rate', 100)
    if psr < 85:
        insights.append({
            'type': 'danger', 'icon': 'credit-card',
            'title': 'High Payment Failure Rate',
            'message': (
                f"Only {psr:.1f}% of payments are succeeding. "
                "Check your Mobile Money and card gateway configurations."
            ),
            'action_url': None, 'action_label': None,
        })

    otr = data.get('on_time_delivery_rate', 100)
    if otr < 80:
        insights.append({
            'type': 'warning', 'icon': 'truck',
            'title': 'Delivery Performance Dropping',
            'message': (
                f"On-time delivery is at {otr:.1f}%. "
                "Review logistics partners and vendor fulfillment SLAs."
            ),
            'action_url': None, 'action_label': None,
        })

    rr = data.get('refund_rate', 0)
    if rr > 5:
        insights.append({
            'type': 'warning', 'icon': 'undo',
            'title': 'Elevated Refund Rate',
            'message': (
                f"Refund rate is at {rr:.1f}%. "
                "Check top-refunded vendors or product quality issues."
            ),
            'action_url': None, 'action_label': None,
        })

    pv = data.get('pending_vendors', 0)
    if pv > 0:
        insights.append({
            'type': 'info', 'icon': 'store-alt',
            'title': f"{pv} Vendor(s) Awaiting Approval",
            'message': "New vendor applications are pending your review.",
            'action_url': '/manage/vendors/?status=pending',
            'action_label': 'Review now',
        })

    if not insights:
        insights.append({
            'type': 'success', 'icon': 'check-circle',
            'title': 'Everything looks great!',
            'message': 'No critical issues detected. Your store is running smoothly.',
            'action_url': None, 'action_label': None,
        })

    return insights


# ============= MAIN DASHBOARD =============

@login_required
@store_admin_required
def dashboard(request):
    """
    Main shop dashboard — KPIs, charts, vendor scorecard, smart insights.

    ROOT CAUSE OF THE Avg('total') BUG:
    Order.total IS a real DecimalField, so Avg('total') is valid SQL.
    The crash happened because previous code used aggregate(total=Sum('total'))
    — naming the OUTPUT key 'total' the same as the SOURCE field.
    Django's ORM then saw 'total' as an existing aggregate, not the field,
    causing the FieldError on the next Avg('total') call.
    Fix: always use a DIFFERENT name for aggregate output keys, e.g. 'rev',
    'avg_val', 'cnt' — never reuse the source field name.
    """

    access = get_user_access_level(request.user)

    today       = timezone.now().date()
    today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    today_end   = timezone.make_aware(datetime.combine(today, datetime.max.time()))

    now                   = timezone.now()
    current_period_start  = now - timedelta(days=30)
    previous_period_start = now - timedelta(days=60)
    previous_period_end   = now - timedelta(days=30)

    # =========================================================
    # 1. REVENUE  (admin / staff only)
    # =========================================================
    if access['can_view_revenue']:

        # ── Totals ──────────────────────────────────────────
        # Output key 'rev' avoids clash with field name 'total'
        total_revenue_today = Order.objects.filter(
            status='delivered',
            paid_at__range=[today_start, today_end]
        ).aggregate(rev=Sum('total'))['rev'] or Decimal('0.00')

        total_revenue_month = Order.objects.filter(
            status='delivered',
            paid_at__month=today.month,
            paid_at__year=today.year
        ).aggregate(rev=Sum('total'))['rev'] or Decimal('0.00')

        total_revenue_all = Order.objects.filter(
            status='delivered'
        ).aggregate(rev=Sum('total'))['rev'] or Decimal('0.00')

        # ── Average Order Value ──────────────────────────────
        # Output key 'avg_val' avoids clash with field name 'total'
        avg_order_value = Order.objects.filter(
            status__in=['delivered', 'processing', 'shipped']
        ).aggregate(avg_val=Avg('total'))['avg_val'] or Decimal('0.00')

        avg_order_value_today = Order.objects.filter(
            created_at__range=[today_start, today_end]
        ).aggregate(avg_val=Avg('total'))['avg_val'] or Decimal('0.00')

        current_aov = Order.objects.filter(
            created_at__gte=current_period_start
        ).aggregate(avg_val=Avg('total'))['avg_val'] or Decimal('0.00')

        previous_aov = Order.objects.filter(
            created_at__gte=previous_period_start,
            created_at__lt=previous_period_end
        ).aggregate(avg_val=Avg('total'))['avg_val'] or Decimal('0.00')

        aov_trend = (
            round(float(current_aov - previous_aov) / float(previous_aov) * 100, 1)
            if previous_aov else 0.0
        )

        # ── Refunds ──────────────────────────────────────────
        refunded_qs    = Order.objects.filter(status='refunded')
        total_refunded = refunded_qs.aggregate(rev=Sum('total'))['rev'] or Decimal('0.00')
        refunds_today  = refunded_qs.filter(
            updated_at__range=[today_start, today_end]
        ).count()
        total_delivered_count = Order.objects.filter(status='delivered').count()
        refund_rate = _safe_rate(refunded_qs.count(), total_delivered_count)

        # ── Payment success rate ─────────────────────────────
        # PaymentTransaction.status choices:
        # pending, processing, successful, failed, cancelled, refunded
        total_txns            = PaymentTransaction.objects.count()
        failed_txns           = PaymentTransaction.objects.filter(status='failed').count()
        failed_payments_today = PaymentTransaction.objects.filter(
            status='failed',
            created_at__range=[today_start, today_end]
        ).count()
        payment_success_rate = _safe_rate(total_txns - failed_txns, total_txns)

        # ── Payment methods breakdown ────────────────────────
        # Field is 'payment_gateway', NOT 'payment_method'
        raw_methods = list(
            PaymentTransaction.objects
            .filter(status='successful')
            .values('payment_gateway')
            .annotate(count=Count('id'), total_amount=Sum('amount'))
            .order_by('-count')
        )
        payment_methods_data = [
            {
                'method': row.get('payment_gateway') or 'Unknown',
                'count':  row['count'],
                'total':  float(row['total_amount'] or 0),
            }
            for row in raw_methods
        ]

        # ── Revenue by category ──────────────────────────────
        # OrderItem.total is a real DecimalField — safe to Sum directly
        category_revenue = list(
            Category.objects.annotate(
                revenue=Coalesce(
                    Sum(
                        'products__order_items__total',
                        filter=Q(products__order_items__order__status='delivered')
                    ),
                    Decimal('0.00')
                )
            ).values('name', 'revenue').order_by('-revenue')[:8]
        )
        for c in category_revenue:
            c['revenue'] = float(c['revenue'])

    else:
        (
            total_revenue_today, total_revenue_month, total_revenue_all,
            avg_order_value, avg_order_value_today, aov_trend,
            total_refunded, refunds_today, refund_rate,
            payment_success_rate, failed_payments_today,
            payment_methods_data, category_revenue,
        ) = (
            Decimal('0.00'), Decimal('0.00'), Decimal('0.00'),
            Decimal('0.00'), Decimal('0.00'), 0.0,
            Decimal('0.00'), 0, 0.0,
            0.0, 0, [], [],
        )

    # =========================================================
    # 2. ORDERS
    # =========================================================
    if access['can_view_all_orders']:
        total_orders_today = Order.objects.filter(created_at__date=today).count()
        total_orders_all   = Order.objects.count()

        orders_by_status = {
            s: Order.objects.filter(status=s).count()
            for s in ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
        }

        # On-time delivery: delivered within 3 days of order creation
        # Order has delivered_at field
        delivered_qs = Order.objects.filter(status='delivered')
        on_time_count = delivered_qs.filter(
            delivered_at__isnull=False,
            delivered_at__lte=F('created_at') + timedelta(days=3)
        ).count()
        on_time_delivery_rate = _safe_rate(on_time_count, delivered_qs.count())
        late_deliveries_today = delivered_qs.filter(
            delivered_at__date=today,
            delivered_at__gt=F('created_at') + timedelta(days=3)
        ).count()

    else:
        vendor_items = OrderItem.objects.filter(vendor__user=request.user)
        total_orders_today = (
            vendor_items.filter(order__created_at__date=today)
            .values('order').distinct().count()
        )
        total_orders_all = vendor_items.values('order').distinct().count()
        orders_by_status = {
            s: vendor_items.filter(order__status=s).values('order').distinct().count()
            for s in ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
        }
        on_time_delivery_rate = 0.0
        late_deliveries_today = 0

    # =========================================================
    # 3. CART ABANDONMENT
    # Cart model has NO status field — estimate from carts with items
    # that don't have a corresponding completed order
    # =========================================================
    try:
        # Customers who completed an order in the last 30 days = converted
        converted_user_ids = Order.objects.filter(
            created_at__gte=current_period_start,
            status__in=['paid', 'processing', 'shipped', 'delivered']
        ).values_list('user_id', flat=True).distinct()

        carts_with_items = CartModel.objects.filter(
            items__isnull=False
        ).distinct()

        total_carts_with_items = carts_with_items.count()

        # Abandoned = has items but customer hasn't completed an order recently
        abandoned_carts = carts_with_items.exclude(
            customer__user_id__in=converted_user_ids
        ).count()

        abandoned_carts_today = carts_with_items.filter(
            updated_at__date=today
        ).exclude(
            customer__user_id__in=converted_user_ids
        ).count()

        cart_abandonment_rate = _safe_rate(abandoned_carts, total_carts_with_items)

    except Exception:
        abandoned_carts = abandoned_carts_today = 0
        cart_abandonment_rate = 0.0

    # =========================================================
    # 4. CUSTOMERS  (admin / staff only)
    # =========================================================
    if access['can_view_customers']:
        total_customers     = User.objects.filter(user_type='customer').count()
        new_customers_today = User.objects.filter(
            user_type='customer', date_joined__date=today
        ).count()

        avg_customer_lifetime_value = (
            User.objects.filter(user_type='customer')
            .annotate(
                ltv=Coalesce(
                    Sum('orders__total', filter=Q(orders__status='delivered')),
                    Decimal('0.00')
                )
            )
            .aggregate(avg_ltv=Avg('ltv'))['avg_ltv'] or Decimal('0.00')
        )

        # Annotated to avoid N+1 on order_count and lifetime_value
        recent_customers = (
            User.objects.filter(user_type='customer')
                .select_related('customer_profile')  # ← CHANGE 'profile' TO 'customer_profile'
                .annotate(
                order_count=Count('orders', distinct=True),
                lifetime_value=Coalesce(
                    Sum('orders__total', filter=Q(orders__status='delivered')),
                     Decimal('0.00')
                )
        )
    .order_by('-date_joined')[:10]
)
    else:
        total_customers = new_customers_today = 0
        avg_customer_lifetime_value = Decimal('0.00')
        recent_customers = []

    # =========================================================
    # 5. PRODUCTS
    # =========================================================
    if access['can_edit_products']:
        total_products          = Product.objects.filter(is_active=True).count()
        total_products_inactive = Product.objects.filter(is_active=False).count()
        low_stock_products = (
            Product.objects
            .filter(
                track_inventory=True,
                stock_quantity__lte=F('low_stock_threshold'),
                is_active=True
            )
            .select_related('vendor')[:10]
        )
        low_stock_count = low_stock_products.count()
        out_of_stock    = Product.objects.filter(
            track_inventory=True, stock_quantity=0, is_active=True
        ).count()
    else:
        vp = Product.objects.filter(vendor__user=request.user)
        total_products          = vp.filter(is_active=True).count()
        total_products_inactive = vp.filter(is_active=False).count()
        low_stock_products = vp.filter(
            track_inventory=True,
            stock_quantity__lte=F('low_stock_threshold'),
            is_active=True
        )[:10]
        low_stock_count = low_stock_products.count()
        out_of_stock    = vp.filter(
            track_inventory=True, stock_quantity=0, is_active=True
        ).count()

    # =========================================================
    # 6. VENDORS  (admin only)
    # =========================================================
    if access['can_view_vendors']:
        total_vendors    = Vendor.objects.filter(is_active=True).count()
        pending_vendors  = Vendor.objects.filter(is_active=False, is_verified=False).count()
        verified_vendors = Vendor.objects.filter(is_verified=True).count()

        vendor_perf_qs = (
            Vendor.objects.filter(is_active=True)
            .select_related('user')
            .annotate(
                total_orders=Count('order_items__order', distinct=True),
                # OrderItem.total is a real field — safe to Sum
                total_revenue=Coalesce(
                    Sum(
                        'order_items__total',
                        filter=Q(order_items__order__status='delivered')
                    ),
                    Decimal('0.00')
                ),
                total_products_count=Count(
                    'products', filter=Q(products__is_active=True)
                ),
                avg_rating=Avg('products__reviews__rating'),
            )
            .order_by('-total_revenue')[:10]
        )

        vendor_performance = []
        for v in vendor_perf_qs:
            v_delivered       = Order.objects.filter(items__vendor=v, status='delivered').distinct()
            v_delivered_count = v_delivered.count()
            v_on_time         = v_delivered.filter(
                delivered_at__isnull=False,
                delivered_at__lte=F('created_at') + timedelta(days=3)
            ).count()
            v_refunded = Order.objects.filter(
                items__vendor=v, status='refunded'
            ).distinct().count()

            vendor_performance.append({
                'store_name':     v.store_name,
                'total_orders':   v.total_orders,
                'total_revenue':  v.total_revenue,
                'total_products': v.total_products_count,
                'avg_rating':     round(float(v.avg_rating or 0), 1),
                'is_verified':    v.is_verified,
                'on_time_rate':   _safe_rate(v_on_time, v_delivered_count),
                'refund_rate':    _safe_rate(v_refunded, v_delivered_count),
            })
    else:
        total_vendors = pending_vendors = verified_vendors = 0
        vendor_performance = []

    # =========================================================
    # 7. REVENUE CHART DATA  (last 30 days)
    #
    # THE ROOT CAUSE FIX IS HERE:
    # Previously: day_qs.aggregate(total=Sum('total'), ..., avg=Avg('total'))
    # When Django sees aggregate(total=Sum('total')), it registers 'total' as
    # an aggregate expression. The subsequent Avg('total') then resolves
    # 'total' as that aggregate — not the DB field — causing the FieldError.
    #
    # Fix: use output keys that NEVER match any source field name:
    #   'rev' instead of 'total', 'avg_val' instead of 'avg'
    # =========================================================
    revenue_chart_data = []
    if access['can_view_revenue']:
        for i in range(29, -1, -1):
            date      = today - timedelta(days=i)
            day_start = timezone.make_aware(datetime.combine(date, datetime.min.time()))
            day_end   = timezone.make_aware(datetime.combine(date, datetime.max.time()))

            day_qs = Order.objects.filter(
                status='delivered',
                paid_at__range=[day_start, day_end]
            )

            # ✅ Output keys 'rev', 'cnt', 'avg_val' — none clash with any field name
            day_agg = day_qs.aggregate(
                rev=Sum('total'),
                cnt=Count('id'),
                avg_val=Avg('total'),
            )

            revenue_chart_data.append({
                'date':        date.strftime('%b %d'),
                'revenue':     float(day_agg['rev'] or 0),
                'order_count': day_agg['cnt'] or 0,
                'aov':         float(day_agg['avg_val'] or 0),
            })

    # =========================================================
    # 8. RECENT ORDERS  (item_count annotated — no N+1)
    # =========================================================
    if access['can_view_all_orders']:
        recent_orders = (
            Order.objects
            .select_related('user')
            .prefetch_related('items__product')
            .annotate(item_count=Count('items', distinct=True))
            .order_by('-created_at')[:10]
        )
    else:
        recent_orders = (
            Order.objects
            .filter(items__vendor__user=request.user)
            .select_related('user')
            .prefetch_related('items__product')
            .annotate(item_count=Count('items', distinct=True))
            .distinct()
            .order_by('-created_at')[:10]
        )

    # =========================================================
    # 9. TOP PRODUCTS
    # OrderItem.total is a real DecimalField — Sum it directly
    # =========================================================
    top_product_base = (
        Product.objects.filter(is_active=True)
        if access['can_edit_products']
        else Product.objects.filter(vendor__user=request.user, is_active=True)
    )

    top_products = (
        top_product_base
        .select_related('vendor')
        .prefetch_related('images')
        .annotate(
            total_sold=Coalesce(Sum('order_items__quantity'), 0),
            # Use 'order_items__total' (OrderItem.total = real field)
            total_revenue=Coalesce(
                Sum(
                    'order_items__total',
                    filter=Q(order_items__order__status='delivered')
                ),
                Decimal('0.00')
            )
        )
        .order_by('-total_sold')[:5]
    )

    # =========================================================
    # 10. SMART INSIGHTS
    # =========================================================
    insights = _build_insights({
        'low_stock_count':       low_stock_count,
        'cart_abandonment_rate': cart_abandonment_rate,
        'payment_success_rate':  payment_success_rate,
        'on_time_delivery_rate': on_time_delivery_rate,
        'refund_rate':           refund_rate,
        'pending_vendors':       pending_vendors,
    })

    # =========================================================
    # CONTEXT
    # =========================================================
    context = {
        'access': access,

        # Revenue KPIs
        'total_revenue_today':         total_revenue_today,
        'total_revenue_month':         total_revenue_month,
        'total_revenue_all':           total_revenue_all,
        'avg_order_value':             avg_order_value,
        'avg_order_value_today':       avg_order_value_today,
        'aov_trend':                   aov_trend,

        # Refunds
        'total_refunded':              total_refunded,
        'refunds_today':               refunds_today,
        'refund_rate':                 refund_rate,

        # Payments
        'payment_success_rate':        payment_success_rate,
        'failed_payments_today':       failed_payments_today,
        'payment_methods_data':        payment_methods_data,

        # Orders
        'total_orders_today':          total_orders_today,
        'total_orders_all':            total_orders_all,
        'orders_by_status':            orders_by_status,
        'on_time_delivery_rate':       on_time_delivery_rate,
        'late_deliveries_today':       late_deliveries_today,
        'recent_orders':               recent_orders,  # ← ADD THIS LINE


        # Cart
        'cart_abandonment_rate':       cart_abandonment_rate,
        'abandoned_carts_today':       abandoned_carts_today,

        # Customers
        'total_customers':             total_customers,
        'new_customers_today':         new_customers_today,
        'avg_customer_lifetime_value': avg_customer_lifetime_value,
        'recent_customers':            recent_customers,

        # Products
        'total_products':              total_products,
        'total_products_inactive':     total_products_inactive,
        'low_stock_products':          low_stock_products,
        'low_stock_count':             low_stock_count,
        'out_of_stock':                out_of_stock,
        'top_products':                top_products,

        # Vendors
        'total_vendors':               total_vendors,
        'pending_vendors':             pending_vendors,
        'verified_vendors':            verified_vendors,
        'vendor_performance':          vendor_performance,

        # Charts
        'revenue_chart_data':          revenue_chart_data,
        'category_revenue':            category_revenue,

        # Insights
        'insights':                    insights,
    }

    return render(request, 'store_admin/dashboard.html', context)


# ============= ORDERS MANAGEMENT =============
@login_required
@store_admin_required
def orders(request):
    """List all orders with filtering"""
    access = get_user_access_level(request.user)

    if access['can_view_all_orders']:
        orders_list = Order.objects.select_related('user').prefetch_related('items')
    else:
        orders_list = (
            Order.objects.filter(items__vendor__user=request.user)
            .select_related('user').distinct().prefetch_related('items')
        )

    status = request.GET.get('status')
    if status and status != 'all':
        orders_list = orders_list.filter(status=status)

    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        orders_list = orders_list.filter(created_at__date__gte=date_from)
    if date_to:
        orders_list = orders_list.filter(created_at__date__lte=date_to)

    search = request.GET.get('search')
    if search:
        orders_list = orders_list.filter(
            Q(order_number__icontains=search) |
            Q(user__email__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(full_name__icontains=search) |
            Q(email__icontains=search)
        )

    orders_list = orders_list.order_by('-created_at')
    
    # Calculate counts for stats cards
    pending_count = orders_list.filter(status='pending').count()
    processing_count = orders_list.filter(status='processing').count()
    shipped_count = orders_list.filter(status='shipped').count()
    delivered_count = orders_list.filter(status='delivered').count()
    cancelled_count = orders_list.filter(status='cancelled').count()
    
    # Calculate amounts
    pending_amount = orders_list.filter(status='pending').aggregate(Sum('total'))['total__sum'] or 0
    processing_amount = orders_list.filter(status='processing').aggregate(Sum('total'))['total__sum'] or 0
    shipped_amount = orders_list.filter(status='shipped').aggregate(Sum('total'))['total__sum'] or 0
    delivered_amount = orders_list.filter(status='delivered').aggregate(Sum('total'))['total__sum'] or 0
    cancelled_amount = orders_list.filter(status='cancelled').aggregate(Sum('total'))['total__sum'] or 0

    context = {
        'access': access,
        'orders': orders_list,
        'status_filter': status or 'all',
        'date_from': date_from,
        'date_to': date_to,
        'search': search,
        'order_statuses': ['pending', 'processing', 'shipped', 'delivered', 'cancelled'],
        'pending_count': pending_count,
        'processing_count': processing_count,
        'shipped_count': shipped_count,
        'delivered_count': delivered_count,
        'cancelled_count': cancelled_count,
        'pending_amount': pending_amount,
        'processing_amount': processing_amount,
        'shipped_amount': shipped_amount,
        'delivered_amount': delivered_amount,
        'cancelled_amount': cancelled_amount,
    }
    return render(request, 'store_admin/orders.html', context)


@login_required
@store_admin_required
def order_detail(request, order_number):
    """View single order details"""
    access = get_user_access_level(request.user)

    if access['can_view_all_orders']:
        order = get_object_or_404(
            Order.objects.select_related('user').prefetch_related(
                'items__product', 'items__vendor', 'payment_transactions'
            ),
            order_number=order_number
        )
    else:
        order = get_object_or_404(
            Order.objects.filter(items__vendor__user=request.user)
            .select_related('user')
            .prefetch_related('items__product', 'items__vendor')
            .distinct(),
            order_number=order_number
        )

    context = {'access': access, 'order': order}
    return render(request, 'store_admin/order_detail.html', context)


# ============= PRODUCTS MANAGEMENT =============
@login_required
@store_admin_required
def products(request):
    """List all products"""
    access = get_user_access_level(request.user)

    if access['can_edit_products'] and request.user.user_type in ['admin', 'staff']:
        products_list = (
            Product.objects.select_related('vendor', 'category')
            .prefetch_related('images')
        )
    else:
        products_list = (
            Product.objects.filter(vendor__user=request.user)
            .select_related('vendor', 'category')
            .prefetch_related('images')
        )

    status = request.GET.get('status')
    if status == 'active':
        products_list = products_list.filter(is_active=True)
    elif status == 'inactive':
        products_list = products_list.filter(is_active=False)
    elif status == 'low_stock':
        products_list = products_list.filter(
            track_inventory=True, stock_quantity__lte=F('low_stock_threshold')
        )
    elif status == 'out_of_stock':
        products_list = products_list.filter(track_inventory=True, stock_quantity=0)

    category_id = request.GET.get('category')
    if category_id:
        products_list = products_list.filter(category_id=category_id)

    search = request.GET.get('search')
    if search:
        products_list = products_list.filter(
            Q(name__icontains=search) |
            Q(sku__icontains=search) |
            Q(description__icontains=search)
        )

    products_list = products_list.order_by('-created_at')
    
    # Get all categories and vendors for filters
    categories = Category.objects.filter(is_active=True)
    vendors = Vendor.objects.filter(is_active=True)
    
    # Calculate stats
    total_products = products_list.count()
    active_products = products_list.filter(is_active=True).count()
    inactive_products = products_list.filter(is_active=False).count()
    low_stock_count = products_list.filter(
        track_inventory=True, 
        stock_quantity__gt=0,
        stock_quantity__lte=F('low_stock_threshold')
    ).count()
    out_of_stock = products_list.filter(
        track_inventory=True, 
        stock_quantity=0
    ).count()

    context = {
        'access': access,
        'products': products_list,
        'categories': categories,
        'vendors': vendors,
        'total_products': total_products,
        'active_products': active_products,
        'inactive_products': inactive_products,
        'low_stock_count': low_stock_count,
        'out_of_stock': out_of_stock,
    }
    return render(request, 'store_admin/products.html', context)

# ============= CUSTOMERS MANAGEMENT =============

@login_required
@admin_or_staff_required
def customers(request):
    """List all customers"""
    access = get_user_access_level(request.user)

    customers_list = (
        User.objects.filter(user_type='customer')
        .select_related('customer_profile')  # ← CHANGE THIS: 'profile' → 'customer_profile'
        .annotate(
            total_orders=Count('orders', distinct=True),
            total_spent=Coalesce(
                Sum('orders__total', filter=Q(orders__status='delivered')),
                Decimal('0.00')
            )
        )
    )

    # Calculate average order value per customer
    for customer in customers_list:
        if customer.total_orders > 0:
            customer.avg_order_value = customer.total_spent / customer.total_orders
        else:
            customer.avg_order_value = Decimal('0.00')

    search = request.GET.get('search')
    if search:
        customers_list = customers_list.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(phone__icontains=search)
        )

    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        customers_list = customers_list.filter(date_joined__date__gte=date_from)
    if date_to:
        customers_list = customers_list.filter(date_joined__date__lte=date_to)

    customers_list = customers_list.order_by('-date_joined')

    # Add stats for the template
    context = {
        'access': access,
        'customers': customers_list,
        'search': search,
        'date_from': date_from,
        'date_to': date_to,
        'total_customers': customers_list.count(),
        'active_customers': customers_list.filter(is_active=True).count(),
        'inactive_customers': customers_list.filter(is_active=False).count(),
        'verified_customers': customers_list.filter(is_verified=True).count(),
        'high_value_customers': customers_list.filter(total_spent__gte=500000).count(),
        'new_customers_30d': customers_list.filter(date_joined__gte=timezone.now() - timedelta(days=30)).count(),
    }
    return render(request, 'store_admin/customers.html', context)

@login_required
@admin_or_staff_required
def customer_detail(request, pk):
    """View single customer details"""
    access   = get_user_access_level(request.user)
    customer = get_object_or_404(
        User.objects.filter(user_type='customer').select_related('profile'), pk=pk
    )
    orders_qs    = Order.objects.filter(user=customer).order_by('-created_at')
    addresses    = Address.objects.filter(user=customer)
    total_orders = orders_qs.count()
    total_spent  = (
        orders_qs.filter(status='delivered')
        .aggregate(rev=Sum('total'))['rev'] or Decimal('0.00')
    )
    avg_order_value = (
        float(total_spent) / total_orders if total_orders else 0
    )

    context = {
        'access': access,
        'customer': customer,
        'orders': orders_qs,
        'addresses': addresses,
        'total_orders': total_orders,
        'total_spent': total_spent,
        'avg_order_value': avg_order_value,
    }
    return render(request, 'store_admin/customer_detail.html', context)


# ============= VENDORS MANAGEMENT =============

@login_required
@admin_only
def vendors(request):
    """List all vendors (Admin only)"""
    access = get_user_access_level(request.user)

    vendors_list = (
        Vendor.objects.select_related('user')
        .annotate(
            total_products=Count('products', filter=Q(products__is_active=True)),
            total_sales=Coalesce(Sum('order_items__quantity'), 0),
            # OrderItem.total is a real field — safe
            total_revenue=Coalesce(
                Sum(
                    'order_items__total',
                    filter=Q(order_items__order__status='delivered')
                ),
                Decimal('0.00')
            )
        )
    )

    status = request.GET.get('status')
    if status == 'active':
        vendors_list = vendors_list.filter(is_active=True)
    elif status == 'inactive':
        vendors_list = vendors_list.filter(is_active=False)
    elif status == 'verified':
        vendors_list = vendors_list.filter(is_verified=True)
    elif status == 'pending':
        vendors_list = vendors_list.filter(is_verified=False, is_active=False)

    search = request.GET.get('search')
    if search:
        vendors_list = vendors_list.filter(
            Q(store_name__icontains=search) |
            Q(business_email__icontains=search) |
            Q(user__email__icontains=search)
        )

    vendors_list = vendors_list.order_by('-created_at')

    context = {
        'access': access,
        'vendors': vendors_list,
        'status_filter': status or 'all',
        'search': search,
    }
    return render(request, 'store_admin/vendors.html', context)


# ============= STAFF MANAGEMENT =============

@login_required
@admin_only
def staff(request):
    """List all staff members (Admin only)"""
    access     = get_user_access_level(request.user)
    staff_list = (
        User.objects.filter(user_type='staff')
        .select_related('profile')
        .order_by('-date_joined')
    )
    context = {'access': access, 'staff': staff_list}
    return render(request, 'store_admin/staff.html', context)


# ============= ANALYTICS =============

@login_required
@admin_only
def analytics(request):
    """Advanced analytics page (Admin only)"""
    access = get_user_access_level(request.user)
    today  = timezone.now().date()

    monthly_sales = []
    for i in range(11, -1, -1):
        month       = today - timedelta(days=30 * i)
        month_start = month.replace(day=1)
        if month.month == 12:
            month_end = month.replace(year=month.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = month.replace(month=month.month + 1, day=1) - timedelta(days=1)

        ms_aware = timezone.make_aware(datetime.combine(month_start, datetime.min.time()))
        me_aware = timezone.make_aware(datetime.combine(month_end,   datetime.max.time()))

        # Output key 'rev' — avoids any potential clash
        rev = Order.objects.filter(
            status='delivered', paid_at__range=[ms_aware, me_aware]
        ).aggregate(rev=Sum('total'))['rev'] or 0

        monthly_sales.append({
            'month':   month_start.strftime('%b %Y'),
            'revenue': float(rev),
        })

    top_vendors = (
        Vendor.objects.filter(is_active=True)
        .annotate(
            total_sales=Coalesce(Sum('order_items__quantity'), 0),
            total_revenue=Coalesce(
                Sum(
                    'order_items__total',
                    filter=Q(order_items__order__status='delivered')
                ),
                Decimal('0.00')
            )
        )
        .order_by('-total_revenue')[:10]
    )

    categories = (
        Category.objects.filter(is_active=True)
        .annotate(
            total_sales=Coalesce(Sum('products__order_items__quantity'), 0),
            total_revenue=Coalesce(
                Sum(
                    'products__order_items__total',
                    filter=Q(products__order_items__order__status='delivered')
                ),
                Decimal('0.00')
            )
        )
        .order_by('-total_revenue')
    )

    context = {
        'access': access,
        'monthly_sales': monthly_sales,
        'top_vendors': top_vendors,
        'categories': categories,
    }
    return render(request, 'store_admin/analytics.html', context)


# ============= SHOP SETTINGS =============

@login_required
@admin_only
def shop_settings(request):
    """Shop configuration (Admin only)"""
    access  = get_user_access_level(request.user)
    context = {'access': access}
    return render(request, 'store_admin/shop_settings.html', context)


# ============= API ENDPOINTS (AJAX) =============

@login_required
@store_admin_required
def get_order_stats(request):
    """AJAX endpoint for order statistics"""
    if request.user.user_type not in ['admin', 'staff']:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    days       = int(request.GET.get('days', 30))
    end_date   = timezone.now()
    start_date = end_date - timedelta(days=days)

    # Output key 'rev' — avoids clash with field 'total'
    data = list(
        Order.objects.filter(created_at__range=[start_date, end_date])
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(
            count=Count('id'),
            rev=Sum('total', filter=Q(status='delivered'))
        )
        .order_by('date')
    )
    return JsonResponse(data, safe=False)


@login_required
@store_admin_required
def get_product_stats(request):
    """AJAX endpoint for product statistics"""
    products_qs = (
        Product.objects.filter(vendor__user=request.user)
        if request.user.user_type == 'vendor'
        else Product.objects.all()
    )

    return JsonResponse({
        'total':        products_qs.count(),
        'active':       products_qs.filter(is_active=True).count(),
        'low_stock':    products_qs.filter(
            track_inventory=True,
            stock_quantity__lte=F('low_stock_threshold')
        ).count(),
        'out_of_stock': products_qs.filter(
            track_inventory=True, stock_quantity=0
        ).count(),
    })

@login_required
@store_admin_required
def update_order_status(request, order_id):
    """Update order status via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)
    
    try:
        # Parse JSON data
        data = json.loads(request.body)
        new_status = data.get('status')
        tracking_number = data.get('tracking_number', '')
        
        # Get the order
        from payment.models import Order
        order = Order.objects.get(id=order_id)
        
        # Check permissions
        access = get_user_access_level(request.user)
        if not access['can_view_all_orders']:
            # Check if vendor owns this order
            if not order.items.filter(vendor__user=request.user).exists():
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        # Validate status
        valid_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
        if new_status not in valid_statuses:
            return JsonResponse({'success': False, 'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}, status=400)
        
        # Update order
        from django.utils import timezone
        order.status = new_status
        
        if tracking_number:
            order.tracking_number = tracking_number
        
        # Set appropriate timestamps
        if new_status == 'shipped' and not order.shipped_at:
            order.shipped_at = timezone.now()
        elif new_status == 'delivered' and not order.delivered_at:
            order.delivered_at = timezone.now()
        elif new_status == 'cancelled':
            # Optionally restore stock here
            pass
        
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Order #{order.order_number} status updated to {new_status}',
            'status': new_status,
            'status_display': order.get_status_display()
        })
        
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    


@login_required
@store_admin_required
def cancel_order(request, order_id):
    """Cancel an order"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)
    
    try:
        from payment.models import Order, OrderItem
        from eccommence.models import Product, ProductVariant
        
        order = Order.objects.get(id=order_id)
        
        # Check permissions
        access = get_user_access_level(request.user)
        if not access['can_view_all_orders']:
            if not order.items.filter(vendor__user=request.user).exists():
                return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        # Only allow cancellation if not already delivered or cancelled
        if order.status in ['delivered', 'cancelled']:
            return JsonResponse({'success': False, 'error': f'Order already {order.status}'}, status=400)
        
        # Restore stock for each item
        for item in order.items.all():
            if item.product.track_inventory:
                if item.product_variant:
                    item.product_variant.stock_quantity += item.quantity
                    item.product_variant.save()
                else:
                    item.product.stock_quantity += item.quantity
                    item.product.save()
        
        order.status = 'cancelled'
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Order #{order.order_number} cancelled successfully'
        })
        
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found'}, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@store_admin_required
def print_order(request, order_number):
    """Print order invoice"""
    from payment.models import Order
    
    order = Order.objects.get(order_number=order_number)
    
    # Check permissions
    access = get_user_access_level(request.user)
    if not access['can_view_all_orders']:
        if not order.items.filter(vendor__user=request.user).exists():
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You don't have permission to view this order")
    
    context = {
        'order': order,
        'shop': request.tenant,
    }
    
    return render(request, 'store_admin/print_invoice.html', context)


@login_required
@store_admin_required
def bulk_update_orders(request):
    """Bulk update multiple orders"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)
    
    try:
        data = json.loads(request.body)
        order_ids = data.get('order_ids', [])
        new_status = data.get('status')
        
        if not order_ids:
            return JsonResponse({'success': False, 'error': 'No orders selected'}, status=400)
        
        from payment.models import Order
        
        valid_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled']
        if new_status not in valid_statuses:
            return JsonResponse({'success': False, 'error': f'Invalid status'}, status=400)
        
        # Update all orders
        updated_count = Order.objects.filter(id__in=order_ids).update(status=new_status)
        
        return JsonResponse({
            'success': True,
            'message': f'{updated_count} orders updated to {new_status}'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)



@login_required
@store_admin_required
def export_orders(request):
    """Export orders to CSV"""
    import csv
    from django.http import HttpResponse
    from payment.models import Order
    
    order_ids = request.GET.get('ids', '').split(',')
    
    if order_ids and order_ids[0]:
        orders = Order.objects.filter(id__in=order_ids)
    else:
        orders = Order.objects.all()
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Order Number', 'Customer', 'Email', 'Date', 'Total', 'Status', 'Payment Method'])
    
    for order in orders:
        writer.writerow([
            order.order_number,
            order.full_name,
            order.email,
            order.created_at.strftime('%Y-%m-%d %H:%M'),
            order.total,
            order.get_status_display(),
            order.get_payment_method_display()
        ])
    
    return response



@login_required
@store_admin_required
def toggle_product_status(request, product_id):
    """Toggle product active/inactive status"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)
    
    try:
        data = json.loads(request.body)
        is_active = data.get('is_active')
        
        from eccommence.models import Product
        product = Product.objects.get(id=product_id)
        
        # Check permissions
        if request.user.user_type == 'vendor' and product.vendor.user != request.user:
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        product.is_active = is_active
        product.save()
        
        return JsonResponse({'success': True})
        
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Product not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    




@login_required
@store_admin_required
def delete_product(request, product_id):
    """Delete a product"""
    if request.method != 'DELETE':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)
    
    try:
        from eccommence.models import Product
        product = Product.objects.get(id=product_id)
        
        # Check permissions
        if request.user.user_type == 'vendor' and product.vendor.user != request.user:
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        product.delete()
        
        return JsonResponse({'success': True})
        
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Product not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@store_admin_required
def update_product_stock(request, product_id):
    """Update product stock quantity"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)
    
    try:
        data = json.loads(request.body)
        new_stock = data.get('stock_quantity')
        
        if new_stock is None:
            return JsonResponse({'success': False, 'error': 'Stock quantity required'}, status=400)
        
        from eccommence.models import Product
        product = Product.objects.get(id=product_id)
        
        # Check permissions
        if request.user.user_type == 'vendor' and product.vendor.user != request.user:
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        product.stock_quantity = new_stock
        product.save()
        
        return JsonResponse({'success': True, 'message': f'Stock updated to {new_stock}'})
        
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Product not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@store_admin_required
def bulk_activate_products(request):
    """Bulk activate products"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)
    
    try:
        data = json.loads(request.body)
        product_ids = data.get('product_ids', [])
        
        from eccommence.models import Product
        
        if request.user.user_type == 'vendor':
            # Vendors can only activate their own products
            products = Product.objects.filter(id__in=product_ids, vendor__user=request.user)
        else:
            products = Product.objects.filter(id__in=product_ids)
        
        count = products.update(is_active=True)
        
        return JsonResponse({'success': True, 'count': count})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@store_admin_required
def bulk_deactivate_products(request):
    """Bulk deactivate products"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)
    
    try:
        data = json.loads(request.body)
        product_ids = data.get('product_ids', [])
        
        from eccommence.models import Product
        
        if request.user.user_type == 'vendor':
            products = Product.objects.filter(id__in=product_ids, vendor__user=request.user)
        else:
            products = Product.objects.filter(id__in=product_ids)
        
        count = products.update(is_active=False)
        
        return JsonResponse({'success': True, 'count': count})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    

@login_required
@store_admin_required
def bulk_delete_products(request):
    """Bulk delete products"""
    if request.method != 'DELETE':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=400)
    
    try:
        data = json.loads(request.body)
        product_ids = data.get('product_ids', [])
        
        from eccommence.models import Product
        
        if request.user.user_type == 'vendor':
            products = Product.objects.filter(id__in=product_ids, vendor__user=request.user)
        else:
            products = Product.objects.filter(id__in=product_ids)
        
        count = products.count()
        products.delete()
        
        return JsonResponse({'success': True, 'count': count})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    


from eccommence.models import Category


@login_required
@store_admin_required
def add_category(request):
    """Add a new category via AJAX"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)
    
    try:
        data = json.loads(request.body)
        category_name = data.get('name', '').strip()
        parent_id = data.get('parent_id')
        description = data.get('description', '').strip()
        
        if not category_name:
            return JsonResponse({'success': False, 'error': 'Category name is required'}, status=400)
        
        # Check if category already exists
        if Category.objects.filter(name__iexact=category_name).exists():
            return JsonResponse({'success': False, 'error': 'A category with this name already exists'}, status=400)
        
        # Get parent category if provided
        parent_category = None
        if parent_id:
            try:
                parent_category = Category.objects.get(id=parent_id)
            except Category.DoesNotExist:
                pass
        
        # Create the category
        category = Category.objects.create(
            name=category_name,
            parent=parent_category,
            description=description,
            is_active=True
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Category "{category_name}" added successfully!',
            'category_id': category.id,
            'category_name': category.get_full_name() if category.parent else category.name
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    


from django.http import JsonResponse
from django.template.loader import render_to_string
from django.utils.text import slugify

@login_required
@store_admin_required
def preview_product(request):
    """Generate product preview"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)
    
    try:
        # Get product data from POST
        product_name = request.POST.get('name', '')
        product_slug = slugify(product_name)
        
        # Build preview URL
        preview_url = f'/product/{product_slug}/preview/'
        
        # Optionally, you can create a temporary preview in session
        request.session['preview_product'] = {
            'name': product_name,
            'price': request.POST.get('price', 0),
            'description': request.POST.get('description', ''),
            'short_description': request.POST.get('short_description', ''),
            'category_id': request.POST.get('category'),
            'images': [],  # You can store image data here if needed
        }
        
        return JsonResponse({
            'success': True,
            'preview_url': preview_url
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
@login_required
@store_admin_required
def set_primary_image(request, image_id):
    """Set an image as primary for a product"""
    from eccommence.models import ProductImage
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)
    
    try:
        image = ProductImage.objects.get(id=image_id)
        product = image.product
        
        # Check permissions
        access = get_user_access_level(request.user)
        if not access['can_edit_products'] or (
            request.user.user_type == 'vendor' and product.vendor.user != request.user
        ):
            return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
        
        # Set all images to not primary
        product.images.all().update(is_primary=False)
        
        # Set this image as primary
        image.is_primary = True
        image.save()
        
        return JsonResponse({'success': True, 'message': 'Primary image updated', 'image_id': image_id})
        
    except ProductImage.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Image not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required
@store_admin_required
def save_preview(request):
    """Save product preview data to session"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)
    
    try:
        # Save product data to session for preview
        preview_data = {
            'name': request.POST.get('name', ''),
            'price': request.POST.get('price', 0),
            'description': request.POST.get('description', ''),
            'short_description': request.POST.get('short_description', ''),
            'category_id': request.POST.get('category'),
        }
        
        request.session['preview_product'] = preview_data
        
        return JsonResponse({'success': True, 'message': 'Preview data saved'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)