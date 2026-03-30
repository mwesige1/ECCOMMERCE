from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.db.models import Q, Avg, Count, Prefetch, F, Sum,Max,Min
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, HttpResponseBadRequest,Http404
from django.views.decorators.http import require_POST
from django.utils import timezone
from decimal import Decimal
from .models import (
    Category, Product, ProductImage, ProductVariant, 
    Review, Coupon, Vendor, Customer, Address,Wishlist
)
from payment.models import Order, OrderItem

"""from .forms import (
    CustomerRegistrationForm, AddressForm, ReviewForm,
    CheckoutForm, ContactForm
)"""

# ============= HOME & PRODUCT LISTING =============

def home(request):
    """Enhanced homepage with featured products, deals, categories, and shop features"""
    
    # Base queryset
    products = Product.objects.filter(is_active=True)
    
    # Search
    query = request.GET.get('q')
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query) |
            Q(meta_keywords__icontains=query)
        )
    
    # Category filter from search dropdown
    category_slug = request.GET.get('category')
    selected_category = None
    if category_slug:
        try:
            selected_category = Category.objects.get(slug=category_slug, is_active=True)
            categories_to_filter = [selected_category] + list(selected_category.subcategories.all())
            products = products.filter(category__in=categories_to_filter)
        except Category.DoesNotExist:
            pass
    
    # Price filter
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)
    
    # Rating filter
    min_rating = request.GET.get('min_rating')
    if min_rating:
        products = products.filter(rating__gte=min_rating)
    
    # Availability filter
    in_stock = request.GET.get('in_stock')
    if in_stock:
        products = products.filter(stock_quantity__gt=0)
    
    # On sale filter
    on_sale = request.GET.get('on_sale')
    if on_sale:
        products = products.filter(
            is_on_sale=True,
            sale_start_date__lte=timezone.now(),
            sale_end_date__gte=timezone.now()
        )
    
    # Vendor filter
    vendor_slugs = request.GET.get('vendors')
    selected_vendors = []
    if vendor_slugs:
        selected_vendors = vendor_slugs.split(',')
        products = products.filter(vendor__slug__in=selected_vendors)
    
    # Sorting
    sort_by = request.GET.get('sort', 'featured')
    valid_sorts = {
        'featured': '-is_featured',
        'price_low': 'price',
        'price_high': '-price',
        'rating': '-rating',
        'newest': '-created_at',
        'popular': '-total_sales',
    }
    
    if sort_by in valid_sorts:
        products = products.order_by(valid_sorts[sort_by], '-created_at')
    else:
        # Default: featured first, then newest
        products = products.order_by('-is_featured', '-created_at')
    
    # Apply prefetch for optimization
    products = products.select_related('category', 'vendor').prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
    )
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(products, 24)  # 24 products per page
    
    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)
    
    # Main categories for filters
    all_categories = Category.objects.filter(
        is_active=True,
        parent__isnull=True
    ).prefetch_related('subcategories')
    
    # Vendors for filter
    vendors = Vendor.objects.filter(is_active=True)[:20]
    
    # Price range
    price_range = Product.objects.filter(is_active=True).aggregate(
        min_price=Min('price'),
        max_price=Max('price')
    )
    
    context = {
        'products': products_page,
        'all_categories': all_categories,
        'vendors': vendors,
        'selected_vendors': selected_vendors,
        'selected_category': selected_category,
        'query': query,
        'sort_by': sort_by,
        'total_products': paginator.count,
        'price_range': price_range,
        'min_price': min_price,
        'max_price': max_price,
        'in_stock_only': in_stock,
        'on_sale_only': on_sale,
    }
    
    return render(request, 'eccommence/home.html', context)


def category(request, item):
    """Category view - renamed from category_view to match your URL"""
    category_obj = get_object_or_404(Category, slug=item, is_active=True)
    
    # Get all child categories
    child_categories = category_obj.subcategories.filter(is_active=True)
    categories_to_filter = [category_obj] + list(child_categories)
    
    # Get products
    products = Product.objects.filter(
        category__in=categories_to_filter,
        is_active=True
    ).select_related('category', 'vendor').prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
    )
    
    # Sorting
    sort_by = request.GET.get('sort', '-created_at')
    valid_sorts = {
        'price_asc': 'price',
        'price_desc': '-price',
        'newest': '-created_at',
        'popular': '-total_sales',
        'rating': '-rating',
    }
    
    if sort_by in valid_sorts:
        products = products.order_by(valid_sorts[sort_by])
    
    # Pagination
    paginator = Paginator(products, 24)
    page = request.GET.get('page', 1)
    
    try:
        products_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        products_page = paginator.page(1)
    
    # Get all categories for sidebar
    all_categories = Category.objects.filter(is_active=True, parent__isnull=True)
    
    context = {
        'category': category_obj,
        'child_categories': child_categories,
        'products': products_page,
        'all_categories': all_categories,
        'total_products': paginator.count,
    }
    
    return render(request, 'eccommence/category.html', context)



