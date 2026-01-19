from django.http import Http404
from django.views.defaults import page_not_found
from django.shortcuts import render
from .models import Information

def dashboard(request):
    if not request.user.has_perm('informationmanagement.access_information_management_system'):
        return render(request, '404.html', status=404)

    systems = request.session.get('accessible_systems', [])
    informations = Information.objects.all()
    return render(request, 'informationmanagement/dashboard.html', {'informations': informations, 'systems': systems})