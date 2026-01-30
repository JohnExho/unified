from django.http import Http404
from django.views.defaults import page_not_found
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count, Avg, F, ExpressionWrapper, DurationField
from .models import InventoryCategory, InventoryItem, InventoryTransaction, Asset, AssetCategory, AssetAssignment, Requisition
from core.models import Address, Logs
from core.utils import encrypt, decrypt, get_client_ip, get_user_agent
import uuid

def dashboard(request):
    if not request.user.has_perm('inventorymanagement.access_inventory_management_system'):
        return render(request, '404.html', status=404)

    systems = request.session.get('accessible_systems', [])
    inventories = InventoryItem.objects.all()
    return render(request, 'inventorymanagement/pages/dashboard.html', {'inventories': inventories, 'systems': systems})

def inventory(request):
    if not request.user.has_perm('inventorymanagement.access_inventory_management_system'):
        return render(request, '404.html', status=404)

    systems = request.session.get('accessible_systems', [])
    search_query = request.GET.get('search', '').strip()

    inventories = InventoryItem.objects.select_related('category')
    if search_query:
        inventories = inventories.filter(
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(unit__icontains=search_query)
        )

    return render(request, 'inventorymanagement/pages/inventory.html', {
        'inventories': inventories,
        'systems': systems,
        'search_query': search_query,
    })

