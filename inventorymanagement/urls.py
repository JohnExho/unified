from django.urls import path
from . import views

app_name = "inventorymanagement"

urlpatterns = [
    path('dashboard/', views.dashboard, name='inventory-dashboard'),
]
