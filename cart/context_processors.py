from .cart import Cart


# create the cart so that they exist on all the pages
def cart(request):
    #return the default data from our cart
    return{'cart':Cart(request)}