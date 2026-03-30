from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils.timezone import now
from django.core.validators import MinValueValidator, MaxValueValidator
from ecom.storage import TenantMediaStorage
import uuid
from decimal import Decimal
from django.conf import settings

# ============= BASE MODELS =============

class TimeStampedModel(models.Model):
    """Abstract base model with timestamps"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


# ============= USER & VENDOR MODELS =============

class Customer(models.Model):
    """Extended user profile for customers"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='customer_profile')
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(
        upload_to='uploads/customers/',
        storage=TenantMediaStorage(),
        null=True,
        blank=True
    )
    is_verified = models.BooleanField(default=False)
    verification_token = models.CharField(max_length=100, blank=True)
    
    # Preferences
    newsletter_subscription = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    gender = models.CharField(
        max_length=20,
        choices=[
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other'),
            ('prefer_not_to_say', 'Prefer not to say')
        ],
        blank=True
    )
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.user.email}"
    
    @property
    def full_name(self):
        return self.user.get_full_name()



class Vendor(TimeStampedModel):
    """Vendor/Store model for multi-vendor marketplace"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vendor_profile')
    store_name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    logo = models.ImageField(
        upload_to='uploads/vendors/logos/',
        storage=TenantMediaStorage(),
        null=True,
        blank=True
    )
    banner = models.ImageField(
        upload_to='uploads/vendors/banners/',
        storage=TenantMediaStorage(),
        null=True,
        blank=True
    )
    
    # Business Information
    business_email = models.EmailField()
    business_phone = models.CharField(max_length=20)
    business_address = models.TextField()
    tax_id = models.CharField(max_length=50, blank=True)
    
    # Status
    is_active = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    verification_date = models.DateTimeField(null=True, blank=True)
    
    # Rating
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    total_reviews = models.IntegerField(default=0)
    
    # Commission
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        help_text="Platform commission percentage"
    )
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return self.store_name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.store_name)
        super().save(*args, **kwargs)


# ============= CATEGORY & PRODUCT MODELS =============

class Category(TimeStampedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcategories'
    )
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to='uploads/categories/',
        storage=TenantMediaStorage(),
        null=True,
        blank=True
    )
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    
    # SEO
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['order', 'name']
        
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(TimeStampedModel):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, blank=True)
    sku = models.CharField(max_length=100, unique=True, blank=True)
    
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    description = models.TextField()
    short_description = models.CharField(max_length=300, blank=True)
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    compare_at_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Original price before discount"
    )
    cost_per_item = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Cost to vendor"
    )
    
    # Sale
    is_on_sale = models.BooleanField(default=False)
    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    sale_start_date = models.DateTimeField(null=True, blank=True)
    sale_end_date = models.DateTimeField(null=True, blank=True)
    
    # Inventory
    track_inventory = models.BooleanField(default=True)
    stock_quantity = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(default=10)
    allow_backorder = models.BooleanField(default=False)
    
    # Physical properties
    weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Weight in kg")
    length = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Length in cm")
    width = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Width in cm")
    height = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Height in cm")
    
    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    # SEO
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.CharField(max_length=300, blank=True)
    
    # Stats
    views = models.IntegerField(default=0)
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    total_reviews = models.IntegerField(default=0)
    total_sales = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['sku']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['is_active', 'is_featured']),
        ]
        
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.sku:
            self.sku = f"PRD-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)
    
    @property
    def current_price(self):
        """Return the current selling price"""
        if self.is_on_sale and self.sale_price:
            return self.sale_price
        return self.price
    
    @property
    def discount_percentage(self):
        """Calculate discount percentage"""
        if self.compare_at_price and self.compare_at_price > self.current_price:
            return round(((self.compare_at_price - self.current_price) / self.compare_at_price) * 100)
        return 0
    
    @property
    def is_in_stock(self):
        """Check if product is in stock"""
        if not self.track_inventory:
            return True
        return self.stock_quantity > 0 or self.allow_backorder
    
    @property
    def is_low_stock(self):
        """Check if stock is low"""
        if not self.track_inventory:
            return False
        return 0 < self.stock_quantity <= self.low_stock_threshold
    @property
    def primary_image_url(self):
        """Return the URL of the primary image or first image if none is primary"""
        try:
            primary = self.images.filter(is_primary=True).first()
            if primary:
                return primary.image.url
            first = self.images.first()
            if first:
                return first.image.url
        except Exception:
            pass
        return None


class ProductImage(TimeStampedModel):
    """Multiple images per product"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='uploads/products/', storage=TenantMediaStorage())
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order', '-is_primary']
        
    def __str__(self):
        return f"{self.product.name} - Image {self.order}"
    
    def save(self, *args, **kwargs):
        # If this is set as primary, remove primary from other images
        if self.is_primary:
            ProductImage.objects.filter(product=self.product, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)


