from django.db import models
import datetime
# these below help to modify the information that can not be created at registraion by django 
# so we extend and create our our and autheticat them by django
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import slugify
# Create your models here.

#produc categories
class Category(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50, blank=True)

    class Meta:
        verbose_name_plural ='Categories'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# custome info
class Customer(models.Model):
    first_name = models.CharField(max_length=100)
    last_name =models.CharField(max_length=100)
    phone = models.CharField(max_length=100)
    email = models.EmailField()
    password =models.CharField(max_length=200)


    def __str__(self):
        return f"{self.first_name} {self.last_name}"

#All the products
class Product(models.Model):
    name = models.CharField(max_length=100)
    price= models.DecimalField(default=0,decimal_places=2,max_digits=10)
    category = models.ForeignKey(Category,on_delete=models.CASCADE,default=1)
    description =models.CharField(max_length=300,default='',blank=True,null=True)
    image = models.ImageField(upload_to='uploads/product/')
    is_onsale = models.BooleanField(default=False)
    sale_price = models.DecimalField(default=0,decimal_places=2,max_digits=10)

    def __str__(self):
        return self.name


class Order(models.Model):
    product = models.ForeignKey(Product,on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer,on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    address= models.CharField(max_length= 100,default='',blank=True)
    phone = models.CharField(max_length=20,default='',blank=True)
    date = models.DateField(default=datetime.datetime.today())
    status = models.BooleanField(default=False)

    def __str__(self):
        return self.product



class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    date_modified = models.DateTimeField(auto_now=True)
    phone = models.CharField(max_length=20, blank=True)
    address1 = models.CharField(max_length=200, blank=True)
    address2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=200, blank=True)
    state = models.CharField(max_length=200, blank=True)
    zipcode = models.CharField(max_length=200, blank=True)
    country = models.CharField(max_length=200, blank=True)
    district = models.CharField(max_length=200, blank=True)
    cart_info = models.CharField(max_length=200, blank=True,null=True)

    profile_picture = models.ImageField(
        upload_to='profile_pics/',    # Folder where uploaded images will go
        default='default_profile.png', # Default picture
        blank=True,
        null=True
    )

    def __str__(self):
        return self.user.username

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)