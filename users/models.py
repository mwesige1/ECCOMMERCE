from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager
)
from django.utils import timezone
from django.core.validators import RegexValidator
from django.urls import reverse
from django.utils.text import slugify
import uuid


# ============= CUSTOM USER MANAGER =============

class UserManager(BaseUserManager):
    """
    Custom user manager where email is the unique identifier
    instead of username.
    """
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with email and password"""
        if not email:
            raise ValueError("Users must have an email address")
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with email and password"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('user_type', 'admin')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True")
        
        return self.create_user(email, password, **extra_fields)


# ============= CUSTOM USER MODEL =============

class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model with email as the primary identifier
    """
    USER_TYPE_CHOICES = (
    ('customer', 'Customer'),
    ('vendor', 'Vendor'),
    ('staff', 'Staff'),
    ('admin', 'Admin'),
)
    
    # Basic Information
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone = models.CharField(validators=[phone_regex], max_length=17, blank=True)
    
    # User Type
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default='customer'
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    
    # Verification
    verification_token = models.CharField(max_length=100, blank=True)
    verification_token_created = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['user_type']),
        ]
    
    def __str__(self):
        return self.email
    
    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between"""
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_short_name(self):
        """Return the short name for the user"""
        return self.first_name
    
@property
def is_customer(self):
    return self.user_type == 'customer'

@property
def is_vendor(self):
    return self.user_type == 'vendor'

@property
def is_staff_member(self):
    return self.user_type == 'staff'

@property
def is_admin(self):
    return self.user_type == 'admin'

@property
def can_access_manage(self):
    """Check if user can access the shop management dashboard"""
    return self.user_type in ['admin', 'staff', 'vendor']



# ============= VENDOR PROFILE =============

class VendorProfile(models.Model):
    """
    Extended profile information for vendors/sellers
    """
    VERIFICATION_STATUS = (
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='extended_vendor_profile')    
    # Store Information
    store_name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    
    logo = models.ImageField(
        upload_to='vendor_logos/',
        blank=True,
        null=True
    )
    banner = models.ImageField(
        upload_to='vendor_banners/',
        blank=True,
        null=True
    )
    
    # Business Information
    business_email = models.EmailField()
    business_phone = models.CharField(max_length=17)
    business_address = models.TextField()
    
    # Business Registration
    business_registration_number = models.CharField(max_length=100, blank=True)
    tax_id = models.CharField(max_length=50, blank=True, verbose_name="Tax ID/VAT Number")
    
    # Bank Information (for payouts)
    bank_name = models.CharField(max_length=200, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    account_holder_name = models.CharField(max_length=200, blank=True)
    bank_code = models.CharField(max_length=20, blank=True)
    swift_code = models.CharField(max_length=20, blank=True)
    
    # Status
    is_active = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS,
        default='pending'
    )
    verification_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Rating & Stats
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00
    )
    total_reviews = models.IntegerField(default=0)
    total_sales = models.IntegerField(default=0)
    
    # Commission
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.00,
        help_text="Platform commission percentage"
    )
    
    # Documents
    id_document = models.FileField(
        upload_to='vendor_documents/',
        blank=True,
        null=True,
        help_text="Government-issued ID"
    )
    business_license = models.FileField(
        upload_to='vendor_documents/',
        blank=True,
        null=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Vendor Profile'
        verbose_name_plural = 'Vendor Profiles'
    
    def __str__(self):
        return self.store_name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.store_name)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('users:vendor_store', kwargs={'slug': self.slug})
    
    @property
    def is_verified(self):
        return self.verification_status == 'verified'
    
    @property
    def can_sell(self):
        return self.is_active and self.is_verified


# ============= MULTI-TENANCY SHOP MODEL =============

class Shop(models.Model):
    """
    Shop model for multi-tenancy support
    Each shop is a separate tenant with its own database schema
    """
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shops',
        limit_choices_to={'user_type': 'vendor'}
    )
    
    # Shop Settings
    description = models.TextField(blank=True)
    logo = models.ImageField(upload_to='shop_logos/', blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Subscription (if you want paid plans)
    subscription_plan = models.CharField(
        max_length=50,
        choices=[
            ('free', 'Free'),
            ('basic', 'Basic'),
            ('premium', 'Premium'),
            ('enterprise', 'Enterprise'),
        ],
        default='free'
    )
    subscription_start = models.DateField(null=True, blank=True)
    subscription_end = models.DateField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Shop'
        verbose_name_plural = 'Shops'
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# ============= ADDRESS MODEL =============

class Address(models.Model):
    """
    User addresses for shipping and billing
    """
    ADDRESS_TYPE_CHOICES = (
        ('shipping', 'Shipping'),
        ('billing', 'Billing'),
        ('both', 'Both'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPE_CHOICES, default='both')
    
    # Contact Information
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=17)
    email = models.EmailField(blank=True)
    
    # Address Details
    address_line1 = models.CharField(max_length=255, verbose_name="Address Line 1")
    address_line2 = models.CharField(max_length=255, blank=True, verbose_name="Address Line 2")
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    
    # Additional Info
    delivery_instructions = models.TextField(blank=True)
    
    # Default Address
    is_default = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
        verbose_name = 'Address'
        verbose_name_plural = 'Addresses'
    
    def __str__(self):
        return f"{self.full_name} - {self.address_line1}, {self.city}"
    
    def save(self, *args, **kwargs):
        # If this is set as default, remove default from other addresses
        if self.is_default:
            Address.objects.filter(
                user=self.user,
                address_type=self.address_type,
                is_default=True
            ).update(is_default=False)
        super().save(*args, **kwargs)
    
    @property
    def full_address(self):
        """Return formatted address"""
        parts = [
            self.address_line1,
            self.address_line2,
            self.city,
            self.state,
            self.postal_code,
            self.country
        ]
        return ", ".join([part for part in parts if part])


