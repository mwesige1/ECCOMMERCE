from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid
from django.conf import settings

class TimeStampedModel(models.Model):
    """Abstract base model with timestamps"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


# ============= SHIPPING ADDRESS =============

class ShippingAddress(TimeStampedModel):
    """Shipping address for orders"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='shipping_addresses'
    )
    
    # Contact Information
    shipping_full_name = models.CharField(max_length=255)
    shipping_email = models.EmailField(max_length=255)
    shipping_phone = models.CharField(max_length=20)
    
    # Address
    shipping_address1 = models.CharField(max_length=255, verbose_name="Address Line 1")
    shipping_address2 = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Address Line 2"
    )
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=100, blank=True)
    shipping_zipcode = models.CharField(max_length=20, blank=True)
    shipping_country = models.CharField(max_length=100)
    
    # Additional
    delivery_instructions = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    
    class Meta:
        verbose_name_plural = 'Shipping Addresses'
        ordering = ['-is_default', '-created_at']
    
    def __str__(self):
        return f'{self.shipping_full_name} - {self.shipping_city}'
    
    @property
    def full_address(self):
        """Return formatted address"""
        parts = [
            self.shipping_address1,
            self.shipping_address2,
            self.shipping_city,
            self.shipping_state,
            self.shipping_zipcode,
            self.shipping_country
        ]
        return ", ".join([part for part in parts if part])


# ============= ORDER MODEL =============

class Order(TimeStampedModel):
    """Customer orders"""
    
    ORDER_STATUS = (
        ('pending', 'Pending Payment'),
        ('payment_failed', 'Payment Failed'),
        ('paid', 'Paid'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    )
    
    # Order Identification
    order_number = models.CharField(max_length=50, unique=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
        blank=True,
        null=True
    )
    # Customer Information
    full_name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255)
    phone = models.CharField(max_length=20)
    
    # Addresses
    shipping_address = models.TextField()
    billing_address = models.TextField(blank=True)
    
    # Order Details
    status = models.CharField(max_length=20, choices=ORDER_STATUS, default='pending')
    
    # Pricing
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    shipping_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)]
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    # Payment Information
    payment_method = models.CharField(max_length=50, blank=True)
    is_paid = models.BooleanField(default=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    # Shipping Information
    tracking_number = models.CharField(max_length=100, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    customer_note = models.TextField(blank=True)
    admin_note = models.TextField(blank=True)
    
    # Coupon
    coupon_code = models.CharField(max_length=50, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f'Order #{self.order_number}'
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate unique order number
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_order_number():
        """Generate unique order number"""
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        random_part = uuid.uuid4().hex[:6].upper()
        return f'ORD-{timestamp}-{random_part}'
    
    @property
    def total_items(self):
        """Total number of items in order"""
        return sum(item.quantity for item in self.items.all())


# ============= ORDER ITEM MODEL =============

class OrderItem(TimeStampedModel):
    """Items in an order"""
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        'eccommence.Product',
        on_delete=models.PROTECT,
        related_name='order_items'
    )
    product_variant = models.ForeignKey(
        'eccommence.ProductVariant',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='order_items'
    )
    vendor = models.ForeignKey(
        'eccommence.Vendor',
        on_delete=models.PROTECT,
        related_name='order_items'
    )
    
    # Product snapshot (in case product is deleted later)
    product_name = models.CharField(max_length=255)
    product_sku = models.CharField(max_length=100)
    product_image = models.CharField(max_length=500, blank=True)
    
    # Pricing
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    # Vendor payout
    vendor_payout = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    commission = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00
    )
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return f'{self.product_name} x {self.quantity}'
    
    def save(self, *args, **kwargs):
        # Calculate total
        self.total = self.price * self.quantity
        
        # Calculate commission and vendor payout
        commission_decimal = self.commission_rate / 100
        self.commission = self.total * Decimal(str(commission_decimal))
        self.vendor_payout = self.total - self.commission
        
        super().save(*args, **kwargs)


# ============= PAYMENT TRANSACTION MODEL =============

class PaymentTransaction(TimeStampedModel):
    """Payment transaction records"""
    
    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    )
    
    PAYMENT_GATEWAY = (
        ('flutterwave', 'Flutterwave'),
        ('paystack', 'Paystack'),
        ('stripe', 'Stripe'),
        ('mpesa', 'M-Pesa'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash_on_delivery', 'Cash on Delivery'),
    )
    
    # Transaction Info
    transaction_id = models.CharField(max_length=200, unique=True, db_index=True)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='payment_transactions'
    )
    
    # Payment Details
    payment_gateway = models.CharField(max_length=50, choices=PAYMENT_GATEWAY)
    gateway_transaction_id = models.CharField(max_length=200, blank=True)
    gateway_reference = models.CharField(max_length=200, blank=True)
    
    # Amount
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    currency = models.CharField(max_length=3, default='UGX')
    
    # Status
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    # Response Data
    gateway_response = models.JSONField(blank=True, null=True)
    error_message = models.TextField(blank=True)
    
    # Timestamps
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Customer Details
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20, blank=True)
    customer_name = models.CharField(max_length=255, blank=True)
    
    # IP Address
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['order']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f'Transaction {self.transaction_id} - {self.status}'
    
    def save(self, *args, **kwargs):
        if not self.transaction_id:
            self.transaction_id = self.generate_transaction_id()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_transaction_id():
        """Generate unique transaction ID"""
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        random_part = uuid.uuid4().hex[:8].upper()
        return f'TXN-{timestamp}-{random_part}'
    
    def mark_as_successful(self):
        """Mark transaction as successful"""
        self.status = 'successful'
        self.completed_at = timezone.now()
        self.save()
        
        # Update order
        self.order.is_paid = True
        self.order.paid_at = timezone.now()
        self.order.status = 'paid'
        self.order.payment_method = self.get_payment_gateway_display()
        self.order.save()
    
    def mark_as_failed(self, error_message=''):
        """Mark transaction as failed"""
        self.status = 'failed'
        self.error_message = error_message
        self.completed_at = timezone.now()
        self.save()
        
        # Update order
        self.order.status = 'payment_failed'
        self.order.save()


