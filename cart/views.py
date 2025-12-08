from django.shortcuts import render,get_object_or_404
from.cart import Cart
from eccommence.models import Product
from django.http import JsonResponse
from django.contrib import messages





# Create your views here.
def cart_summary(request):
    # display all the products in the cart
    cart = Cart(request)

    #paa through the products to the html from the cart where the funcction is created
    cart_products = cart.show_products

    # pass through the products to the html from the cart,py function
    quantities = cart.show_cart_items

    # get all the total from the cart.p in the function
    totals = cart.cart_total

    return render  (request,'cart.html',{'cart_products':cart_products,'quantities':quantities,'totals':totals})

def cart_add(request):
    # Get the cart
    cart = Cart(request)
    #test for post
    if request.POST.get('action') == 'post':
        #get the stuff posted 
        product_id = int(request.POST.get('product_id'))
        # get the selected quantity in the browser
        product_qty= int(request.POST.get('product_qty'))


        # look for that product in the database
        product = get_object_or_404(Product,id =product_id)
        product_name =product.name
        

        #save session 
        cart.add(product=product,quantity = product_qty)

        # get all the quantities in the cart
        cart_quantity = cart.__len__()


        messages.success(request,(f'{product_name } Added to Cart.....'))
        # return response
        #response = JsonResponse({'product Name: ': product.name})!! this was just see if the product name is printed iin the console
        
        response = JsonResponse({'qty':cart_quantity})
        return response




def cart_update(request):
    # Get the cart.py class 
    cart = Cart(request)

    # test for post
    if request.POST.get('action') == 'post':
        # get the stuff posted 
        product_id = request.POST.get('product_id')
        product_qty = request.POST.get('product_qty')

        # ✅ check if product_qty is missing or empty
        if not product_qty:
            return JsonResponse({'error': 'No quantity provided'}, status=400)

        try:
            product_id = int(product_id)
            product_qty = int(product_qty)
        except ValueError:
            return JsonResponse({'error': 'Invalid data format'}, status=400)

        # ✅ use the cart.update from the Cart class to pass id and quantity
        cart.update(product=product_id, quantity=product_qty)

        messages.success(request,('Item has been updated to cart...'))
        response = JsonResponse({'qty': product_qty})
        return response




def cart_delete(request):
    # Get the cart.py class 
    cart = Cart(request)

    # test for post
    if request.POST.get('action') == 'post':
        # get the stuff posted 
        product_id = request.POST.get('product_id')
    # ✅ use the cart.delete from the Cart class to pass id for the slected product to be deleted
        cart.delete(product=product_id)
        messages.success(request,('Item deleted from cart.....'))
        response = JsonResponse({'product': product_id})
        return response

