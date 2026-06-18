from django.shortcuts import redirect, render
from django.urls import reverse
from urllib.parse import urlparse, parse_qs

class SystemAwareLoginRedirectMiddleware:
    """
    Redirects generic /accounts/login/ to system-specific login pages
    based on the 'next' parameter.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if this is a redirect to the generic /accounts/login/ page
        if request.path == '/accounts/login/':
            next_url = request.GET.get('next', '')
            
            # Detect which system based on the 'next' URL
            if next_url:
                if next_url.startswith('/researchmanagement/'):
                    return redirect(f'/researchmanagement/login/?next={next_url}')
                elif next_url.startswith('/performanceevaluation/'):
                    return redirect(f'/performanceevaluation/login/?next={next_url}')
                elif next_url.startswith('/inventorymanagement/'):
                    return redirect(f'/inventorymanagement/login/?next={next_url}')
                elif next_url.startswith('/librarymanagement/'):
                    return redirect(f'/librarymanagement/login/?next={next_url}')
                elif next_url.startswith('/communityextensionservices/'):
                    return redirect(f'/communityextensionservices/login/?next={next_url}')
                elif next_url.startswith('/informationmanagement/'):
                    return redirect(f'/informationmanagement/login/?next={next_url}')
                elif next_url.startswith('/scholarshipmanagement/'):
                    return redirect(f'/scholarshipmanagement/login/?next={next_url}')
            
            # Default to core login for /accounts/login/ without a system-specific next URL
            return redirect('/login/')
        
        return self.get_response(request)


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
