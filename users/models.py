from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

# =========================
# Profile model
# =========================
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, blank=True)
    address1 = models.CharField(max_length=200, blank=True)
    address2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=200, blank=True)
    state = models.CharField(max_length=200, blank=True)
    zipcode = models.CharField(max_length=200, blank=True)
    country = models.CharField(max_length=200, blank=True)
    district = models.CharField(max_length=200, blank=True)
    cart_info = models.CharField(max_length=200, blank=True, null=True)

    profile_picture = models.ImageField(
        upload_to='profile_pics/',
        default='default_profile.png',
        blank=True,
        null=True
    )

    def __str__(self):
        return self.user.username


"""# Signal to automatically create Profile when a new User is created
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
"""
User = settings.AUTH_USER_MODEL


class Shop(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

   
    class Meta:
        ordering=['created_at']

    def __str__(self):
        return self.name