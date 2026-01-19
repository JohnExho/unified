from django.http import Http404
from django.views.defaults import page_not_found
from django.shortcuts import render
from .models import Inventory

def dashboard(request):
    if not request.user.has_perm('inventorymanagement.access_inventory_management_system'):
        return render(request, '404.html', status=404)

    systems = request.session.get('accessible_systems', [])
    inventories = Inventory.objects.all()
    return render(request, 'inventorymanagement/dashboard.html', {'inventories': inventories, 'systems': systems})