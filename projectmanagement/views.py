from django.http import Http404
from django.views.defaults import page_not_found
from django.shortcuts import render
from .models import Project
from core.utils import get_client_ip, get_user_agent, decrypt, encrypt
from core.models import SystemMembership
from core.forms import LoginForm

def dashboard(request):
    system_name = 'projectmanagement'  # current system
    # Superuser bypass
    if not request.user.is_superuser and not SystemMembership.objects.filter(user=request.user, system_name=system_name).exists():
        return render(request, '404.html', status=404)
    
    systems = request.session.get('accessible_systems', [])
    projects = Project.objects.all()
    return render(request, 'projectmanagement/pages/dashboard.html', {'projects': projects, 'systems': systems})

def settings(request):
    system_name = 'projectmanagement'  # current system
    # Superuser bypass
    if not request.user.is_superuser and not SystemMembership.objects.filter(user=request.user, system_name=system_name).exists():
        return render(request, '404.html', status=404)
    
    systems = request.session.get('accessible_systems', [])

    home_address = request.user.addresses.filter(type='home').first()
    secondary_address = request.user.addresses.filter(type='billing').first()

    # Decrypt the address fields if they exist
    if home_address:
        home_address.full_address = decrypt(home_address.full_address)
        home_address.city = decrypt(home_address.city)
        home_address.province = decrypt(home_address.province)
        home_address.postal_code = decrypt(home_address.postal_code)
        home_address.country = decrypt(home_address.country)
        if home_address.phone:
            home_address.phone = decrypt(home_address.phone)

    if secondary_address:
        secondary_address.full_address = decrypt(secondary_address.full_address)
        secondary_address.city = decrypt(secondary_address.city)
        secondary_address.province = decrypt(secondary_address.province)
        secondary_address.postal_code = decrypt(secondary_address.postal_code)
        secondary_address.country = decrypt(secondary_address.country)
        if secondary_address.phone:
            secondary_address.phone = decrypt(secondary_address.phone)

    return render(
        request,
        'projectmanagement/pages/settings.html',
        {
            'systems': systems,
            'home_address': home_address,
            'secondary_address': secondary_address,
            'system_name': system_name,
        }
    )