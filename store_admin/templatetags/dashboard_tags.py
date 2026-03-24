from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply two values"""
    try:
        return Decimal(str(value)) * Decimal(str(arg))
    except (ValueError, TypeError, Decimal.InvalidOperation):
        return 0

@register.filter
def divide(value, arg):
    """Divide two values"""
    try:
        if Decimal(str(arg)) == 0:
            return 0
        return Decimal(str(value)) / Decimal(str(arg))
    except (ValueError, TypeError, Decimal.InvalidOperation):
        return 0

@register.filter
def percentage(value, total):
    """Calculate percentage"""
    try:
        if Decimal(str(total)) == 0:
            return 0
        return (Decimal(str(value)) / Decimal(str(total)) * 100)
    except (ValueError, TypeError, Decimal.InvalidOperation):
        return 0

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary"""
    return dictionary.get(key)

@register.simple_tag
def status_color(status):
    """Return color class for status"""
    colors = {
        'pending': 'status-pending',
        'processing': 'status-processing',
        'shipped': 'status-shipped',
        'delivered': 'status-delivered',
        'cancelled': 'status-cancelled',
    }
    return colors.get(status, '')