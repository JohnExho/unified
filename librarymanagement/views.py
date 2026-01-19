from django.http import Http404
from django.views.defaults import page_not_found
from django.shortcuts import render
from .models import Library

def dashboard(request):
    if not request.user.has_perm('librarymanagement.access_library_management_system'):
        return render(request, '404.html', status=404)

    systems = request.session.get('accessible_systems', [])
    libraries = Library.objects.all()
    return render(request, 'librarymanagement/dashboard.html', {'libraries': libraries, 'systems': systems})