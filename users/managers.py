from django.db import models


class UserQuerySet(models.QuerySet):
    """Custom queryset for User model"""
    
    def customers(self):
        """Return only customer users"""
        return self.filter(user_type='customer')
    
    def vendors(self):
        """Return only vendor users"""
        return self.filter(user_type='vendor')
    
    def active(self):
        """Return only active users"""
        return self.filter(is_active=True)
    
    def verified(self):
        """Return only verified users"""
        return self.filter(is_verified=True)