from eccommence.models import Product,Profile


class Cart():
    def __init__(self,request):
        
        self.session = request.session
        # Get the request
        self.request = request 

        #Get the current sessiobn key if it exists
        cart = self.session.get('session_key')

        # if the user is new ,no session key ! create one!
        if 'session_key' not in request.session:
            cart = self.session['session_key'] ={}

        # iniatializing the cart variable to use on everypage
        self.cart = cart

    def add(self,product,quantity):
        product_id = str(product.id)
        product_qty = str(quantity)

        # logic
        if product_id in self.cart:
            pass
        else:
            #self.cart[product_id] = {'price':str(product.price)}
            self.cart[product_id] = int(product_qty)

        self.session.modified = True

        # Deal with the logged in users to save their cart info in the database
        # check if the user is logged in
        if self.request.user.is_authenticated:
            # Get logged in user
            current_user = Profile.objects.filter(user__id=self.request.user.id)
            # convert our cart from {'3':2,'1':5} to {"3":2,"1":5} because we need to store json format in the db
            Jscart =str(self.cart)
            # replace the single cots with double cots
            Jscart=Jscart.replace("\'","\"")
            # save the Jcart to the database under profile with name cart_info
            current_user.update(cart_info=str(Jscart))


    # keep all the number fo the quantity in the cart
    def __len__(self):
        return len(self.cart)
    

    def cart_total(self):
        #{'3':6,'1':4} this is an example of how our dictionary looks like

        #Get the bid's of the products in cart
        product_ids = self.cart.keys()
        # look those keys in our product model in the database
        products = Product.objects.filter(id__in=product_ids)
        # Get the quantities
        quantities = self.cart
        # lets start counting at 0
        total = 0

        # iterate on all the quantities in the cart
        for key,value in quantities.items():
            # convert the key string back to an interger
            key = int(key)
            for product in products:
                if product.id == key:
                    if product.sale_price:
                        total = total + (product.sale_price * value)
                    else:
                        total = total + (product.price * value)
        return "{:,}".format(total)

    # function show all the products in the cart 
    def show_products(self):
        # get the id's of the products in the cart
        product_ids = self.cart.keys()
        # Use the and filter the products with those id's in the database
        products  = Product.objects.filter(id__in=product_ids)

        # return those very products
        return products
    
    # a function to display all the items in the cart
    def show_cart_items(self):
        quantities = self.cart
        return quantities
    

    def update(self,product,quantity):
        # the product and quantity paramenters we get them from our html through the jqeury
        #and then transfer them through the url to views up to the cart.py
        product_id = str(product)
        product_qty = int(quantity)

        # we charge to str and interger because the dictioray looks like this
        # {'3':5,'2':6} where the str is the key and int is the value

        # Get the cart and update the product id and the quantity
        Ourcart =self.cart
        Ourcart[product_id]=product_qty

        self.session.modified = True

         # Deal with the logged in users to save and update their cart info in the database
        # check if the user is logged in
        if self.request.user.is_authenticated:
            # Get logged in user
            current_user = Profile.objects.filter(user__id=self.request.user.id)
            # convert our cart from {'3':2,'1':5} to {"3":2,"1":5} because we need to store json format in the db
            Jscart =str(self.cart)
            # replace the single cots with double cots
            Jscart=Jscart.replace("\'","\"")
            # save the Jcart to the database under profile with name cart_info
            current_user.update(cart_info=str(Jscart))
        thing = self.cart
        return thing

    # Function to delte an item from the cart, the product is an id fron the frontend
    def delete(self,product):
        product_id = str(product)
        # check and delete the item with that id
        if product_id in self.cart:
            del self.cart[product_id]
        self.session.modified = True

         # Deal with the logged in users to save their cart info in the database
        # check if the user is logged in
        if self.request.user.is_authenticated:
            # Get logged in user
            current_user = Profile.objects.filter(user__id=self.request.user.id)
            # convert our cart from {'3':2,'1':5} to {"3":2,"1":5} because we need to store json format in the db
            Jscart =str(self.cart)
            # replace the single cots with double cots
            Jscart=Jscart.replace("\'","\"")
            # save the Jcart to the database under profile with name cart_info
            current_user.update(cart_info=str(Jscart))


    def db_add(self,product,quantity):
        product_id = str(product)
        product_qty = str(quantity)

        # logic
        if product_id in self.cart:
            pass
        else:
            #self.cart[product_id] = {'price':str(product.price)}
            self.cart[product_id] = int(product_qty)

        self.session.modified = True

        # Deal with the logged in users to save their cart info
        # check if the user is logged in
        if self.request.user.is_authenticated:
            # Get logged in user
            current_user = Profile.objects.filter(user__id=self.request.user.id)
            # convert our cart from {'3':2,'1':5} to {"3":2,"1":5} because we need to store json format in the db
            Jscart =str(self.cart)
            # replace the single cots with double cots
            Jscart=Jscart.replace("\'","\"")
            # save the Jcart to the database under profile with name cart_info
            current_user.update(cart_info=str(Jscart))

