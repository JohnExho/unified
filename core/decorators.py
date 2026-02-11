"""
Authorization decorators for RBAC enforcement.
"""
from functools import wraps
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from .models import SystemMembership


def require_system_access(view_func):
    """
    Ensures user has access to the current system.
    Must be used after @login_required.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        current_system = getattr(request, 'current_system', None) or request.session.get('current_system', 'core')
        
        # Superusers always have access
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Check system membership
        if not SystemMembership.objects.filter(
            user=request.user,
            system_name=current_system
        ).exists():
            # Find which system the user actually has access to and use that 404 page
            user_system = SystemMembership.objects.filter(
                user=request.user
            ).values_list('system_name', flat=True).first()
            
            # Use the user's system 404 page if they have one, otherwise generic
            if user_system:
                system_404_template = f'{user_system}/404.html'
                try:
                    return render(request, system_404_template, status=404)
                except:
                    pass
            
            # Fallback to generic 404
            return render(request, '404.html', status=404)
        
        return view_func(request, *args, **kwargs)
    return wrapper


def require_system_role(allowed_roles):
    """
    Ensures user has one of the specified roles in the current system.
    Must be used after @login_required.
    
    Usage:
        @login_required
        @require_system_role(['admin', 'superadmin'])
        def my_admin_view(request):
            ...
    
    Args:
        allowed_roles: List of role names (e.g., ['admin', 'superadmin'])
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            current_system = getattr(request, 'current_system', None) or request.session.get('current_system', 'core')
            
            # Superusers always have access
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Check if user has required role
            membership = SystemMembership.objects.filter(
                user=request.user,
                system_name=current_system,
                system_role__in=allowed_roles
            ).first()
            
            if not membership:
                # Determine if this is an AJAX request
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
                    return JsonResponse({
                        'error': 'You do not have permission to perform this action.',
                        'required_roles': allowed_roles
                    }, status=403)
                
                return HttpResponseForbidden(
                    "You do not have permission to access this page. "
                    f"Required roles: {', '.join(allowed_roles)}"
                )
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_superadmin(view_func):
    """
    Ensures user is either a Django superuser or has 'superadmin' role.
    Must be used after @login_required.
    
    Usage:
        @login_required
        @require_superadmin
        def delete_user(request, user_id):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        current_system = getattr(request, 'current_system', None) or request.session.get('current_system', 'core')
        
        # Check if user is Django superuser
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Check if user has superadmin role
        membership = SystemMembership.objects.filter(
            user=request.user,
            system_name=current_system,
            system_role='superadmin'
        ).first()
        
        if not membership:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
                return JsonResponse({
                    'error': 'Only superadmins can perform this action.'
                }, status=403)
            
            return HttpResponseForbidden(
                "You do not have permission to access this page. "
                "This action requires superadmin privileges."
            )
        
        return view_func(request, *args, **kwargs)
    return wrapper