def product_detail(request, slug):
    """Enhanced product detail page"""
    
    # Get product with related data
    product = get_object_or_404(
        Product.objects.select_related('category', 'vendor').prefetch_related(
            'images',
            'variants',
            Prefetch('reviews', queryset=Review.objects.filter(is_approved=True).select_related('customer__user'))
        ),
        slug=slug,
        is_active=True
    )
    
    # Increment view count
    Product.objects.filter(id=product.id).update(views=F('views') + 1)
    
    # Check if user has this in wishlist
    in_wishlist = False
    if request.user.is_authenticated:
        try:
            in_wishlist = Wishlist.objects.filter(
                customer__user=request.user,
                product=product
            ).exists()
        except Exception:
            in_wishlist = False
    
    # Get related products
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id).select_related('category', 'vendor').prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
    )[:8]
    
    # Get reviews
    reviews = product.reviews.filter(is_approved=True).select_related('customer__user')[:10]
    
    # Check if user can review
    can_review = False
    if request.user.is_authenticated:
        try:
            has_purchased = OrderItem.objects.filter(
                order__customer__user=request.user,
                product=product,
                order__status='delivered'
            ).exists()
            
            already_reviewed = Review.objects.filter(
                customer__user=request.user,
                product=product
            ).exists()
            
            can_review = has_purchased and not already_reviewed
        except Exception:
            can_review = False
    
    context = {
        'product': product,
        'related_products': related_products,
        'reviews': reviews,
        'in_wishlist': in_wishlist,
        'can_review': can_review,
    }
    
    return render(request, 'eccommence/product_detail.html', context)



def category_view(request, slug):
    """Category page with products and filters"""
    
    category = get_object_or_404(Category, slug=slug, is_active=True)
    
    # Get all child categories
    child_categories = category.subcategories.filter(is_active=True)
    categories_to_filter = [category] + list(child_categories)
    
    # Get products
    products = Product.objects.filter(
        category__in=categories_to_filter,
        is_active=True
    ).select_related('category', 'vendor').prefetch_related(
        Prefetch('images', queryset=ProductImage.objects.filter(is_primary=True))
    )
    
    # Price filter
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)
    
    # Rating filter
    min_rating = request.GET.get('min_rating')
    if min_rating:
        products = products.filter(rating__gte=min_rating)
    
    # Availability filters
    if request.GET.get('in_stock'):
        products = products.filter(stock_quantity__gt=0)
    
    if request.GET.get('on_sale'):
        products = products.filter(is_on_sale=True)
    
    # Sorting
    sort_by = request.GET.get('sort', '-created_at')
    valid_sorts = {
        'price_asc': 'price',
        'price_desc': '-price',
        '-created_at': '-created_at',
        'newest': '-created_at',
        'popular': '-total_sales',
        'rating': '-rating',
    }
    
    if sort_by in valid_sorts:
        products = products.order_by(valid_sorts[sort_by])
    else:
        products = products.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(products, 24)
    page = request.GET.get('page', 1)
    
    try:
        products_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        products_page = paginator.page(1)
    
    context = {
        'category': category,
        'child_categories': child_categories,
        'products': products_page,
        'total_products': paginator.count,
    }
    
    return render(request, 'eccommence/category.html', context)

def category_list(request):
    """All categories page"""
    
    categories = Category.objects.filter(
        is_active=True,
        parent__isnull=True
    ).prefetch_related('subcategories').annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    )
    
    context = {
        'categories': categories,
    }
    
    return render(request, 'eccommence/category_list.html', context)



# ============= CHECKOUT VIEWS =============

