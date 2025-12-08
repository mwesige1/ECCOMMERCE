from django import forms
from .models import ShippingAddress





class ShippingForm(forms.ModelForm):
    shipping_full_name = forms.CharField(
        label="",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Full Name'
        }),
        required=True,
    )

    shipping_email = forms.EmailField(
        label="",
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Email Address'
        }),
        required=True,
    )

    shipping_address1 = forms.CharField(
        label="",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Address Line 1'
        }),
        required=True,
    )

    shipping_address2 = forms.CharField(
        label="",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Address Line 2 (Optional)'
        }),
        required=False,
    )

    shipping_city = forms.CharField(
        label="",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'City'
        }),
        required=True,
    )

    shipping_state = forms.CharField(
        label="",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'State / Province'
        }),
        required=True,
    )

    shipping_country = forms.CharField(
        label="",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Country'
        }),
        required=True,
    )

    
    class Meta:
        model = ShippingAddress
        
        exclude =['user',]


