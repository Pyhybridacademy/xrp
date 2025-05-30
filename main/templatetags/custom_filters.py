from django import template
from decimal import Decimal

register = template.Library()

@register.filter
def absolute(value):
    """Returns the absolute value of a number."""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return value

@register.filter
def subtract(value, arg):
    """Subtracts the arg from the value."""
    try:
        return Decimal(str(value)) - Decimal(str(arg))
    except (ValueError, TypeError):
        return value