def assets(request):
    if not request.user.has_perm('inventorymanagement.access_inventory_management_system'):
        return render(request, '404.html', status=404)

    systems = request.session.get('accessible_systems', [])
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()

    assets_queryset = Asset.objects.select_related('category').prefetch_related('assignments')
    
    if search_query:
        assets_queryset = assets_queryset.filter(
            Q(asset_code__icontains=search_query) |
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    if status_filter:
        assets_queryset = assets_queryset.filter(status=status_filter)

    # Get counts for each status
    all_count = Asset.objects.count()
    available_count = Asset.objects.filter(status='AVAILABLE').count()
    assigned_count = Asset.objects.filter(status='ASSIGNED').count()
    repair_count = Asset.objects.filter(status='UNDER_REPAIR').count()
    retired_count = Asset.objects.filter(status='RETIRED').count()

    # Get assigned to info for each asset
    assets_with_assignment = []
    for asset in assets_queryset:
        latest_assignment = asset.assignments.filter(returned_at__isnull=True).first()
        assigned_to = latest_assignment.assigned_to if latest_assignment else None
        assets_with_assignment.append({
            'asset': asset,
            'assigned_to': assigned_to
        })

    return render(request, 'inventorymanagement/pages/assets.html', {
        'assets_data': assets_with_assignment,
        'systems': systems,
        'search_query': search_query,
        'status_filter': status_filter,
        'all_count': all_count,
        'available_count': available_count,
        'assigned_count': assigned_count,
        'repair_count': repair_count,
        'retired_count': retired_count,
    })

def requisitions(request):
    if not request.user.has_perm('inventorymanagement.access_inventory_management_system'):
        return render(request, '404.html', status=404)

    systems = request.session.get('accessible_systems', [])
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip().upper()

    requisitions_queryset = Requisition.objects.select_related('requested_by', 'approved_by').annotate(
        item_count=Count('items', distinct=True)
    )

    if search_query:
        requisitions_queryset = requisitions_queryset.filter(
            Q(requested_by__first_name__icontains=search_query) |
            Q(requested_by__last_name__icontains=search_query) |
            Q(requested_by__username__icontains=search_query) |
            Q(purpose__icontains=search_query)
        )

    if status_filter:
        requisitions_queryset = requisitions_queryset.filter(status=status_filter)

    pending_count = Requisition.objects.filter(status='PENDING').count()
    approved_count = Requisition.objects.filter(status='APPROVED').count()
    rejected_count = Requisition.objects.filter(status='REJECTED').count()

    fulfillment_stats = Requisition.objects.filter(approved_at__isnull=False).annotate(
        fulfillment_time=ExpressionWrapper(
            F('approved_at') - F('created_at'),
            output_field=DurationField()
        )
    ).aggregate(avg_fulfillment=Avg('fulfillment_time'))

    avg_fulfillment_days = None
    if fulfillment_stats['avg_fulfillment']:
        avg_fulfillment_days = round(fulfillment_stats['avg_fulfillment'].total_seconds() / 86400, 1)

    return render(request, 'inventorymanagement/pages/requisitions.html', {
        'systems': systems,
        'requisitions': requisitions_queryset,
        'search_query': search_query,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'avg_fulfillment_days': avg_fulfillment_days,
    })

def reports(request):
    if not request.user.has_perm('inventorymanagement.access_inventory_management_system'):
        return render(request, '404.html', status=404)

    systems = request.session.get('accessible_systems', [])
    report_type = request.GET.get('report', 'transactions').strip().lower()
    
    # Get report statistics
    total_items = InventoryItem.objects.count()
    low_stock_items = InventoryItem.objects.filter(quantity__lte=F('low_stock_threshold')).count()
    total_assets = Asset.objects.count()
    total_requisitions = Requisition.objects.count()
    
    # Prepare data based on report type
    context = {
        'systems': systems,
        'report_type': report_type,
        'total_items': total_items,
        'low_stock_items': low_stock_items,
        'total_assets': total_assets,
        'total_requisitions': total_requisitions,
    }
    
    if report_type == 'inventory':
        inventories = InventoryItem.objects.select_related('category').all()
        context['inventories'] = inventories
    elif report_type == 'assets':
        assets_queryset = Asset.objects.select_related('category').prefetch_related('assignments')
        assets_with_assignment = []
        for asset in assets_queryset:
            latest_assignment = asset.assignments.filter(returned_at__isnull=True).first()
            assigned_to = latest_assignment.assigned_to if latest_assignment else None
            assets_with_assignment.append({
                'asset': asset,
                'assigned_to': assigned_to
            })
        context['assets_data'] = assets_with_assignment
    elif report_type == 'requisitions':
        requisitions_queryset = Requisition.objects.select_related('requested_by', 'approved_by').annotate(
            item_count=Count('items', distinct=True)
        )
        context['requisitions'] = requisitions_queryset
    else:
        # Default to transactions
        recent_transactions = InventoryTransaction.objects.select_related(
            'item', 'performed_by'
        ).order_by('-created_at')[:10]
        context['recent_transactions'] = recent_transactions
    
    return render(request, 'inventorymanagement/pages/reports.html', context)

def settings(request):
    if not request.user.has_perm('inventorymanagement.access_inventory_management_system'):
        return render(request, '404.html', status=404)
    
    systems = request.session.get('accessible_systems', [])
    
    # Get user addresses
    home_address = Address.objects.filter(user=request.user, type='home').first()
    secondary_address = Address.objects.filter(user=request.user, type='billing').first()
    
    # Decrypt address fields if they exist
    if home_address:
        home_address.full_address = decrypt(home_address.full_address)
        home_address.city = decrypt(home_address.city)
        home_address.province = decrypt(home_address.province)
        home_address.postal_code = decrypt(home_address.postal_code)
        home_address.country = decrypt(home_address.country)
    
    if secondary_address:
        secondary_address.full_address = decrypt(secondary_address.full_address)
        secondary_address.city = decrypt(secondary_address.city)
        secondary_address.province = decrypt(secondary_address.province)
        secondary_address.postal_code = decrypt(secondary_address.postal_code)
        secondary_address.country = decrypt(secondary_address.country)
    
    return render(request, 'inventorymanagement/pages/settings.html', {
        'systems': systems,
        'home_address': home_address,
        'secondary_address': secondary_address
    })

@login_required
@require_POST
def upload_avatar(request):
    avatar = request.FILES.get("avatar")
    if avatar:
        # Delete old avatar if exists
        if request.user.avatar:
            request.user.avatar.delete(save=False)

        # Save new avatar
        request.user.avatar = avatar
        request.user.save()

        Logs.objects.create(
            user=request.user,
            system_name='inventorymanagement',
            action='UPDATE',
            target_model='User',
            target_id=request.user.id,
            description=f"Updated avatar for user '{request.user.username}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )

        messages.success(request, "Avatar uploaded successfully.")
    return redirect('inventorymanagement:settings')

@login_required
@require_POST
def remove_avatar(request):
    if request.user.avatar:
        request.user.avatar.delete(save=False)
        request.user.avatar = None
        request.user.save()
    
        Logs.objects.create(
            user=request.user,
            system_name='inventorymanagement',
            action='UPDATE',
            target_model='User',
            target_id=request.user.id,
            description=f"Removed avatar for user '{request.user.username}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )

    messages.success(request, "Avatar removed successfully.")
    return redirect('inventorymanagement:settings')

@login_required
@require_POST
def profile_update(request):
    user = request.user

    # Get form data
    first_name = request.POST.get("first_name", "").strip()
    middle_name = request.POST.get("middle_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    username = request.POST.get("username", "").strip()
    phone = request.POST.get("phone", "").strip()
    bio = request.POST.get("bio", "").strip()

    # Update user fields
    if first_name:
        user.first_name = first_name
    if middle_name:
        user.middle_name = middle_name
    if last_name:
        user.last_name = last_name
    if username:
        user.username = username
    if phone:
        user.phone_number = phone
    if bio:
        user.bio = bio

    user.save()

    Logs.objects.create(
        user=user,
        system_name='inventorymanagement',
        action='UPDATE',
        target_model='User',
        target_id=user.id,
        description=f"Updated profile for user '{user.username}'",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )

    messages.success(request, "Profile updated successfully.")
    return redirect("inventorymanagement:settings")

@login_required
def change_password(request):
    if request.method == "POST":
        current_password = request.POST.get("current_password")
        new_password1 = request.POST.get("new_password1")
        new_password2 = request.POST.get("new_password2")
        user = request.user

        # Check current password
        if not user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
            return redirect("inventorymanagement:settings")

        # Check new passwords match
        if new_password1 != new_password2:
            messages.error(request, "New passwords do not match.")
            return redirect("inventorymanagement:settings")

        # Validate password strength
        if len(new_password1) < 8:
            messages.error(request, "New password must be at least 8 characters long.")
            return redirect("inventorymanagement:settings")

        # Set new password
        user.set_password(new_password1)
        user.save()

        # Keep user logged in after password change
        update_session_auth_hash(request, user)

        Logs.objects.create(
            user=user,
            system_name='inventorymanagement',
            action='UPDATE',
            target_model='User',
            target_id=user.id,
            description=f"Changed password for user '{user.username}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )

        messages.success(request, "Password changed successfully.")
        return redirect("inventorymanagement:settings")

    return redirect("inventorymanagement:settings")

@login_required
def save_addresses(request):
    if request.method != "POST":
        return redirect("inventorymanagement:settings")

    user = request.user

    # Handle Address 1 (home)
    home_address, created = Address.objects.get_or_create(
        user=user,
        type="home",
        defaults={
            "id": uuid.uuid4(),
            "full_address": encrypt(request.POST.get("address1", "")),
            "city": encrypt(request.POST.get("city1", "")),
            "province": encrypt(request.POST.get("province1", "")),
            "postal_code": encrypt(request.POST.get("zip1", "")),
            "country": encrypt(request.POST.get("country1", "")),
            "phone": encrypt(request.POST.get("phone1", "")),
            "created_at": timezone.now(),
            "updated_at": timezone.now(),
        }
    )

    if created:
        Logs.objects.create(
            user=user,
            system_name='inventorymanagement',
            action='CREATE',
            target_model='Address',
            target_id=home_address.id,
            description=f"Created home address for user '{user.username}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
    else:
        # Update existing home address
        home_address.full_address = encrypt(request.POST.get("address1", ""))
        home_address.city = encrypt(request.POST.get("city1", ""))
        home_address.province = encrypt(request.POST.get("province1", ""))
        home_address.postal_code = encrypt(request.POST.get("zip1", ""))
        home_address.country = encrypt(request.POST.get("country1", ""))
        home_address.phone = encrypt(request.POST.get("phone1", ""))
        home_address.updated_at = timezone.now()
        home_address.save()

        Logs.objects.create(
            user=user,
            system_name='inventorymanagement',
            action='UPDATE',
            target_model='Address',
            target_id=home_address.id,
            description=f"Updated home address for user '{user.username}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )

    # Handle Address 2 (billing/secondary)
    address2_value = request.POST.get("address2", "").strip()
    if address2_value:
        billing_address, created = Address.objects.get_or_create(
            user=user,
            type="billing",
            defaults={
                "id": uuid.uuid4(),
                "full_address": encrypt(address2_value),
                "city": encrypt(request.POST.get("city2", "")),
                "province": encrypt(request.POST.get("province2", "")),
                "postal_code": encrypt(request.POST.get("zip2", "")),
                "country": encrypt(request.POST.get("country2", "")),
                "phone": encrypt(request.POST.get("phone2", "")),
                "created_at": timezone.now(),
                "updated_at": timezone.now(),
            }
        )

        if created:
            Logs.objects.create(
                user=user,
                system_name='inventorymanagement',
                action='CREATE',
                target_model='Address',
                target_id=billing_address.id,
                description=f"Created billing address for user '{user.username}'",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
            )
        else:
            billing_address.full_address = encrypt(address2_value)
            billing_address.city = encrypt(request.POST.get("city2", ""))
            billing_address.province = encrypt(request.POST.get("province2", ""))
            billing_address.postal_code = encrypt(request.POST.get("zip2", ""))
            billing_address.country = encrypt(request.POST.get("country2", ""))
            billing_address.phone = encrypt(request.POST.get("phone2", ""))
            billing_address.updated_at = timezone.now()
            billing_address.save()

            Logs.objects.create(
                user=user,
                system_name='inventorymanagement',
                action='UPDATE',
                target_model='Address',
                target_id=billing_address.id,
                description=f"Updated billing address for user '{user.username}'",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
            )

    messages.success(request, "Addresses saved successfully.")
    return redirect("inventorymanagement:settings")

@login_required
def delete_address(request, address_id):
    address = get_object_or_404(
        Address,
        id=address_id,
        user=request.user
    )

    # Never allow deleting home address
    if address.type == 'home':
        messages.error(request, "Cannot delete home address.")
        return redirect('inventorymanagement:settings')

    if request.method == "POST":
        address.delete()

        Logs.objects.create(
            user=request.user,
            system_name='inventorymanagement',
            action='DELETE',
            target_model='Address',
            target_id=address.id,
            description=f"Deleted address for user '{request.user.username}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )

        messages.success(request, "Address deleted successfully.")

    return redirect('inventorymanagement:settings')