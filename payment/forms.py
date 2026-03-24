from django import forms
from .models import ShippingAddress, Refund


class ShippingForm(forms.ModelForm):
    """Shipping address form"""
    
    class Meta:
        model = ShippingAddress
        fields = [
            'shipping_full_name',
            'shipping_email', 
            'shipping_phone',
            'shipping_address1',
            'shipping_address2',
            'shipping_city',
            'shipping_country',
            'delivery_instructions',
        ]
        
        widgets = {
            'shipping_full_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Full Name',
                'required': True,
            }),
            'shipping_email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'Email Address',
                'required': True,
            }),
            'shipping_phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Phone Number (e.g., 0700123456)',
                'required': True,
            }),
            'shipping_address1': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Address Line 1',
                'required': True,
            }),
            'shipping_address2': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Address Line 2 (Optional)',
            }),
            'shipping_city': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'City',
                'required': True,
            }),
            'shipping_country': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Country',
                'value': 'Uganda',
            }),
            'delivery_instructions': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'Delivery instructions (Optional)',
                'rows': 3,
            }),
        }
        
        labels = {
            'shipping_full_name': 'Full Name',
            'shipping_email': 'Email Address',
            'shipping_phone': 'Phone Number',
            'shipping_address1': 'Address Line 1',
            'shipping_address2': 'Address Line 2',
            'shipping_city': 'City',
            'shipping_country': 'Country',
            'delivery_instructions': 'Delivery Instructions',
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