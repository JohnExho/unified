from django.urls import path
from django.shortcuts import redirect
from . import views

app_name = "librarymanagement"

def root_redirect(request):
    return redirect('librarymanagement:library-dashboard')

urlpatterns = [
    path('',  root_redirect, name='library-root'),
    path('dashboard/', views.dashboard, name='library-dashboard'),
]


#naming convention use snake library_dashboard