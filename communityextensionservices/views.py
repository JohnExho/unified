from django.http import Http404
from django.views.defaults import page_not_found
from django.shortcuts import render
from .models import Service

def dashboard(request):
    if not request.user.has_perm('communityextensionservices.access_community_extension_services_system'):
        return render(request, '404.html', status=404)
    
    systems = request.session.get('accessible_systems', [])
    services = Service.objects.all()
    return render(request, 'communityextensionservices/dashboard.html', {'services': services, 'systems': systems})
