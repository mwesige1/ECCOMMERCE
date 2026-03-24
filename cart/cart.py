from decimal import Decimal
from django.conf import settings
from eccommence.models import Product, ProductVariant, Customer
from .models import Cart as CartModel, CartItem


class Cart:
    """
    Session-based cart helper class
    Syncs with database for authenticated users
    """
    
    def __init__(self, request):
        self.session = request.session
        self.request = request
        
        # Get or create session key
        if not request.session.session_key:
            request.session.create()
        
        # Initialize cart from session
        cart = self.session.get(settings.CART_SESSION_ID, {})
        
        # For authenticated users, sync with database
        if request.user.is_authenticated:
            self._sync_with_database()
        
        self.cart = cart
    
    def _sync_with_database(self):
        """Sync session cart with database for logged-in users"""
        try:
            # Check if user has customer_profile
            if not hasattr(self.request.user, 'customer_profile'):
                return
            
            customer = self.request.user.customer_profile
            db_cart, created = CartModel.objects.get_or_create(customer=customer)
            
            # If session has items, merge with database cart
            session_cart = self.session.get(settings.CART_SESSION_ID, {})
            if session_cart:
                for product_id, quantity in session_cart.items():
                    try:
                        product = Product.objects.get(id=int(product_id))
                        cart_item, created = CartItem.objects.get_or_create(
                            cart=db_cart,
                            product=product,
                            defaults={'quantity': quantity, 'price': product.current_price}
                        )
                        if not created:
                            cart_item.quantity += quantity
                            cart_item.save()
                    except Product.DoesNotExist:
                        pass
                
                # Clear session cart after syncing
                self.session[settings.CART_SESSION_ID] = {}
                self.session.modified = True
        except Exception:
            # Silently handle any cart sync issues
            pass
    
    def add(self, product, quantity=1, variant=None, update_quantity=False):
        """
        Add a product to the cart or update its quantity
        
        Args:
            product: Product instance
            quantity: Quantity to add
            variant: ProductVariant instance (optional)
            update_quantity: If True, set quantity; if False, add to existing
        """
        product_id = str(product.id)
        variant_id = str(variant.id) if variant else None
        cart_key = f"{product_id}_{variant_id}" if variant_id else product_id
        
        # Check stock availability
        if product.track_inventory:
            available_stock = variant.stock_quantity if variant else product.stock_quantity
            current_qty = self.cart.get(cart_key, 0)
            
            if not update_quantity:
                new_quantity = current_qty + quantity
            else:
                new_quantity = quantity
            
            if new_quantity > available_stock:
                raise ValueError(f"Only {available_stock} items available in stock")
        
        # Add or update quantity
        if cart_key in self.cart:
            if update_quantity:
                self.cart[cart_key] = quantity
            else:
                self.cart[cart_key] += quantity
        else:
            self.cart[cart_key] = quantity
        
        self.save()
        
        # Sync with database for authenticated users
        if self.request.user.is_authenticated:
            self._save_to_database(product, quantity, variant, update_quantity)
    
    def _save_to_database(self, product, quantity, variant, update_quantity):
        """Save cart to database for authenticated users"""
        try:
            if not hasattr(self.request.user, 'customer_profile'):
                return
            
            customer = self.request.user.customer_profile
            db_cart, created = CartModel.objects.get_or_create(customer=customer)
            
            cart_item, created = CartItem.objects.get_or_create(
                cart=db_cart,
                product=product,
                variant=variant,
                defaults={'quantity': quantity, 'price': product.current_price}
            )
            
            if not created:
                if update_quantity:
                    cart_item.quantity = quantity
                else:
                    cart_item.quantity += quantity
                cart_item.save()
        except Exception:
            pass
    
    def remove(self, product, variant=None):
        """Remove a product from the cart"""
        product_id = str(product.id)
        variant_id = str(variant.id) if variant else None
        cart_key = f"{product_id}_{variant_id}" if variant_id else product_id
        
        if cart_key in self.cart:
            del self.cart[cart_key]
            self.save()
            
            # Remove from database
            if self.request.user.is_authenticated:
                try:
                    if not hasattr(self.request.user, 'customer_profile'):
                        return
                    
                    customer = self.request.user.customer_profile
                    db_cart = CartModel.objects.filter(customer=customer).first()
                    if db_cart:
                        CartItem.objects.filter(
                            cart=db_cart,
                            product=product,
                            variant=variant
                        ).delete()
                except Exception:
                    pass
    
    def update_quantity(self, product, quantity, variant=None):
        """Update quantity for a specific product"""
        if quantity <= 0:
            self.remove(product, variant)
        else:
            self.add(product, quantity, variant, update_quantity=True)
    
    def increase_quantity(self, product, variant=None):
        """Increase quantity by 1"""
        product_id = str(product.id)
        variant_id = str(variant.id) if variant else None
        cart_key = f"{product_id}_{variant_id}" if variant_id else product_id
        
        if cart_key in self.cart:
            self.cart[cart_key] += 1
            self.save()
            
            # Update database
            if self.request.user.is_authenticated:
                self._update_database_quantity(product, self.cart[cart_key], variant)
            
            return self.cart[cart_key]
        return 0
    
    def decrease_quantity(self, product, variant=None):
        """Decrease quantity by 1, remove if reaches 0"""
        product_id = str(product.id)
        variant_id = str(variant.id) if variant else None
        cart_key = f"{product_id}_{variant_id}" if variant_id else product_id
        
        if cart_key in self.cart:
            if self.cart[cart_key] > 1:
                self.cart[cart_key] -= 1
                self.save()
                
                # Update database
                if self.request.user.is_authenticated:
                    self._update_database_quantity(product, self.cart[cart_key], variant)
                
                return self.cart[cart_key]
            else:
                self.remove(product, variant)
                return 0
        return 0
    
    def _update_database_quantity(self, product, quantity, variant):
        """Update quantity in database"""
        try:
            if not hasattr(self.request.user, 'customer_profile'):
                return
            
            customer = self.request.user.customer_profile
            db_cart = CartModel.objects.filter(customer=customer).first()
            if db_cart:
                cart_item = CartItem.objects.filter(
                    cart=db_cart,
                    product=product,
                    variant=variant
                ).first()
                if cart_item:
                    cart_item.quantity = quantity
                    cart_item.save()
        except Exception:
            pass
    
    def clear(self):
        """Clear the cart"""
        self.cart = {}
        self.save()
        
        # Clear database cart
        if self.request.user.is_authenticated:
            try:
                if not hasattr(self.request.user, 'customer_profile'):
                    return
                
                customer = self.request.user.customer_profile
                db_cart = CartModel.objects.filter(customer=customer).first()
                if db_cart:
                    db_cart.clear()
            except Exception:
                pass
    
    def get_products(self):
        """Get all products in cart with their quantities"""
        product_ids = []
        for key in self.cart.keys():
            # Extract product_id from cart_key (handles both "123" and "123_456" formats)
            product_id = key.split('_')[0]
            product_ids.append(int(product_id))
        
        products = Product.objects.filter(id__in=product_ids).select_related(
            'category', 'vendor'
        ).prefetch_related('images')
        
        # Attach quantity to each product
        for product in products:
            product_id = str(product.id)
            # Find the cart key (could have variant)
            for cart_key, quantity in self.cart.items():
                if cart_key.startswith(product_id):
                    product.cart_quantity = quantity
                    break
        
        return products
    
    def get_total_price(self):
        """Calculate total price of cart"""
        total = Decimal('0.00')
        
        for key, quantity in self.cart.items():
            product_id = key.split('_')[0]
            variant_id = key.split('_')[1] if '_' in key else None
            
            try:
                product = Product.objects.get(id=int(product_id))
                price = product.current_price
                
                if variant_id:
                    variant = ProductVariant.objects.get(id=int(variant_id))
                    price += variant.price_adjustment
                
                total += price * quantity
            except (Product.DoesNotExist, ProductVariant.DoesNotExist):
                pass
        
        return total
    
    def get_subtotal(self):
        """Alias for get_total_price"""
        return self.get_total_price()
    
    def __len__(self):
        """Return total number of items in cart"""
        return sum(self.cart.values())
    
    def __iter__(self):
        """Iterate over items in cart"""
        product_ids = [int(key.split('_')[0]) for key in self.cart.keys()]
        products = Product.objects.filter(id__in=product_ids)
        
        cart = self.cart.copy()
        
        for key, quantity in cart.items():
            product_id = int(key.split('_')[0])
            variant_id = int(key.split('_')[1]) if '_' in key else None
            
            product = next((p for p in products if p.id == product_id), None)
            if product:
                variant = None
                if variant_id:
                    try:
                        variant = ProductVariant.objects.get(id=variant_id)
                    except ProductVariant.DoesNotExist:
                        pass
                
                price = product.current_price
                if variant:
                    price += variant.price_adjustment
                
                yield {
                    'product': product,
                    'variant': variant,
                    'quantity': quantity,
                    'price': price,
                    'total_price': price * quantity,
                }
    
    def save(self):
        """Save cart to session"""
        self.session[settings.CART_SESSION_ID] = self.cart
        self.session.modified = True