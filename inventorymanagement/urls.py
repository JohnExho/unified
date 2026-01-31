from django.urls import path
from . import views
from django.shortcuts import redirect

app_name = "inventorymanagement"

def root_redirect(request):
    if request.user.is_authenticated:
        return redirect('inventorymanagement:inventory-dashboard')
    else:
        return redirect('/inventorymanagement/login')

urlpatterns = [
    path('',  root_redirect, name='inventory-root'),
    path('dashboard/', views.dashboard, name='inventory-dashboard'),
    path('export-dashboard/', views.export_dashboard, name='export_dashboard'),
    path('inventory/', views.inventory, name='inventory'),
    path('assets/', views.assets, name='assets'),
    path('asset/<uuid:asset_id>/', views.asset_detail, name='asset_detail'),
    path('requisitions/', views.requisitions, name='requisitions'),
    path('reports/', views.reports, name='reports'),
    path('export-report/', views.export_report, name='export_report'),
    path('settings/', views.settings, name='settings'),
    path('upload-avatar/', views.upload_avatar, name='upload_avatar'),
    path('remove-avatar/', views.remove_avatar, name='remove_avatar'),
    path('profile-update/', views.profile_update, name='profile_update'),
    path('change-password/', views.change_password, name='change_password'),
    path('save-addresses/', views.save_addresses, name='save_addresses'),
    path('delete-address/<uuid:address_id>/', views.delete_address, name='delete_address'),
    
    # Inventory Management URLs
    path('inventory/create/', views.create_inventory_item, name='create_item'),
    path('inventory/edit/<uuid:item_id>/', views.edit_inventory_item, name='edit_item'),
    path('inventory/delete/<uuid:item_id>/', views.delete_inventory_item, name='delete_item'),
    path('inventory/export/', views.export_inventory, name='export_inventory'),
    path('category/create/', views.create_inventory_category, name='create_category'),
    path('category/delete/<uuid:category_id>/', views.delete_inventory_category, name='delete_category'),
    path('api/categories/', views.get_categories, name='get_categories'),
    
    # Asset Management URLs
    path('asset/create/', views.create_asset, name='create_asset'),
    path('asset/edit/<uuid:asset_id>/', views.edit_asset, name='edit_asset'),
    path('asset/delete/<uuid:asset_id>/', views.delete_asset, name='delete_asset'),
    path('asset/assign/<uuid:asset_id>/', views.assign_asset, name='assign_asset'),
    path('asset/return/<uuid:asset_id>/', views.return_asset, name='return_asset'),
    path('asset/export/', views.export_assets, name='export_assets'),
    path('asset-category/create/', views.create_asset_category, name='create_asset_category'),
    path('asset-category/delete/<uuid:category_id>/', views.delete_asset_category, name='delete_asset_category'),
    path('api/asset-categories/', views.get_asset_categories, name='get_asset_categories'),
    path('api/system-members/', views.get_system_members, name='get_system_members'),
    path('asset/<uuid:asset_id>/maintenance/', views.get_asset_maintenance, name='get_asset_maintenance'),
    path('asset/<uuid:asset_id>/maintenance/create/', views.create_asset_maintenance, name='create_asset_maintenance'),
    path('asset-maintenance/<uuid:maintenance_id>/edit/', views.edit_asset_maintenance, name='edit_asset_maintenance'),
    path('asset-maintenance/<uuid:maintenance_id>/delete/', views.delete_asset_maintenance, name='delete_asset_maintenance'),
    
    # Requisition Management URLs
    path('requisition/create/', views.create_requisition, name='create_requisition'),
    path('requisition/<uuid:requisition_id>/', views.view_requisition, name='view_requisition'),
    path('requisition/<uuid:requisition_id>/edit/', views.edit_requisition, name='edit_requisition'),
    path('requisition/<uuid:requisition_id>/delete/', views.delete_requisition, name='delete_requisition'),
    path('requisition/<uuid:requisition_id>/approve/', views.approve_requisition, name='approve_requisition'),
    path('requisition/<uuid:requisition_id>/reject/', views.reject_requisition, name='reject_requisition'),
    path('requisition/<uuid:requisition_id>/issue/', views.issue_requisition, name='issue_requisition'),
    path('requisition/<uuid:requisition_id>/items/', views.get_requisition_items, name='get_requisition_items'),
    path('requisitions/export/', views.export_requisitions, name='export_requisitions'),
    
    # Admin routes
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/system-logs/', views.system_logs, name='system_logs'),
    path('admin/deactivate-user/<uuid:user_id>/', views.deactivate_user, name='deactivate_user'),
    path('admin/activate-user/<uuid:user_id>/', views.activate_user, name='activate_user'),
    path('admin/update-tos/', views.update_tos, name='update_tos'),
    path('admin/manage-user-access/<uuid:user_id>/', views.manage_user_access, name='manage_user_access'),
]