@login_required
def checkout(request):
    """Checkout page"""
    
    customer = request.user.customer_profile
    cart = Cart.objects.filter(customer=customer).first()
    
    if not cart or cart.total_items == 0:
        messages.warning(request, 'Your cart is empty')
        return redirect('cart')
    
    cart_items = cart.items.select_related('product', 'variant')
    
    # Get or create addresses
    shipping_addresses = Address.objects.filter(
        customer=customer,
        address_type='shipping'
    ).order_by('-is_default')
    
    billing_addresses = Address.objects.filter(
        customer=customer,
        address_type='billing'
    ).order_by('-is_default')
    
    # Calculate totals
    subtotal = cart.subtotal
    shipping = Decimal('5000.00')
    tax = subtotal * Decimal('0.18')
    
    # Apply coupon if exists
    discount = Decimal('0.00')
    coupon_code = request.session.get('coupon_code')
    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code)
            if coupon.is_valid():
                if coupon.discount_type == 'percentage':
                    discount = subtotal * (coupon.discount_value / 100)
                    if coupon.max_discount_amount:
                        discount = min(discount, coupon.max_discount_amount)
                else:
                    discount = coupon.discount_value
        except Coupon.DoesNotExist:
            pass
    
    total = subtotal + shipping + tax - discount
    
    if request.method == 'POST':
        # Process checkout
        shipping_address_id = request.POST.get('shipping_address')
        billing_address_id = request.POST.get('billing_address')
        payment_method = request.POST.get('payment_method')
        
        try:
            shipping_address = Address.objects.get(id=shipping_address_id, customer=customer)
            billing_address = Address.objects.get(id=billing_address_id, customer=customer)
        except Address.DoesNotExist:
            messages.error(request, 'Invalid address selected')
            return redirect('checkout')
        
        # Create order
        order = Order.objects.create(
            customer=customer,
            shipping_address=shipping_address,
            billing_address=billing_address,
            subtotal=subtotal,
            shipping_cost=shipping,
            tax=tax,
            discount=discount,
            total=total,
            payment_method=payment_method,
            customer_note=request.POST.get('customer_note', '')
        )
        
        # Create order items
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                vendor=cart_item.product.vendor,
                product=cart_item.product,
                variant=cart_item.variant,
                product_name=cart_item.product.name,
                sku=cart_item.variant.sku if cart_item.variant else cart_item.product.sku,
                quantity=cart_item.quantity,
                price=cart_item.price
            )
            
            # Update stock
            if cart_item.product.track_inventory:
                if cart_item.variant:
                    cart_item.variant.stock_quantity -= cart_item.quantity
                    cart_item.variant.save()
                else:
                    cart_item.product.stock_quantity -= cart_item.quantity
                    cart_item.product.save()
        
        # Clear cart
        cart.items.all().delete()
        
        # Clear coupon from session
        if 'coupon_code' in request.session:
            del request.session['coupon_code']
        
        messages.success(request, f'Order {order.order_number} placed successfully!')
        return redirect('order_confirmation', order_number=order.order_number)
    
    context = {
        'cart_items': cart_items,
        'shipping_addresses': shipping_addresses,
        'billing_addresses': billing_addresses,
        'subtotal': subtotal,
        'shipping': shipping,
        'tax': tax,
        'discount': discount,
        'total': total,
        'coupon_code': coupon_code,
    }
    
    return render(request, 'eccommence/checkout.html', context)


@login_required
def order_confirmation(request, order_number):
    """Order confirmation page"""
    
    order = get_object_or_404(
        Order.objects.select_related('customer', 'shipping_address', 'billing_address').prefetch_related(
            'items__product',
            'items__vendor'
        ),
        order_number=order_number,
        customer__user=request.user
    )
    
    context = {
        'order': order,
    }
    
    return render(request, 'eccommence/order_confirmation.html', context)





# ============= REVIEW VIEWS =============

@login_required
@require_POST
def submit_review(request, product_slug):
    """Submit product review"""
    
    product = get_object_or_404(Product, slug=product_slug)
    customer = request.user.customer_profile
    
    # Check if user has purchased this product
    has_purchased = OrderItem.objects.filter(
        order__customer=customer,
        product=product,
        order__status='delivered'
    ).exists()
    
    if not has_purchased:
        return JsonResponse({
            'success': False,
            'message': 'You can only review products you have purchased'
        }, status=403)
    
    # Check if already reviewed
    if Review.objects.filter(customer=customer, product=product).exists():
        return JsonResponse({
            'success': False,
            'message': 'You have already reviewed this product'
        }, status=400)
    
    rating = int(request.POST.get('rating'))
    title = request.POST.get('title')
    comment = request.POST.get('comment')
    
    review = Review.objects.create(
        product=product,
        customer=customer,
        rating=rating,
        title=title,
        comment=comment,
        is_verified_purchase=True
    )
    
    # Update product rating
    avg_rating = Review.objects.filter(product=product, is_approved=True).aggregate(
        avg=Avg('rating')
    )['avg'] or 0
    
    product.rating = round(avg_rating, 2)
    product.total_reviews = Review.objects.filter(product=product, is_approved=True).count()
    product.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Review submitted successfully! It will be published after moderation.'
    })


def product_preview(request, slug):
    """Preview product before publishing"""
    # Check if there's preview data in session
    preview_data = request.session.get('preview_product', None)
    
    if preview_data:
        # Create a temporary product object for preview
        from django.forms.models import model_to_dict
        
        class TempProduct:
            pass
        
        product = TempProduct()
        product.name = preview_data.get('name', '')
        product.price = preview_data.get('price', 0)
        product.description = preview_data.get('description', '')
        product.short_description = preview_data.get('short_description', '')
        product.slug = slug
        product.is_active = True
        product.is_on_sale = False
        product.rating = 0
        product.total_reviews = 0
        
        # Try to get category
        category_id = preview_data.get('category_id')
        if category_id:
            try:
                product.category = Category.objects.get(id=category_id)
            except Category.DoesNotExist:
                product.category = None
        else:
            product.category = None
        
        # For images, we can't show actual uploaded images in preview without saving
        # So we'll show placeholder or no images
        product.images = []
        
        context = {
            'product': product,
            'is_preview': True,
        }
    else:
        # If no preview data, try to get actual product
        try:
            product = Product.objects.get(slug=slug, is_active=True)
            context = {
                'product': product,
                'is_preview': False,
            }
        except Product.DoesNotExist:
            raise Http404("Product not found")
    
    return render(request, 'eccommence/product_detail.html', context)


@property
def primary_image_url(self):
    """Return the URL of the primary image or first image if none is primary"""
    primary = self.images.filter(is_primary=True).first()
    if primary:
        return primary.image.url
    first = self.images.first()
    if first:
        return first.image.url
    return None