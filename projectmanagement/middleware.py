from core.models import SystemMembership
from django.shortcuts import render

class ProjectManagementSystemMiddleware:
    """
    Ensures `current_system` is set to 'researchmanagement' for all researchmanagement views.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only set for researchmanagement URLs
        if request.path.startswith('/researchmanagement/'):
            request.current_system = 'researchmanagement'
            # Don't override session during logout to preserve origin system
            if not request.path.endswith('/logout/'):
                request.session['current_system'] = 'researchmanagement'

        response = self.get_response(request)
        return response

class ProjectManagementAdminMiddleware:
    """
    Ensures that only users with admin or superadmin roles can access admin views.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/researchmanagement/admin/'):
            # Check if user is authenticated first
            if not request.user.is_authenticated:
                return render(request, 'projectmanagement/404.html', status=404)
            
            current_system = request.session.get('current_system', 'researchmanagement')
            if not request.user.is_superuser and not SystemMembership.objects.filter(
                user=request.user,
                system_name=current_system,
                system_role__in=['admin', 'superadmin']
            ).exists():
                return render(request, 'projectmanagement/404.html', status=404)

        response = self.get_response(request)
        return response