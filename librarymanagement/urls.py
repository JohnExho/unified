from django.urls import path
from . import views

app_name = "librarymanagement"

urlpatterns = [
    path('dashboard/', views.dashboard, name='library-dashboard'),
]
