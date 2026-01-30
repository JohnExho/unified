from django.urls import path
from . import views

app_name = "inventorymanagement"

urlpatterns = [
    path('dashboard/', views.dashboard, name='inventory-dashboard'),
    path('inventory/', views.inventory, name='inventory'),
    path('assets/', views.assets, name='assets'),
    path('requisitions/', views.requisitions, name='requisitions'),
    path('reports/', views.reports, name='reports'),
    path('settings/', views.settings, name='settings'),
    path('upload-avatar/', views.upload_avatar, name='upload_avatar'),
    path('remove-avatar/', views.remove_avatar, name='remove_avatar'),
    path('profile-update/', views.profile_update, name='profile_update'),
    path('change-password/', views.change_password, name='change_password'),
    path('save-addresses/', views.save_addresses, name='save_addresses'),
    path('delete-address/<uuid:address_id>/', views.delete_address, name='delete_address'),
]
