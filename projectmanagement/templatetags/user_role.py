from django import template
from core.models import SystemMembership

register = template.Library()


@register.simple_tag
def get_user_role(user, system_name):
    """
    Fetch the user's current role for a specific system directly from the database.
    This ensures the role is always up-to-date, even if it was recently changed.
    """
    if not user.is_authenticated:
        return None
    
    membership = SystemMembership.objects.filter(
        user=user,
        system_name=system_name,
        system_role__in=['admin', 'superadmin']
    ).first()
    
    return membership.system_role if membership else None
