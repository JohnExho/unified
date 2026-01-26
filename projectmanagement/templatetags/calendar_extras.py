from django import template

register = template.Library()


@register.filter
def priority_level(priority):
    """
    Convert priority number (1-10) to level (low, medium, high)
    """
    if isinstance(priority, (int, float)):
        if priority >= 8:
            return 'high'
        elif priority >= 5:
            return 'medium'
        else:
            return 'low'
    return 'medium'


@register.filter
def priority_label(priority):
    """
    Convert priority number to readable label
    """
    if isinstance(priority, (int, float)):
        if priority >= 9:
            return 'Critical'
        elif priority >= 7:
            return 'High'
        elif priority >= 5:
            return 'Medium'
        elif priority >= 3:
            return 'Low'
        else:
            return 'Minimal'
    return 'Normal'


@register.filter
def get_item(dictionary, key):
    """
    Get item from dictionary by key
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def days_until(date):
    """
    Calculate days until a given date
    """
    from datetime import date as date_class, datetime
    if isinstance(date, datetime):
        date = date.date()
    
    if isinstance(date, date_class):
        today = date_class.today()
        delta = (date - today).days
        return delta
    return None


@register.filter
def status_text(days):
    """
    Get human-readable status text for days difference
    """
    if days == 0:
        return 'Today'
    elif days == 1:
        return 'Tomorrow'
    elif days > 0:
        return f'In {days} days'
    elif days == -1:
        return 'Yesterday'
    else:
        return f'{abs(days)} days ago'
