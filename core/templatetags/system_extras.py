from django import template
from core.models import Systems

register = template.Library()

@register.filter
def lookup_system(system_name):
    try:
        return Systems.objects.get(name=system_name)
    except Systems.DoesNotExist:
        return None

@register.filter
def dict_get(dictionary, key):
    """Get a value from a dictionary using a key"""
    if dictionary and key:
        return dictionary.get(key, ('user', 'User'))
    return ('user', 'User')