class ProductVariant(TimeStampedModel):
    """Product variants (size, color, etc.)"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=100, help_text="e.g., Size, Color")
    value = models.CharField(max_length=100, help_text="e.g., XL, Red")
    sku = models.CharField(max_length=100, unique=True, blank=True)
    
    price_adjustment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Price difference from base product"
    )
    stock_quantity = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['product', 'name', 'value']
        ordering = ['name', 'value']
        
    def __str__(self):
        return f"{self.product.name} - {self.name}: {self.value}"
    
    def save(self, *args, **kwargs):
        if not self.sku:
            self.sku = f"{self.product.sku}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)


# ============= ADDRESS MODEL =============

class Address(TimeStampedModel):
    """Customer addresses"""
    ADDRESS_TYPES = (
        ('billing', 'Billing'),
        ('shipping', 'Shipping'),
    )
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='addresses')
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPES)
    
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    
    is_default = models.BooleanField(default=False)
    
    class Meta:
        verbose_name_plural = 'Addresses'
        ordering = ['-is_default', '-created_at']
        
    def __str__(self):
        return f"{self.full_name} - {self.address_line1}, {self.city}"
    
    def save(self, *args, **kwargs):
        # If this is set as default, remove default from other addresses of same type
        if self.is_default:
            Address.objects.filter(
                customer=self.customer,
                address_type=self.address_type,
                is_default=True
            ).update(is_default=False)
        super().save(*args, **kwargs)





# ============= ORDER MODELS =============


class Review(TimeStampedModel):
    """Product reviews"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='reviews')
    order_item = models.ForeignKey('payment.OrderItem', on_delete=models.SET_NULL, null=True, blank=True)
    
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=200)
    comment = models.TextField()
    
    is_verified_purchase = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    
    # Vendor response
    vendor_response = models.TextField(blank=True)
    vendor_responded_at = models.DateTimeField(null=True, blank=True)
    
    # Helpful votes
    helpful_count = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['product', 'customer', 'order_item']
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.product.name} - {self.rating} stars by {self.customer.full_name}"



class Coupon(TimeStampedModel):
    """Discount coupons"""
    DISCOUNT_TYPE = (
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    )
    
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPE)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum discount for percentage coupons"
    )
    
    usage_limit = models.IntegerField(null=True, blank=True, help_text="Total usage limit")
    usage_limit_per_customer = models.IntegerField(default=1)
    times_used = models.IntegerField(default=0)
    
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return self.code
    
    def is_valid(self):
        """Check if coupon is currently valid"""
        if not self.is_active:
            return False
        current_time = now()
        if current_time < self.valid_from or current_time > self.valid_to:
            return False
        if self.usage_limit and self.times_used >= self.usage_limit:
            return False
        return True
    


class Wishlist(TimeStampedModel):
    """User's wishlist items"""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')
    
    class Meta:
        unique_together = ('customer', 'product')
        ordering = ['-created_at']
        verbose_name = 'Wishlist Item'
        verbose_name_plural = 'Wishlist Items'
    
    def __str__(self):
        return f"{self.customer.user.username} - {self.product.name}"