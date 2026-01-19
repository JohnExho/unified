from django.http import Http404
from django.views.defaults import page_not_found
from django.shortcuts import render
from .models import Performance

def dashboard(request):
    if not request.user.has_perm('performanceevaluation.access_performance_evaluation_system'):
        return render(request, '404.html', status=404)

    systems = request.session.get('accessible_systems', [])
    performances = Performance.objects.all()
    return render(request, 'performanceevaluation/dashboard.html', {'performances': performances, 'systems': systems})