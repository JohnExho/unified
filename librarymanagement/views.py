from django.http import Http404
from django.views.defaults import page_not_found
from django.shortcuts import render
from .models import Library
from core.models import SystemMembership

def dashboard(request):
    system_name = 'librarymanagement'  # current system
    
    if not request.user.is_superuser and not SystemMembership.objects.filter(user=request.user, system_name=system_name).exists():
        return render(request, '404.html', status=404)

     # Superuser bypass
    systems = request.session.get('accessible_systems', [])
    libraries = Library.objects.all()
    return render(request, 'librarymanagement/dashboard.html', {'libraries': libraries, 'systems': systems, 'system_name': system_name})