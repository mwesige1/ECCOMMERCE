from django.shortcuts import render,redirect
from cart.cart import Cart
from .forms import ShippingForm
from.models import ShippingAddress
from django.contrib import messages



# Create your views here.
def payment_success(request):
    return render(request,'payment_success.html')
   


def checkout(request):
    
      # display all the products in the cart
    cart = Cart(request)
    #paa through the products to the html from the cart where the funcction is created
    cart_products = cart.show_products

    # pass through the products to the html from the cart,py function
    quantities = cart.show_cart_items

    # get all the total from the cart.p in the function
    totals = cart.cart_total


    # check if the user is logged in and display the shpping information form with his information and if not 
    # authenticated provide an empty shipping form
    if request.user.is_authenticated:
        user_shipping = ShippingAddress.objects.filter(user=request.user).first()
        if not user_shipping:
            user_shipping = ShippingAddress.objects.create(user=request.user)
        shipping_form = ShippingForm(request.POST or None, instance=user_shipping)
        
    else:
        shipping_form = ShippingForm(request.POST or None)




    return render  (request,'checkout_info.html',
                    {'cart_products':cart_products,
                     'quantities':quantities,
                     'totals':totals,
                     'shipping_form':shipping_form
                     
                     })


"""
def checkout_info(request):
    # display all the products in the cart
    cart = Cart(request)
    #paa through the products to the html from the cart where the funcction is created
    cart_products = cart.show_products

    # pass through the products to the html from the cart,py function
    quantities = cart.show_cart_items

    # get all the total from the cart.p in the function
    totals = cart.cart_total

    #check to see if the user is authenticated or logged in
    if request.user.is_authenticated:
            return render  (request,'checkout.html',
                {'cart_products':cart_products,
                    'quantities':quantities,
                    'totals':totals,
                    'shipping_info':request.POST
                    
                    })
    else:
        # Not logged in
        pass




   """