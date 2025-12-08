from django.contrib import admin
from.models import Category,Customer,Product,Order,Profile
from django.contrib.auth.models import User

# Register your models here.
admin.site.register(Category)
admin.site.register(Customer)
admin.site.register(Product)
admin.site.register( Order)
admin.site.register( Profile)



# so lets override the admin panel so that the fiels we have added on the profile 
# model be seen in the admin panel



# Add the profile information to the existing info in django
class ProfileInLine(admin.StackedInline):
    # which model are we extending or overriding
    model = Profile

# clarifies which model and the fielsd you want from the model and coconate
class UserAdmin(admin.ModelAdmin):
    model = User
    fields = ['username','first_name','last_name','email']
    inlines =[ProfileInLine]

# unregister the old way
admin.site.unregister(User)

# Re-register the new way
admin.site.register(User,UserAdmin)