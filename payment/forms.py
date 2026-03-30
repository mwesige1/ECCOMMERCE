from django import forms
from users.models import Address
from .models import Refund


class ShippingForm(forms.ModelForm):
    """Shipping address form using Address model from users app"""
    
    class Meta:
        model = Address
        fields = [
            'full_name',
            'email',
            'phone',
            'address_line1',
            'address_line2',
            'city',
            'state',
            'postal_code',
            'country',
            'delivery_instructions',
            'is_default',
        ]
        
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Full Name',
                'required': True,
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'Email Address',
                'required': True,
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Phone Number (e.g., 0700123456)',
                'required': True,
            }),
            'address_line1': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Address Line 1',
                'required': True,
            }),
            'address_line2': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Address Line 2 (Optional)',
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'City',
                'required': True,
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'State/Province',
                'required': True,
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Postal Code',
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Country',
                'initial': 'Uganda',
            }),
            'delivery_instructions': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'Delivery instructions (Optional)',
                'rows': 3,
            }),
            'is_default': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }
        
        labels = {
            'full_name': 'Full Name',
            'email': 'Email Address',
            'phone': 'Phone Number',
            'address_line1': 'Address Line 1',
            'address_line2': 'Address Line 2',
            'city': 'City',
            'state': 'State/Province',
            'postal_code': 'Postal Code',
            'country': 'Country',
            'delivery_instructions': 'Delivery Instructions',
            'is_default': 'Set as default address',
        }


class PaymentMethodForm(forms.Form):
    """Payment method selection form"""
    
    PAYMENT_CHOICES = [
        ('mtn_mobile_money', 'MTN Mobile Money'),
        ('airtel_money', 'Airtel Money'),
        ('cash_on_delivery', 'Cash on Delivery'),
    ]
    
    payment_method = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'payment-radio'}),
        required=True,
    )


class RefundRequestForm(forms.ModelForm):
    """Refund request form"""
    
    class Meta:
        model = Refund
        fields = ['reason', 'description', 'image1', 'image2', 'image3']
        
        widgets = {
            'reason': forms.Select(attrs={
                'class': 'form-select',
                'required': True,
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'Please describe the issue in detail...',
                'rows': 5,
                'required': True,
            }),
            'image1': forms.FileInput(attrs={
                'class': 'form-file',
                'accept': 'image/*',
            }),
            'image2': forms.FileInput(attrs={
                'class': 'form-file',
                'accept': 'image/*',
            }),
            'image3': forms.FileInput(attrs={
                'class': 'form-file',
                'accept': 'image/*',
            }),
        }
        
        labels = {
            'reason': 'Refund Reason',
            'description': 'Description',
            'image1': 'Photo 1 (Optional)',
            'image2': 'Photo 2 (Optional)',
            'image3': 'Photo 3 (Optional)',
        }