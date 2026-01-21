from django.shortcuts import redirect, render
from django.urls import reverse

class SuperuserOnlyDashboardMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        dashboard_url = reverse('core:core_dashboard')

        # Normalize the path: strip trailing slash
        request_path = request.path.rstrip('/')

        if request_path == dashboard_url.rstrip('/'):
            user = request.user

            if not (user.is_authenticated and user.is_superuser):
                # Option 1: redirect to login
                current_system = request.session.get('current_system', 'core')
                request.session.flush()
                return redirect(f'/{current_system}/login/')
                # Option 2: redirect home
                # return redirect('/')
                # Option 3: show 403
                # from django.http import HttpResponseForbidden
                # return HttpResponseForbidden("You are not allowed here.")

        return self.get_response(request)
