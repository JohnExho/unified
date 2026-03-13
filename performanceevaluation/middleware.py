from core.models import SystemMembership
from django.shortcuts import render


class PerformanceEvaluationSystemMiddleware:
    """
    Ensures `current_system` is set to 'performanceevaluation' for all performanceevaluation views.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/performanceevaluation/'):
            request.current_system = 'performanceevaluation'
            # Don't override session during logout to preserve origin system
            if not request.path.endswith('/logout/'):
                request.session['current_system'] = 'performanceevaluation'

        return self.get_response(request)


class PerformanceEvaluationAdminMiddleware:
    """
    Ensures that only users with admin or superadmin roles can access admin views.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/performanceevaluation/admin/'):
            # Check if user is authenticated first
            if not request.user.is_authenticated:
                return render(request, 'performanceevaluation/404.html', status=404)
            
            current_system = request.session.get('current_system', 'performanceevaluation')
            if not request.user.is_superuser and not SystemMembership.objects.filter(
                user=request.user,
                system_name=current_system,
                system_role__in=['admin', 'superadmin']
            ).exists():
                return render(request, 'performanceevaluation/404.html', status=404)

        return self.get_response(request)
