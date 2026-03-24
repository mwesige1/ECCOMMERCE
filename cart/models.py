from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
from eccommence.models import Product, ProductVariant, Customer

class TimeStampedModel(models.Model):
    """Abstract base model with timestamps"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class Cart(TimeStampedModel):
    """Shopping cart - supports both authenticated and guest users"""
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.CASCADE, 
        related_name='carts', 
        null=True, 
        blank=True
    )
    session_key = models.CharField(
        max_length=100, 
        blank=True,
        help_text="For anonymous users"
    )
    
    # Coupon tracking
    coupon_code = models.CharField(max_length=50, blank=True)
    discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0
    )
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['customer']),
            models.Index(fields=['session_key']),
        ]
        
    def __str__(self):
        if self.customer:
            return f"Cart - {self.customer.full_name}"
        return f"Cart - Guest ({self.session_key[:10]}...)"
    
    @property
    def total_items(self):
        """Total number of items in cart"""
        return sum(item.quantity for item in self.items.all())
    
    @property
    def subtotal(self):
        return sum((item.total_price for item in self.items.all()), Decimal('0.00'))
    
    @property
    def total(self):
        """Cart total after discounts"""
        return max(self.subtotal - self.discount_amount, Decimal('0.00'))
    
    def clear(self):
        """Remove all items from cart"""
        self.items.all().delete()
        self.coupon_code = ''
        self.discount_amount = Decimal('0.00')
        self.save()


class CartItem(TimeStampedModel):
    """Items in shopping cart"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(
        ProductVariant, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Price at time of adding to cart"
    )
    
    class Meta:
        unique_together = ['cart', 'product', 'variant']
        ordering = ['created_at']
        
    def __str__(self):
        variant_str = f" - {self.variant.value}" if self.variant else ""
        return f"{self.product.name}{variant_str} x {self.quantity}"
    
    @property
    def total_price(self):
        """Total price for this cart item"""
        return self.price * self.quantity
    
    @property
    def available_stock(self):
        """Check available stock"""
        if self.variant:
            return self.variant.stock_quantity
        return self.product.stock_quantity if self.product.track_inventory else 999999
    
    def save(self, *args, **kwargs):
        # Set price from product if not already set
        if not self.price:
            self.price = self.product.current_price
            if self.variant:
                self.price += self.variant.price_adjustment
        super().save(*args, **kwargs)


class SavedForLater(TimeStampedModel):
    """Items saved for later (moved from cart)"""
    customer = models.ForeignKey(
        Customer, 
        on_delete=models.CASCADE, 
        related_name='saved_items'
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(
        ProductVariant, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    
    class Meta:
        unique_together = ['customer', 'product', 'variant']
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.customer.full_name} - {self.product.name}"