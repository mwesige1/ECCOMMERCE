from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, SetPasswordForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import User, VendorProfile, Address, Shop
from eccommence.models import Customer


# ============= AUTHENTICATION FORMS =============

class CustomLoginForm(AuthenticationForm):
    """Enhanced login form"""
    username = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Address',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )


class CustomerRegistrationForm(UserCreationForm):
    """Customer registration form"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Address'
        })
    )
    first_name = forms.CharField(
        required=True,
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name'
        })
    )
    last_name = forms.CharField(
        required=True,
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name'
        })
    )
    phone = forms.CharField(
        required=False,
        max_length=17,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone Number (Optional)'
        })
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        })
    )
    
    terms_accepted = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='I accept the Terms and Conditions'
    )
    
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone', 'password1', 'password2']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('This email address is already registered.')
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'customer'
        if commit:
            user.save()
        return user


class VendorRegistrationForm(UserCreationForm):
    """Vendor registration form"""
    # Personal Information
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Address'
        })
    )
    first_name = forms.CharField(
        required=True,
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name'
        })
    )
    last_name = forms.CharField(
        required=True,
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name'
        })
    )
    phone = forms.CharField(
        required=True,
        max_length=17,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone Number'
        })
    )
    
    # Store Information
    store_name = forms.CharField(
        required=True,
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Store Name'
        })
    )
    store_description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Brief description of your store',
            'rows': 4
        })
    )
    
    # Business Information
    business_email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Business Email'
        })
    )
    business_phone = forms.CharField(
        required=True,
        max_length=17,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Business Phone'
        })
    )
    business_address = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Business Address',
            'rows': 3
        })
    )
    
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm Password'
        })
    )
    
    terms_accepted = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='I accept the Vendor Terms and Conditions'
    )
    
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone', 'password1', 'password2']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('This email address is already registered.')
        return email
    
    def clean_store_name(self):
        store_name = self.cleaned_data.get('store_name')
        if VendorProfile.objects.filter(store_name=store_name).exists():
            raise ValidationError('This store name is already taken.')
        return store_name
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'vendor'
        if commit:
            user.save()
            
            # Create vendor profile
            VendorProfile.objects.create(
                user=user,
                store_name=self.cleaned_data['store_name'],
                description=self.cleaned_data.get('store_description', ''),
                business_email=self.cleaned_data['business_email'],
                business_phone=self.cleaned_data['business_phone'],
                business_address=self.cleaned_data['business_address'],
            )
        return user


# ============= PROFILE FORMS =============

class UserUpdateForm(UserChangeForm):
    """Update user basic information"""
    password = None  # Hide password field
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Address'
        })
    )
    first_name = forms.CharField(
        required=True,
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name'
        })
    )
    last_name = forms.CharField(
        required=True,
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name'
        })
    )
    phone = forms.CharField(
        required=False,
        max_length=17,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone Number'
        })
    )
    
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise ValidationError('This email address is already in use.')
        return email


class VendorProfileUpdateForm(forms.ModelForm):
    """Update vendor profile information"""
    
    class Meta:
        model = VendorProfile
        fields = [
            'store_name', 'description', 'logo', 'banner',
            'business_email', 'business_phone', 'business_address',
            'business_registration_number', 'tax_id',
            'bank_name', 'account_number', 'account_holder_name',
            'bank_code', 'swift_code'
        ]
        widgets = {
            'store_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Store Name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Store Description',
                'rows': 4
            }),
            'business_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Business Email'
            }),
            'business_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Business Phone'
            }),
            'business_address': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Business Address',
                'rows': 3
            }),
            'business_registration_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Business Registration Number'
            }),
            'tax_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tax ID / VAT Number'
            }),
            'bank_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Bank Name'
            }),
            'account_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Account Number'
            }),
            'account_holder_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Account Holder Name'
            }),
            'bank_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Bank Code'
            }),
            'swift_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'SWIFT/BIC Code'
            }),
        }


class AddressForm(forms.ModelForm):
    """Address form for shipping/billing"""
    
    class Meta:
        model = Address
        fields = [
            'address_type', 'full_name', 'phone', 'email',
            'address_line1', 'address_line2', 'city', 'state',
            'postal_code', 'country', 'delivery_instructions', 'is_default'
        ]
        widgets = {
            'address_type': forms.Select(attrs={'class': 'form-control'}),
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full Name'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone Number'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email (Optional)'
            }),
            'address_line1': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Address Line 1'
            }),
            'address_line2': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Address Line 2 (Optional)'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City'
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'State/Province'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Postal Code'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Country'
            }),
            'delivery_instructions': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Delivery Instructions (Optional)',
                'rows': 3
            }),
            'is_default': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class ChangePasswordForm(SetPasswordForm):
    """Custom password change form"""
    
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New Password'
        }),
        help_text='Your password must contain at least 8 characters.'
    )
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm New Password'
        })
    )
    
    class Meta:
        model = User
        fields = ['new_password1', 'new_password2']


class CustomerProfilePictureForm(forms.ModelForm):
    """Standalone profile picture upload form for Customer model"""
    
    class Meta:
        model = Customer
        fields = ['profile_picture']
        widgets = {
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }


# ============= SHOP FORMS (Multi-Tenancy) =============

class ShopCreationForm(forms.ModelForm):
    """Shop creation form for vendors"""
    
    domain = forms.CharField(
        max_length=200,
        required=True,
        help_text="Primary domain (e.g., myshop.localhost or myshop.yourdomain.com)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'shop-name.localhost'
        })
    )
    
    class Meta:
        model = Shop
        fields = ['name', 'description', 'logo']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Shop Name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Shop Description',
                'rows': 4
            }),
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if Shop.objects.filter(name=name).exists():
            raise ValidationError('A shop with this name already exists.')
        return name


class ShopAdminForm(forms.ModelForm):
    """Shop admin form for superusers"""
    
    domain = forms.CharField(
        max_length=200,
        required=True,
        help_text="Primary domain (e.g., shop1.localhost)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'shop-name.localhost'
        })
    )
    
    class Meta:
        model = Shop
        fields = ['name', 'owner', 'description', 'logo', 'is_active', 'subscription_plan']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Shop Name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Shop Description',
                'rows': 4
            }),
            'subscription_plan': forms.Select(attrs={
                'class': 'form-control'
            }),
        }


class ShopUpdateForm(forms.ModelForm):
    """Shop update form for vendors"""
    
    class Meta:
        model = Shop
        fields = ['name', 'description', 'logo']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Shop Name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Shop Description',
                'rows': 4
            }),
        }


# ============= PASSWORD RESET FORMS =============

class PasswordResetRequestForm(forms.Form):
    """Password reset request form"""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            raise ValidationError('No account found with this email address.')
        return email


# ============= EMAIL VERIFICATION FORM =============

class ResendVerificationForm(forms.Form):
    """Resend email verification form"""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        try:
            user = User.objects.get(email=email)
            if user.is_verified:
                raise ValidationError('This email is already verified.')
        except User.DoesNotExist:
            raise ValidationError('No account found with this email address.')
        return email


# ============= CONTACT FORM =============

class ContactForm(forms.Form):
    """General contact form"""
    
    name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your Name'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your Email'
        })
    )
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Subject'
        })
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Your Message',
            'rows': 5
        })
    )


# ============= VENDOR VERIFICATION UPLOAD FORM =============

class VendorDocumentUploadForm(forms.ModelForm):
    """Form for uploading vendor verification documents"""
    
    class Meta:
        model = VendorProfile
        fields = ['id_document', 'business_license']
        widgets = {
            'id_document': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,application/pdf'
            }),
            'business_license': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*,application/pdf'
            }),
        }
from eccommence.models import Customer

class CustomerUpdateForm(forms.ModelForm):
    """Update customer profile information"""
    
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'placeholder': 'Date of Birth'
        })
    )
    
    class Meta:
        model = Customer
        fields = [
            'date_of_birth',
            'gender',
            'newsletter_subscription',
            'sms_notifications',
        ]
        widgets = {
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'newsletter_subscription': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'sms_notifications': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }