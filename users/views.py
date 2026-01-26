from django.shortcuts import render,redirect
from django.contrib.auth .forms import AuthenticationForm
from django.contrib.auth import login,logout,authenticate
from django.contrib import messages
from django.contrib.auth.models import User
from.forms import RegisterForm,UpdateUserForm,ChangePasswordForm,UserProfileInfo,ProfilePictureForm
from django.contrib.auth.decorators import login_required
from users.models import Profile
import json
from cart.cart import Cart
from payment.models import ShippingAddress
from payment.forms import ShippingForm
from django.contrib.auth import update_session_auth_hash





def login_view(request):
    # check if the user is already logged in
    if request.user.is_authenticated:
        return redirect('eccommence:home')
    
    # handle submission
    if request.method == 'POST':
        # create an instance of the authentication form with request data
        form = AuthenticationForm(request, data=request.POST)
        # check if form is valid 
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            # verify using django built in authentication
            user = authenticate(username=username, password=password)
            # if authentication was successful
            if user is not None:
                # login user
                login(request, user)

                # work on the cart so that after logging in back the previous cart info comes back
                # Get the current user
                current_user, created = Profile.objects.get_or_create(user=request.user)

                # Get their saved cart from the database
                saved_cart = current_user.cart_info

                # convert the cart_info dictionary {"2":5,"4":1} to python dictionary
                # let's first check if it's not empty
                if saved_cart:
                    # then we convert to python dictionary
                    converted_cart = json.loads(saved_cart)
                    # Access the cart class to add in the items from the db
                    cart = Cart(request)
                    # loop through all the items in the converted_cart and add them to the cart class
                    for key, value in converted_cart.items():
                        cart.db_add(product=key, quantity=value)
                        # db_add is a separate function in the cart class that will 
                        # add these products to the cart after login

                # display message
                messages.success(request, f'Hello {user.username}, Welcome Back')
                # redirect
                return redirect('eccommence:home')
            else:
                # display error if authentication failed
                messages.error(request, 'Invalid username or Password')
        
        else:
            # display an error if form is invalid
            messages.error(request, 'Invalid username or password ')
    else:
        # if the request is get, just display an empty form
        form = AuthenticationForm()
    return render(request, 'grok/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')  


def register(request):
    if request.method == "POST":
        #create a form instance with post data
        form = RegisterForm(request.POST)
        #check validity
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')

            # authenticate the user
            user = authenticate(username=username, password=password)

            # log in automatically
            login(request, user)

            return redirect('user_info')
        else:
            # django will automatically show the error
            messages.error(request,"Please correct the errors below")
    
    else:
        form = RegisterForm()
    return render(request,'register1.html',{'form':form})


def update_user(request):
    if request.user.is_authenticated:
        current_user = User.objects.get(id=request.user.id)
        
        # Get or create the user's profile
        try:
            user_profile = Profile.objects.get(user=current_user)
        except Profile.DoesNotExist:
            user_profile = Profile.objects.create(user=current_user)
        
        # Initialize both forms
        user_form = UpdateUserForm(request.POST or None, instance=current_user)
        profile_form = UserProfileInfo(request.POST or None, instance=user_profile)
        
        if request.method == 'POST':
            if user_form.is_valid() and profile_form.is_valid():
                user_form.save()
                profile_form.save()
                
                login(request, current_user)
                messages.success(request, f'{current_user}, your information has been updated.')
                return redirect('eccommence:home')
            else:
                messages.error(request, 'Please correct the errors below.')
        
        # IMPORTANT: Pass 'form' (not 'user_form') for template compatibility
        return render(request, 'grok/edit_user_info.html', {
            'form': user_form,          # Template expects 'form' for user fields
            'profile_form': profile_form  # Template expects 'profile_form' for address fields
        })
    
    else:
        messages.warning(request, 'You must be logged in to access this page.')
        return redirect('login')


def update_password(request):
    # Check if the user is authenticated
    if request.user.is_authenticated:
        # Get the current logged in user
        current_user = request.user

        # check if the form has been filled
        if request.method == 'POST':
            form = ChangePasswordForm(current_user, request.POST)

            if form.is_valid():
                user = form.save()
                # re-login the user after changing the password
                update_session_auth_hash(request, user)

                messages.success(request, 'Password Changed Successfully')
                return redirect('update_user')
            else:
                # form is not valid, render the same page with errors
                return render(request, 'edit-info.html', {'form': form})


        else:
            form = ChangePasswordForm(current_user)
            return render(request, 'edit-info.html', {'form': form})

    else:
        messages.warning(request, 'User has to be logged in to change password')
        return redirect('eccommence:home')
    



# This decorator automatically redirects users to the login page if they are not logged in
@login_required
def user_info(request):
    # Get the profile that belongs to the currently logged-in user
    # "request.user" gives the User object of whoever is logged in
    profile = Profile.objects.get(user=request.user)
    user = request.user


    # Get the shipping user information for the logged-in user
    # get_or_create returns a tuple (object, created), so we unpack it
    user_shipping, created = ShippingAddress.objects.get_or_create(user=request.user)

    # Check if the form is being submitted (POST request)
    if request.method == 'POST':
        # Bind the submitted form data (request.POST) to the existing profile instance
        form = UserProfileInfo(request.POST, instance=profile)
        shipping_form = ShippingForm(request.POST, instance=user_shipping)

        # Check if the submitted form is valid
        if form.is_valid() or shipping_form.is_valid():
            # Save the updated profile information to the database
            form.save()

            # Save the updated shipping information to the database
            shipping_form.save()

            # Show a success message to the user
            messages.success(request, 'Your information has been updated successfully.')

            # Redirect the user to the homepage (you can change this to any page you prefer)
            return redirect('eccommence:home')

    # If it's not a POST request (GET request), show the form with existing profile data
    else:
        form = UserProfileInfo(instance=profile)
        shipping_form = ShippingForm(instance=user_shipping)

    # Finally, render the template and pass the forms to it
    return render(request, 'grok/user-info.html', {'form': form, 'shipping_form': shipping_form,'user':user})


@login_required
def change_profile_picture(request):
    profile = request.user.profile

    if request.method == 'POST':
        form = ProfilePictureForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('user_info')  # or wherever you want
    else:
        form = ProfilePictureForm(instance=profile)  # for GET requests

    # Always return a response (renders form for GET or invalid POST)
    return render(request, 'grok/edit_user_info.html', {'form': form})


