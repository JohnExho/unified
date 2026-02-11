from core.models import SystemMembership
from django.shortcuts import render

class ProjectManagementSystemMiddleware:
    """
    Ensures `current_system` is set to 'projectmanagement' for all projectmanagement views.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only set for projectmanagement URLs
        if request.path.startswith('/projectmanagement/'):
            request.current_system = 'projectmanagement'
            # Don't override session during logout to preserve origin system
            if not request.path.endswith('/logout/'):
                request.session['current_system'] = 'projectmanagement'
        else:
            request.current_system = None

        response = self.get_response(request)
        return response

class ProjectManagementAdminMiddleware:
    """
    Ensures that only users with admin or superadmin roles can access admin views.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/projectmanagement/admin/'):
            # Check if user is authenticated first
            if not request.user.is_authenticated:
                return render(request, 'projectmanagement/404.html', status=404)
            
            current_system = request.session.get('current_system', 'projectmanagement')
            if not request.user.is_superuser and not SystemMembership.objects.filter(
                user=request.user,
                system_name=current_system,
                system_role__in=['admin', 'superadmin']
            ).exists():
                return render(request, 'projectmanagement/404.html', status=404)

        response = self.get_response(request)
        return response