# ============= REFUND MODEL =============

class Refund(TimeStampedModel):
    """Refund requests and processing"""
    
    REFUND_STATUS = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
    )
    
    REFUND_REASON = (
        ('damaged', 'Damaged Product'),
        ('wrong_item', 'Wrong Item Received'),
        ('not_as_described', 'Not as Described'),
        ('defective', 'Defective Product'),
        ('late_delivery', 'Late Delivery'),
        ('changed_mind', 'Changed Mind'),
        ('other', 'Other'),
    )
    
    refund_id = models.CharField(max_length=50, unique=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='refunds')
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='refunds'
    )
    
    # Refund Details
    reason = models.CharField(max_length=50, choices=REFUND_REASON)
    description = models.TextField()
    refund_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    # Status
    status = models.CharField(max_length=20, choices=REFUND_STATUS, default='pending')
    
    # Admin Notes
    admin_notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Timestamps
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    # Images/Evidence
    image1 = models.ImageField(upload_to='refunds/', blank=True, null=True)
    image2 = models.ImageField(upload_to='refunds/', blank=True, null=True)
    image3 = models.ImageField(upload_to='refunds/', blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f'Refund {self.refund_id} - {self.order.order_number}'
    
    def save(self, *args, **kwargs):
        if not self.refund_id:
            self.refund_id = f'REF-{uuid.uuid4().hex[:10].upper()}'
        super().save(*args, **kwargs)


# ============= PAYMENT METHOD MODEL =============

class PaymentMethod(TimeStampedModel):
    """Available payment methods"""
    
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    icon = models.ImageField(upload_to='payment_methods/', blank=True, null=True)
    
    # Configuration
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    
    # API Configuration (stored as JSON)
    api_config = models.JSONField(blank=True, null=True)
    
    # Supported Countries/Currencies
    supported_countries = models.JSONField(default=list, blank=True)
    supported_currencies = models.JSONField(default=list, blank=True)
    
    # Fees
    has_transaction_fee = models.BooleanField(default=False)
    transaction_fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )
    transaction_fee_fixed = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    # Display Order
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name