from django.db import models
from django.contrib.auth.models import User
from eccommence.models import Product
from django.db.models.signals import post_save
from django.dispatch import receiver



# Create your models here.

class ShippingAddress(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE,blank=True,null=True)
    shipping_full_name = models.CharField(max_length=255)
    shipping_email = models.CharField(max_length=255)
    shipping_address1 = models.CharField(max_length=255 ,null=True,blank=True )
    shipping_address2= models.CharField(max_length=255 ,null=True,blank=True)
    shipping_city = models.CharField(max_length=255 ,null=True)
    shipping_state = models.CharField(max_length=255,null=True,blank=True)
    shipping_country = models.CharField(max_length=255,null=True)



    # Do not pluralize Address
    class Meta:
        verbose_name_plural = 'Shipping Address'


    def __str__(self):
        return f'Shipping Address - {str(self.id)}'

    # create the shipping address automatically once a new user is created
""" @receiver(post_save, sender=User)
    def create_shppingAddress(sender, instance, created, **kwargs):
        if created:
            ShippingAddress.objects.create(user=instance)"""
        
# model to get all the orders in the cart for payment
class Order(models .Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE,blank=True,null=True)
    full_name = models.CharField(max_length=250)
    email = models .EmailField(max_length=250)
    shipping_address = models.TextField()
    amoint_paid = models.DecimalField(max_digits=15,decimal_places=2)
    date_ordered = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Order ID - {str(self.id)}'


# models to the all the items in the cart for payment
class OrderItem(models.Model):
    # Foriegn key to access order,product the person ordering

    order = models.ForeignKey(Order,on_delete=models.CASCADE,blank=True)
    product = models.ForeignKey(Product,on_delete=models.CASCADE, blank=True)
    user = models.ForeignKey(User,on_delete=models.CASCADE,blank=True,null=True)

    quantity = models.PositiveBigIntegerField(default=1)
    price = models.DecimalField(max_digits=15,decimal_places=2)

    def __str__(self):
        return f'Order Item -{str(self.id)}'



