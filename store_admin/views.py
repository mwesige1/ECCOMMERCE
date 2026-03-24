from django.shortcuts import render, get_object_or_404
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


# ============= PRODUCTS ADD / EDIT =============

@login_required
@store_admin_required
def product_add(request):
    """Add new product"""
    access = get_user_access_level(request.user)
    # Placeholder — wire up your product form here
    context = {'access': access}
    return render(request, 'store_admin/product_form.html', context)


@login_required
@store_admin_required
def product_edit(request, pk):
    """Edit existing product"""
    access  = get_user_access_level(request.user)
    product = get_object_or_404(Product, pk=pk)

    # Vendors can only edit their own products
    if not access['can_edit_products'] or (
        request.user.user_type == 'vendor'
        and product.vendor.user != request.user
    ):
        from django.http import HttpResponseForbidden
        return HttpResponseForbidden("You don't have permission to edit this product.")

    context = {'access': access, 'product': product}
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

    context = {
        'access': access,
        'refunds': refunds_qs,
        'status_filter': status or 'all',
        'search': search,
    }
    return render(request, 'store_admin/refunds.html', context)


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
            .select_related('profile')
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
    date_to   = request.GET.get('date_to')
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

    context = {
        'access': access,
        'orders': orders_list,
        'status_filter': status or 'all',
        'date_from': date_from,
        'date_to': date_to,
        'search': search,
        'order_statuses': ['pending', 'processing', 'shipped', 'delivered', 'cancelled'],
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
    categories    = Category.objects.filter(is_active=True)

    context = {
        'access': access,
        'products': products_list,
        'categories': categories,
        'status_filter': status or 'all',
        'category_filter': category_id,
        'search': search,
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
        .select_related('profile')
        .annotate(
            total_orders=Count('orders', distinct=True),
            total_spent=Coalesce(
                Sum('orders__total', filter=Q(orders__status='delivered')),
                Decimal('0.00')
            )
        )
    )

    search = request.GET.get('search')
    if search:
        customers_list = customers_list.filter(
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(phone__icontains=search)
        )

    date_from = request.GET.get('date_from')
    date_to   = request.GET.get('date_to')
    if date_from:
        customers_list = customers_list.filter(date_joined__date__gte=date_from)
    if date_to:
        customers_list = customers_list.filter(date_joined__date__lte=date_to)

    customers_list = customers_list.order_by('-date_joined')

    context = {
        'access': access,
        'customers': customers_list,
        'search': search,
        'date_from': date_from,
        'date_to': date_to,
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