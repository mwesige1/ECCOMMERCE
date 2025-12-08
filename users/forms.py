from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm,UserChangeForm,SetPasswordForm
from eccommence.models import Profile


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True,widget=forms.EmailInput(attrs={
        'class':'form-control',
        'placeholder':'Enter Email Address'
    }))

    first_name = forms.CharField(required=True,max_length=30,
                                 widget=forms.TextInput(attrs={
                                     'class':'form-control',
                                     'placeholder':'First Name'
                                 }))
    
    last_name = forms.CharField(required=True,max_length=30,
                                widget=forms.TextInput(attrs={
                                    'class':'form-control',
                                     'placeholder':'Last Name'
                                }))
    
    password1 = forms.CharField(required=True,max_length=30,
                                label='Password',
                                strip=False,
                                widget=forms.PasswordInput(attrs={
                                    'class':'form-control',
                                     'placeholder':'Enter Password'
                                }))

    
    password2 = forms.CharField(required=True,max_length=30,
                                label='Confirm Password',
                                widget=forms.PasswordInput(attrs={
                                    'class':'form-control',
                                     'placeholder':'confirm Password'
                                }),
                                strip=False,
                                )
    

    class Meta:
        model= User
        fields =['username','first_name','last_name','email','password1','password2']

        widgets ={
            'username':forms.TextInput(attrs={
                 'class':'form-control',
                 'placeholder':'choose a username'

            }),
        }

    def clean_email(self):
        # ensure the email is unique.
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email address is already registered')
        return email
    



class UpdateUserForm(UserChangeForm):
    # Hide the password related on this page
    password = None
    # these are the only fields to show on the page
    email = forms.EmailField(required=True,widget=forms.EmailInput(attrs={
        'class':'form-control',
        'placeholder':'Enter Email Address'
    }))

    first_name = forms.CharField(required=True,max_length=30,
                                 widget=forms.TextInput(attrs={
                                     'class':'form-control',
                                     'placeholder':'First Name'
                                 }))
    
    last_name = forms.CharField(required=True,max_length=30,
                                widget=forms.TextInput(attrs={
                                    'class':'form-control',
                                     'placeholder':'Last Name'
                                }))
    
    

    

    class Meta:
        model= User
        fields =['username','first_name','last_name','email']

        widgets ={
            'username':forms.TextInput(attrs={
                 'class':'form-control',
                 'placeholder':'choose a username'

            }),
        }

    def clean_email(self):
        # ensure the email is unique.
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email address is already registered')
        return email
    



class ChangePasswordForm(SetPasswordForm):
    class Meta:
        model = User
        fields = ['new_password1','new_password2']



# create a form to show the profile information


class UserProfileInfo(forms.ModelForm):
    phone = forms.CharField(
        label="",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone Number'
        })
    )

    address1 = forms.CharField(
        label="",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Address Line 1'
        })
    )

    address2 = forms.CharField(
        label="",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Address Line 2'
        })
    )

    city = forms.CharField(
        label="",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'City'
        })
    )

    state = forms.CharField(
        label="",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'State'
        })
    )

    zipcode = forms.CharField(
        label="",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Zip Code'
        })
    )

    country = forms.CharField(
        label="",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Country'
        })
    )

    district = forms.CharField(
        label="",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'District'
        })
    )

    class Meta:
        model = Profile
        fields = ['phone', 'address1', 'address2', 'city', 'state', 'zipcode', 'country', 'district']

class ProfilePictureForm(forms.ModelForm):

    class Meta:
        model = Profile
        fields = ['profile_picture']