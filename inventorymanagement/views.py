from django.http import Http404, JsonResponse, HttpResponse
from django.views.defaults import page_not_found
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count, Avg, F, ExpressionWrapper, DurationField
from .models import InventoryCategory, InventoryItem, InventoryTransaction, Asset, AssetCategory, AssetAssignment, AssetMaintenance, Requisition, RequisitionItem, MLInsight
from core.models import Address, Logs, SystemMembership
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from core.utils import encrypt, decrypt, get_client_ip, get_user_agent
from core.decorators import require_system_access, require_system_role
import uuid
from django.core.paginator import Paginator
from core.models import Systems
import csv
import json
from datetime import datetime, timedelta

@login_required
@require_system_access
def dashboard(request):
    from django.db.models.functions import TruncDate
    from django.utils import timezone
    from datetime import timedelta
    import json
    
    current_system = request.current_system
    systems = request.session.get('accessible_systems', [])
    
    # Get basic statistics
    total_items = InventoryItem.objects.count()
    active_items = InventoryItem.objects.filter(quantity__gt=F('low_stock_threshold')).count()
    out_of_stock = InventoryItem.objects.filter(quantity=0).count()
    low_stock = InventoryItem.objects.filter(quantity__gt=0, quantity__lte=F('low_stock_threshold')).count()
    # Show both low stock and out of stock items in the table (items needing attention)
    low_stock_items = InventoryItem.objects.filter(quantity__lte=F('low_stock_threshold')).order_by('quantity')
    
    # Get today's transactions
    today = timezone.now().date()
    issued_today = InventoryTransaction.objects.filter(
        created_at__date=today,
        transaction_type='ISSUE'
    ).count()
    returned_today = InventoryTransaction.objects.filter(
        created_at__date=today,
        transaction_type='RETURN'
    ).count()
    
    # Get inventory by category for bar chart
    from django.db.models import Sum
    category_data = InventoryItem.objects.values('category__name').annotate(
        total_quantity=Sum('quantity')
    ).order_by('-total_quantity')[:5]
    
    category_labels = [item['category__name'] or 'Uncategorized' for item in category_data]
    category_values = [item['total_quantity'] or 0 for item in category_data]
    
    # Get transaction trend for last 30 days (line chart)
    last_30_days = timezone.now() - timedelta(days=30)
    transaction_data = InventoryTransaction.objects.filter(
        created_at__gte=last_30_days
    ).annotate(date=TruncDate('created_at')).values('date', 'transaction_type').annotate(
        count=Count('id')
    ).order_by('date')
    
    # Organize data by date and type
    dates_set = set()
    issued_dict = {}
    returned_dict = {}
    
    for item in transaction_data:
        date_str = item['date'].strftime('%b %d')
        dates_set.add((item['date'], date_str))
        if item['transaction_type'] == 'ISSUE':
            issued_dict[date_str] = item['count']
        elif item['transaction_type'] == 'RETURN':
            returned_dict[date_str] = item['count']
    
    # Sort dates and create aligned data
    sorted_dates = sorted(dates_set, key=lambda x: x[0])
    trend_dates = [d[1] for d in sorted_dates]
    issued_values = [issued_dict.get(d[1], 0) for d in sorted_dates]
    returned_values = [returned_dict.get(d[1], 0) for d in sorted_dates]
    
    # Get recent transactions
    recent_transactions = InventoryTransaction.objects.select_related(
        'item', 'performed_by'
    ).order_by('-created_at')[:10]
    
    context = {
        'systems': systems,
        'current_system': current_system,
        'total_items': total_items,
        'active_items': active_items,
        'low_stock_count': low_stock,
        'out_of_stock': out_of_stock,
        'low_stock_items': low_stock_items,
        'issued_today': issued_today,
        'returned_today': returned_today,
        'category_labels': json.dumps(category_labels),
        'category_values': json.dumps(category_values),
        'trend_dates': json.dumps(trend_dates),
        'issued_values': json.dumps(issued_values),
        'returned_values': json.dumps(returned_values),
        'recent_transactions': recent_transactions,
    }
    
    return render(request, 'inventorymanagement/pages/dashboard.html', context)

@login_required
@require_system_access
def inventory(request):
    current_system = request.current_system
    systems = request.session.get('accessible_systems', [])
    search_query = request.GET.get('search', '').strip()
    category_filter = request.GET.get('category', '').strip()
    stock_status_filter = request.GET.get('stock_status', '').strip()
    status_filter = request.GET.get('status', '').strip()

    inventories = InventoryItem.objects.select_related('category')
    
    if search_query:
        inventories = inventories.filter(
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(unit__icontains=search_query)
        )
    
    if category_filter:
        inventories = inventories.filter(category__id=category_filter)
    
    if stock_status_filter == 'low':
        inventories = inventories.filter(quantity__lte=F('low_stock_threshold'))
    elif stock_status_filter == 'normal':
        inventories = inventories.filter(quantity__gt=F('low_stock_threshold'))
    
    if status_filter == 'active':
        inventories = inventories.filter(is_active=True)
    elif status_filter == 'inactive':
        inventories = inventories.filter(is_active=False)
    
    # Get all categories for filter dropdown
    categories = InventoryCategory.objects.filter(is_active=True)

    context = {
        'inventories': inventories,
        'systems': systems,
        'current_system': current_system,
        'search_query': search_query,
        'categories': categories,
        'category_filter': category_filter,
        'stock_status_filter': stock_status_filter,
        'status_filter': status_filter,
    }

    # Return only table partial for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'inventorymanagement/partials/_inventory_table.html', context)

    return render(request, 'inventorymanagement/pages/inventory.html', context)
@login_required
@require_system_access
def asset_detail(request, asset_id):
    """Show detailed view of a single asset with maintenance history"""
    asset = get_object_or_404(Asset, id=asset_id)
    latest_assignment = asset.assignments.filter(returned_at__isnull=True).first()
    assigned_to = latest_assignment.assigned_to if latest_assignment else None
    
    # Check if user is admin
    current_system = request.current_system
    is_admin = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system,
        system_role__in=['admin', 'superadmin']
    ).exists()
    
    return render(request, 'inventorymanagement/pages/asset_detail.html', {
        'asset': asset,
        'assigned_to': assigned_to,
        'is_admin': is_admin,
    })


@login_required
@require_system_access
def assets(request):
    current_system = request.current_system
    systems = request.session.get('accessible_systems', [])
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    category_filter = request.GET.get('category', '').strip()
    assignment_filter = request.GET.get('assignment', '').strip()

    assets_queryset = Asset.objects.select_related('category').prefetch_related('assignments')
    
    if search_query:
        assets_queryset = assets_queryset.filter(
            Q(asset_code__icontains=search_query) |
            Q(name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    if status_filter:
        assets_queryset = assets_queryset.filter(status=status_filter)
    
    if category_filter:
        assets_queryset = assets_queryset.filter(category__id=category_filter)

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
        
        # Apply assignment filter
        if assignment_filter == 'assigned' and not assigned_to:
            continue
        elif assignment_filter == 'unassigned' and assigned_to:
            continue
        
        assets_with_assignment.append({
            'asset': asset,
            'assigned_to': assigned_to
        })

    # Check if this is an AJAX request for partial HTML
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'inventorymanagement/partials/_assets_table.html', {
            'assets_data': assets_with_assignment,
        })

    return render(request, 'inventorymanagement/pages/assets.html', {
        'assets_data': assets_with_assignment,
        'systems': systems,
        'current_system': current_system,
        'search_query': search_query,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'assignment_filter': assignment_filter,
        'all_count': all_count,
        'available_count': available_count,
        'assigned_count': assigned_count,
        'repair_count': repair_count,
        'retired_count': retired_count,
    })

@login_required
@require_system_access
def requisitions(request):
    current_system = request.current_system
    systems = request.session.get('accessible_systems', [])
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip().upper()
    approval_filter = request.GET.get('approval', '').strip().lower()
    date_range = request.GET.get('date_range', '30').strip()

    requisitions_queryset = Requisition.objects.select_related('requested_by', 'approved_by').annotate(
        item_count=Count('items', distinct=True)
    )

    if search_query:
        # Search by username or purpose (first_name/last_name are encrypted)
        from django.contrib.auth import get_user_model
        User = get_user_model()
        matching_users = User.objects.filter(
            username__icontains=search_query
        ).values_list('id', flat=True)
        
        requisitions_queryset = requisitions_queryset.filter(
            Q(requested_by_id__in=matching_users) |
            Q(purpose__icontains=search_query) |
            Q(event_name__icontains=search_query) |
            Q(borrower_first_name__icontains=search_query) |
            Q(borrower_last_name__icontains=search_query)
        )

    if status_filter:
        requisitions_queryset = requisitions_queryset.filter(status=status_filter)

    # Approval filter
    if approval_filter == 'approved':
        requisitions_queryset = requisitions_queryset.filter(approved_by__isnull=False)
    elif approval_filter == 'unapproved':
        requisitions_queryset = requisitions_queryset.filter(approved_by__isnull=True)

    # Date range filter
    if date_range and date_range != 'all':
        try:
            days = int(date_range)
            from_date = timezone.now() - timedelta(days=days)
            requisitions_queryset = requisitions_queryset.filter(created_at__gte=from_date)
        except ValueError:
            pass

    pending_count = Requisition.objects.filter(status='PENDING').count()
    approved_count = Requisition.objects.filter(status='APPROVED').count()
    rejected_count = Requisition.objects.filter(status='REJECTED').count()

    requisitions_list = list(requisitions_queryset)

    for requisition in requisitions_list:
        borrower_name = f"{requisition.borrower_first_name} {requisition.borrower_middle_initial} {requisition.borrower_last_name}".replace('  ', ' ').strip()
        requestor_display = requisition.requested_by.get_full_name() or requisition.requested_by.username
        requisition.borrower_display = borrower_name or requestor_display
        requisition.requestor_display = requestor_display if borrower_name and borrower_name != requestor_display else None
        requisition.event_display = requisition.event_name or '—'
        requisition.schedule_display = requisition.created_at.strftime('%Y-%m-%d')
        requisition.purpose_display = requisition.purpose or '—'

        if requisition.date_borrowed or requisition.date_returned:
            start_text = f"{requisition.date_borrowed or '—'} {requisition.time_borrowed or ''}".strip()
            end_text = f"{requisition.date_returned or '—'} {requisition.time_returned or ''}".strip()
            requisition.schedule_display = f"{start_text} to {end_text}".strip()

        # Legacy fallback for requisitions created before dedicated fields were added.
        if not borrower_name and requisition.purpose:
            purpose_lines = [line.strip() for line in requisition.purpose.splitlines() if line.strip()]
            line_map = {}
            for line in purpose_lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    line_map[key.strip().lower()] = value.strip()

            requisition.borrower_display = line_map.get('borrower', requisition.borrower_display)
            requisition.event_display = line_map.get('name of event', '—')

            date_borrowed = line_map.get('date borrowed')
            date_returned = line_map.get('date returned')
            time_borrowed = line_map.get('time borrowed')
            time_returned = line_map.get('time returned')

            if date_borrowed or date_returned:
                start_text = f"{date_borrowed or '—'} {time_borrowed or ''}".strip()
                end_text = f"{date_returned or '—'} {time_returned or ''}".strip()
                requisition.schedule_display = f"{start_text} to {end_text}".strip()

            requisition.purpose_display = line_map.get('purpose/notes', requisition.purpose_display)

    # Calculate average fulfillment time for ISSUED requisitions only
    fulfillment_stats = Requisition.objects.filter(status='ISSUED', approved_at__isnull=False).annotate(
        fulfillment_time=ExpressionWrapper(
            F('approved_at') - F('created_at'),
            output_field=DurationField()
        )
    ).aggregate(avg_fulfillment=Avg('fulfillment_time'))

    avg_fulfillment_days = None
    if fulfillment_stats['avg_fulfillment']:
        total_seconds = fulfillment_stats['avg_fulfillment'].total_seconds()
        days = total_seconds / 86400
        if days >= 1:
            avg_fulfillment_days = f"{round(days, 1)} days"
        else:
            hours = total_seconds / 3600
            avg_fulfillment_days = f"{round(hours, 1)} hours"


    # Check if user is admin
    is_admin = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system,
        system_role__in=['admin', 'superadmin']
    ).exists()

    # Check if it's an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'inventorymanagement/partials/_requisitions_table.html', {
            'requisitions': requisitions_list,
            'is_admin': is_admin,
        })

    return render(request, 'inventorymanagement/pages/requisitions.html', {
        'systems': systems,
        'current_system': current_system,
        'requisitions': requisitions_list,
        'search_query': search_query,
        'status_filter': status_filter,
        'approval_filter': approval_filter,
        'date_range': date_range,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'avg_fulfillment_days': avg_fulfillment_days,
        'avg_fulfillment_days': avg_fulfillment_days,
        'is_admin': is_admin,
    })

@login_required
@require_system_access
def reports(request):
    from django.db.models.functions import TruncDate
    from django.utils import timezone
    from datetime import timedelta
    import json
    
    current_system = request.current_system
    systems = request.session.get('accessible_systems', [])
    report_type = request.GET.get('report', 'transactions').strip().lower()
    
    # Get report statistics
    total_items = InventoryItem.objects.count()
    low_stock_items = InventoryItem.objects.filter(quantity__lte=F('low_stock_threshold')).count()
    total_assets = Asset.objects.count()
    total_requisitions = Requisition.objects.count()
    
    # Base context
    context = {
        'systems': systems,
        'current_system': current_system,
        'report_type': report_type,
        'total_items': total_items,
        'low_stock_items': low_stock_items,
        'total_assets': total_assets,
        'total_requisitions': total_requisitions,
    }
    
    # Get data for last 30 days
    last_30_days = timezone.now() - timedelta(days=30)
    
    if report_type == 'inventory':
        # Get inventory items
        inventories = InventoryItem.objects.select_related('category').all()
        context['inventories'] = inventories
        
        # Inventory stock trend - cumulative stock over time
        stock_trend = InventoryTransaction.objects.filter(
            created_at__gte=last_30_days
        ).annotate(date=TruncDate('created_at')).values('date').annotate(
            issued=Count('id', filter=Q(transaction_type='ISSUE')),
            returned=Count('id', filter=Q(transaction_type='RETURN'))
        ).order_by('date')
        
        # Calculate cumulative stock level
        initial_stock = InventoryItem.objects.aggregate(total=Count('id'))['total'] or 0
        cumulative_stock = initial_stock
        stock_dates = []
        stock_levels = []
        
        for item in stock_trend:
            stock_dates.append(item['date'].strftime('%b %d'))
            cumulative_stock += (item['returned'] - item['issued'])
            stock_levels.append(cumulative_stock)
        
        context['stock_trend_dates'] = json.dumps(stock_dates)
        context['stock_trend_levels'] = json.dumps(stock_levels)
        
        # Inventory by category
        category_data = InventoryItem.objects.values('category__name').annotate(
            total_quantity=Count('id')
        ).order_by('-total_quantity')[:5]
        
        context['category_labels'] = json.dumps([item['category__name'] or 'Uncategorized' for item in category_data])
        context['category_values'] = json.dumps([item['total_quantity'] for item in category_data])
        
    elif report_type == 'assets':
        # Get assets with assignment info
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
        
        # Asset status distribution
        status_data = Asset.objects.values('status').annotate(count=Count('id'))
        status_labels = [item['status'].replace('_', ' ').title() for item in status_data]
        status_values = [item['count'] for item in status_data]
        
        context['asset_status_labels'] = json.dumps(status_labels)
        context['asset_status_values'] = json.dumps(status_values)
        
        # Asset assignments over time
        assignment_trend = AssetAssignment.objects.filter(
            assigned_at__gte=last_30_days
        ).annotate(date=TruncDate('assigned_at')).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        trend_dates = [item['date'].strftime('%b %d') for item in assignment_trend]
        trend_volumes = [item['count'] for item in assignment_trend]
        
        context['trend_dates'] = json.dumps(trend_dates)
        context['trend_volumes'] = json.dumps(trend_volumes)
        
    elif report_type == 'requisitions':
        # Get requisitions
        requisitions_queryset = Requisition.objects.select_related('requested_by', 'approved_by').annotate(
            item_count=Count('items', distinct=True)
        )
        context['requisitions'] = requisitions_queryset
        
        # Requisition status distribution
        status_data = Requisition.objects.values('status').annotate(count=Count('id'))
        req_status_labels = [item['status'].title() for item in status_data]
        req_status_values = [item['count'] for item in status_data]
        
        context['req_status_labels'] = json.dumps(req_status_labels)
        context['req_status_values'] = json.dumps(req_status_values)
        
        # Requisitions fulfillment trend
        req_trend = Requisition.objects.filter(
            created_at__gte=last_30_days
        ).annotate(date=TruncDate('created_at')).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        trend_dates = [item['date'].strftime('%b %d') for item in req_trend]
        trend_volumes = [item['count'] for item in req_trend]
        
        context['trend_dates'] = json.dumps(trend_dates)
        context['trend_volumes'] = json.dumps(trend_volumes)
        
    else:
        # Default to transactions
        recent_transactions = InventoryTransaction.objects.select_related(
            'item', 'performed_by'
        ).order_by('-created_at')
        context['recent_transactions'] = recent_transactions
        
        # Transaction types distribution
        trans_type_data = InventoryTransaction.objects.values('transaction_type').annotate(
            count=Count('id')
        )
        trans_type_labels = [item['transaction_type'].replace('_', ' ').title() for item in trans_type_data]
        trans_type_values = [item['count'] for item in trans_type_data]
        
        context['trans_type_labels'] = json.dumps(trans_type_labels)
        context['trans_type_values'] = json.dumps(trans_type_values)
        
        # Transaction volume trend
        trans_trend = InventoryTransaction.objects.filter(
            created_at__gte=last_30_days
        ).annotate(date=TruncDate('created_at')).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        trend_dates = [item['date'].strftime('%b %d') for item in trans_trend]
        trend_volumes = [item['count'] for item in trans_trend]
        
        context['trend_dates'] = json.dumps(trend_dates)
        context['trend_volumes'] = json.dumps(trend_volumes)
    
    return render(request, 'inventorymanagement/pages/reports.html', context)

@login_required
@require_system_access
def settings(request):
    current_system = request.current_system
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
        'current_system': current_system,
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
            hidden_description=f"User '{request.user.username}' updated their avatar",
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
            hidden_description=f"User '{request.user.username}' removed their avatar",
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
        hidden_description=f"User '{user.username}' updated their profile",
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
            hidden_description=f"User '{user.username}' changed their password",
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
            hidden_description=f"User '{user.username}' created their home address",
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
            hidden_description=f"User '{user.username}' updated their home address",
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
                hidden_description=f"User '{user.username}' created their billing address",
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
                hidden_description=f"User '{user.username}' updated their billing address",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
            )

    messages.success(request, "Addresses saved successfully.")
    return redirect("inventorymanagement:settings")

@login_required
@require_system_access
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
            hidden_description=f"User '{request.user.username}' deleted an address",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )

        messages.success(request, "Address deleted successfully.")

    return redirect('inventorymanagement:settings')

@login_required
@require_system_role(['admin', 'superadmin'])
def admin_dashboard(request):
    """Admin dashboard for inventory management system"""
    current_system = request.current_system or 'inventorymanagement'
    
    systems = request.session.get('accessible_systems', [])
    search_query = request.GET.get('search', '').strip()
    
    # Get all users in the system except current user and superusers
    users_in_system = SystemMembership.objects.filter(
        system_name=current_system
    ).values_list('user_id', flat=True)
    

    User = get_user_model()
    users = User.objects.filter(id__in=users_in_system).exclude(id=request.user.id).exclude(is_superuser=True)
    
    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    total_users = users.count()
    
    # Pagination
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page') or 1
    users_page = paginator.get_page(page_number)
    
    # Get or create Terms of Service for the current system
    tos_text = ''
    if current_system:
        try:
            system_record, created = Systems.objects.get_or_create(
                name=current_system,
                defaults={
                    'description': 'Inventory Management System',
                    'terms_of_service': 'Default Terms of Service for Inventory Management System. Please update this content.'
                }
            )
            tos_text = system_record.terms_of_service if system_record.terms_of_service else ''
        except Exception:
            tos_text = ''
    
    # Fetch roles for users in this system
    ROLE_LABELS = {
        'superadmin': 'Super Admin',
        'admin': 'Admin',
        'user': 'User',
    }
    system_roles = {
        m.user_id: (m.system_role, ROLE_LABELS.get(m.system_role, m.system_role.title()))
        for m in SystemMembership.objects.filter(
            system_name=current_system,
            user__in=users_page
        )
    }
    
    context = {
        'systems': systems,
        'current_system': current_system,
        'users': users_page,
        'total_users': total_users,
        'search_query': search_query,
        'tos_text': tos_text,
        'system_roles': system_roles,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'user_list_html': render_to_string(
                'inventorymanagement/partials/admin/_user_access_view.html',
                context,
                request=request
            ),
            'total_users': total_users,
        })
    
    return render(
        request,
        'inventorymanagement/pages/admin/dashboard.html',
        context
    )

@login_required
@require_system_role(['admin', 'superadmin'])
def system_logs(request):
    """View system logs for inventory management"""
    current_system = request.current_system
    
    systems = request.session.get('accessible_systems', [])
    search_query = request.GET.get('search', '').strip()
    
    logs_qs = Logs.objects.filter(system_name=current_system).order_by('-created_at')
    
    if search_query:
        logs_qs = logs_qs.filter(
            Q(user__username__icontains=search_query) |
            Q(action__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(logs_qs, 10)
    page_number = request.GET.get('page') or 1
    logs = paginator.get_page(page_number)
    
    context = {
        'systems': systems,
        'current_system': current_system,
        'logs': logs,
        'total_logs': logs_qs.count(),
        'search_query': search_query,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'logs_list_html': render_to_string(
                'inventorymanagement/partials/admin/_system_logs_table.html',
                context,
                request=request
            ),
        })
    
    return render(
        request,
        'inventorymanagement/pages/admin/system_logs.html',
        context
    )
    search_query = request.GET.get('search', '').strip()
    
    logs = Logs.objects.filter(system_name=current_system).order_by('-created_at')
    
    if search_query:
        logs = logs.filter(
            Q(user__username__icontains=search_query) |
            Q(action__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    context = {
        'systems': systems,
        'current_system': current_system,
        'logs': logs,
        'search_query': search_query,
        'is_superuser': request.user.is_superuser,
    }
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'logs_list_html': render_to_string(
                'inventorymanagement/partials/admin/_system_logs_table.html',
                context,
                request=request
            ),
        })
    
    return render(
        request,
        'inventorymanagement/pages/admin/system_logs.html',
        context
    )

@login_required
@require_system_role(['admin', 'superadmin'])
@require_POST
def deactivate_user(request, user_id):
    """Deactivate a user"""

    if user.is_superuser and user.id == request.user.id:
        messages.error(request, "You cannot deactivate your own account.")
        return redirect('inventorymanagement:admin_dashboard')

    User = get_user_model()
    user = get_object_or_404(User, id=user_id)
    user.is_active = False
    user.save()
    
    Logs.objects.create(
        user=request.user,
        system_name='inventorymanagement',
        action='UPDATE',
        target_model='User',
        target_id=user.id,
        description=f"Deactivated user '{user.username}'",
        hidden_description=f"Admin '{request.user.username}' deactivated user '{user.username}'",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    
    messages.success(request, f"User '{user.username}' has been deactivated.")
    return redirect('inventorymanagement:admin_dashboard')

@login_required
@require_system_role(['admin', 'superadmin'])
@require_POST
def activate_user(request, user_id):
    """Activate a user"""
    User = get_user_model()
    user = get_object_or_404(User, id=user_id)
    user.is_active = True
    user.save()
    
    Logs.objects.create(
        user=request.user,
        system_name='inventorymanagement',
        action='UPDATE',
        target_model='User',
        target_id=user.id,
        description=f"Activated user '{user.username}'",
        hidden_description=f"Admin '{request.user.username}' activated user '{user.username}'",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    
    messages.success(request, f"User '{user.username}' has been activated.")
    return redirect('inventorymanagement:admin_dashboard')

@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_http_methods(["POST"])
def update_tos(request):
    """Update the Terms of Service for the current system"""
    current_system = getattr(request, 'current_system', None) or 'inventorymanagement'
    
    from core.models import Systems
    tos_text = request.POST.get('tos_text', '')
    
    system, created = Systems.objects.get_or_create(
        name=current_system,
        defaults={}
    )
    system.terms_of_service = tos_text
    system.save()
    
    Logs.objects.create(
        user=request.user,
        system_name=current_system,
        action='UPDATE',
        target_model='Systems',
        target_id=system.id,
        description=f"Updated Terms of Service for system '{current_system}'",
        hidden_description=f"Admin '{request.user.username}' updated Terms of Service for system '{current_system}'",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    
    messages.success(request, "Terms of Service updated successfully.")
    return redirect("inventorymanagement:admin_dashboard")

@login_required
@require_system_role(['admin', 'superadmin'])
def manage_user_access(request, user_id):
    """Manage user access levels within the current system"""
    if request.method == 'POST':
        current_system = request.current_system
        User = get_user_model()
        user = get_object_or_404(User, id=user_id)
        
        new_role = request.POST.get('system_role', 'user')
        
        # Update or create system membership
        membership, created = SystemMembership.objects.get_or_create(
            user=user,
            system_name=current_system,
            defaults={'system_role': new_role}
        )
        
        if not created:
            old_role = membership.system_role
            membership.system_role = new_role
            membership.save()
            
            Logs.objects.create(
                user=request.user,
                system_name=current_system,
                action='UPDATE',
                target_model='SystemMembership',
                target_id=membership.id,
                description=f"Changed role for user '{user.username}' from {old_role} to {new_role}",
                hidden_description=f"Admin '{request.user.username}' changed role for user '{user.username}' from {old_role} to {new_role}",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
            )
            messages.success(request, f"User '{user.username}' role updated to {new_role}.")
        else:
            Logs.objects.create(
                user=request.user,
                system_name=current_system,
                action='CREATE',
                target_model='SystemMembership',
                target_id=membership.id,
                description=f"Added user '{user.username}' with role {new_role}",
                hidden_description=f"Admin '{request.user.username}' added user '{user.username}' with role {new_role}",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
            )
            messages.success(request, f"User '{user.username}' added to system with role {new_role}.")
    
    return redirect("inventorymanagement:admin_dashboard")
    """
    Update the Terms of Service for the current system.
    """

    current_system = request.current_system  # set by middleware

    # Get system membership for the current user
    system_membership = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system
    ).first()

    allowed_roles = ['superadmin', 'admin']

    # Allow if superuser OR membership role is allowed
    if not (request.user.is_superuser or (system_membership and system_membership.system_role in allowed_roles)):
        return render(request, '404.html', status=404)

    tos_text = request.POST.get('tos_text', '')

    system = Systems.objects.get(name=current_system)
    system.terms_of_service = tos_text
    system.save()

    Logs.objects.create(
        user=request.user,
        system_name=current_system,
        action='UPDATE',
        target_model='Systems',
        target_id=system.id,
        description=f"Updated Terms of Service for system '{current_system}'",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )

    messages.success(request, "Terms of Service updated successfully.")
    return redirect("projectmanagement:pm_admin_dashboard") 


# ===================== INVENTORY ITEM MANAGEMENT VIEWS =====================

@login_required
@require_system_access
def create_inventory_item(request):
    """Create a new inventory item"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        category_id = request.POST.get('category', '')
        unit = request.POST.get('unit', '').strip()
        quantity = request.POST.get('quantity', 0)
        low_stock_threshold = request.POST.get('low_stock_threshold', 5)
        description = request.POST.get('description', '').strip()
        
        # Validation
        if not name:
            return JsonResponse({'success': False, 'error': 'Item name is required'})
        if not category_id:
            return JsonResponse({'success': False, 'error': 'Category is required'})
        if not unit:
            return JsonResponse({'success': False, 'error': 'Unit is required'})
        
        try:
            category = InventoryCategory.objects.get(id=category_id)
            
            item = InventoryItem.objects.create(
                name=name,
                category=category,
                unit=unit,
                quantity=int(quantity),
                low_stock_threshold=int(low_stock_threshold),
                description=description
            )
            
            # Create transaction record for initial quantity
            if int(quantity) > 0:
                InventoryTransaction.objects.create(
                    item=item,
                    transaction_type='ADJUST',
                    quantity=int(quantity),
                    performed_by=request.user,
                    remarks=f"Initial quantity set during item creation"
                )
            
            # Log the action
            Logs.objects.create(
                user=request.user,
                system_name='inventorymanagement',
                action='CREATE',
                target_model='InventoryItem',
                target_id=item.id,
                description=f"Created inventory item '{item.name}'",
                hidden_description=f"User '{request.user.username}' created inventory item '{item.name}'",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
            )
            
            messages.success(request, f"Inventory item '{item.name}' created successfully.")
            return JsonResponse({'success': True, 'item_id': str(item.id)})
        except InventoryCategory.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Category not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    # GET request - show modal
    categories = InventoryCategory.objects.filter(is_active=True)
    return render(request, 'inventorymanagement/modals/add_item_modal.html', {
        'categories': categories
    })


@login_required
@require_system_access
def edit_inventory_item(request, item_id):
    """Edit an inventory item"""
    item = get_object_or_404(InventoryItem, id=item_id)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        category_id = request.POST.get('category', '')
        unit = request.POST.get('unit', '').strip()
        quantity = request.POST.get('quantity', 0)
        low_stock_threshold = request.POST.get('low_stock_threshold', 5)
        description = request.POST.get('description', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        
        # Validation
        if not name:
            return JsonResponse({'success': False, 'error': 'Item name is required'})
        if not category_id:
            return JsonResponse({'success': False, 'error': 'Category is required'})
        if not unit:
            return JsonResponse({'success': False, 'error': 'Unit is required'})
        
        try:
            category = InventoryCategory.objects.get(id=category_id)
            
            old_quantity = item.quantity
            new_quantity = int(quantity)
            
            item.name = name
            item.category = category
            item.unit = unit
            item.quantity = new_quantity
            item.low_stock_threshold = int(low_stock_threshold)
            item.description = description
            item.is_active = is_active
            item.save()
            
            # Create transaction record if quantity changed
            quantity_diff = new_quantity - old_quantity
            if quantity_diff != 0:
                InventoryTransaction.objects.create(
                    item=item,
                    transaction_type='ADJUST',
                    quantity=quantity_diff,
                    performed_by=request.user,
                    remarks=f"Quantity adjusted from {old_quantity} to {new_quantity}"
                )
            
            # Log the action
            Logs.objects.create(
                user=request.user,
                system_name='inventorymanagement',
                action='UPDATE',
                target_model='InventoryItem',
                target_id=item.id,
                description=f"Updated inventory item '{item.name}'",
                hidden_description=f"User '{request.user.username}' updated inventory item '{item.name}'",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
            )
            
            messages.success(request, f"Inventory item '{item.name}' updated successfully.")
            return JsonResponse({'success': True, 'item_id': str(item.id)})
        except InventoryCategory.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Category not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    # GET request - show modal with current data
    categories = InventoryCategory.objects.filter(is_active=True)
    return render(request, 'inventorymanagement/modals/edit_item_modal.html', {
        'item': item,
        'categories': categories
    })


@login_required
@require_system_access
@require_POST
def delete_inventory_item(request, item_id):
    """Delete an inventory item"""
    item = get_object_or_404(InventoryItem, id=item_id)
    item_name = item.name
    
    try:
        item_id_str = str(item.id)
        
        # Create transaction record for item disposal
        if item.quantity > 0:
            InventoryTransaction.objects.create(
                item=item,
                transaction_type='DISPOSE',
                quantity=-item.quantity,
                performed_by=request.user,
                remarks=f"Item disposed (deleted from system)"
            )
        
        item.delete()
        
        # Log the action
        Logs.objects.create(
            user=request.user,
            system_name='inventorymanagement',
            action='DELETE',
            target_model='InventoryItem',
            target_id=item_id_str,
            description=f"Deleted inventory item '{item_name}'",
            hidden_description=f"User '{request.user.username}' deleted inventory item '{item_name}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        
        messages.success(request, f"Inventory item '{item_name}' deleted successfully.")
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_system_access
def create_inventory_category(request):
    """Create a new inventory category"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        
        # Validation
        if not name:
            return JsonResponse({'success': False, 'error': 'Category name is required'})
        
        # Check if category already exists
        if InventoryCategory.objects.filter(name__iexact=name).exists():
            return JsonResponse({'success': False, 'error': 'Category already exists'})
        
        try:
            category = InventoryCategory.objects.create(
                name=name,
                description=description
            )
            
            # Log the action
            Logs.objects.create(
                user=request.user,
                system_name='inventorymanagement',
                action='CREATE',
                target_model='InventoryCategory',
                target_id=category.id,
                description=f"Created inventory category '{category.name}'",
                hidden_description=f"User '{request.user.username}' created inventory category '{category.name}'",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
            )
            
            messages.success(request, f"Category '{category.name}' created successfully.")
            return JsonResponse({'success': True, 'category_id': str(category.id)})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    # GET request - show modal
    return render(request, 'inventorymanagement/modals/add_category_modal.html')


@login_required
@require_system_access
@require_POST
def delete_inventory_category(request, category_id):
    """Delete an inventory category"""
    category = get_object_or_404(InventoryCategory, id=category_id)
    
    # Check if category has items
    if category.items.exists():
        return JsonResponse({'success': False, 'error': 'Cannot delete category with existing items'})
    
    category_name = category.name
    
    try:
        category_id_str = str(category.id)
        category.delete()
        
        # Log the action
        Logs.objects.create(
            user=request.user,
            system_name='inventorymanagement',
            action='DELETE',
            target_model='InventoryCategory',
            target_id=category_id_str,
            description=f"Deleted inventory category '{category_name}'",
            hidden_description=f"User '{request.user.username}' deleted inventory category '{category_name}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        
        messages.success(request, f"Category '{category_name}' deleted successfully.")
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_system_access
def export_report(request):
    """Export reports data to CSV based on report type with chart data"""
    import csv
    from django.http import HttpResponse
    from django.db.models.functions import TruncDate
    from datetime import timedelta
    
    report_type = request.GET.get('report', 'transactions').strip().lower()
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{report_type}_report.csv"'
    
    writer = csv.writer(response)
    
    if report_type == 'inventory':
        # Summary statistics
        writer.writerow(['INVENTORY SUMMARY STATISTICS'])
        writer.writerow(['Total Items', InventoryItem.objects.count()])
        writer.writerow(['Low Stock Items', InventoryItem.objects.filter(quantity__lte=F('low_stock_threshold')).count()])
        writer.writerow([])
        
        # Inventory by Category (Chart Data)
        writer.writerow(['INVENTORY BY CATEGORY'])
        writer.writerow(['Category', 'Total Items'])
        category_data = InventoryItem.objects.values('category__name').annotate(
            total=Count('id')
        ).order_by('-total')
        for item in category_data:
            writer.writerow([item['category__name'] or 'Uncategorized', item['total']])
        writer.writerow([])
        
        # Detailed inventory items
        writer.writerow(['DETAILED INVENTORY ITEMS'])
        writer.writerow(['Item Name', 'Category', 'Quantity', 'Unit', 'Low Stock Threshold', 'Status', 'Last Updated'])
        inventories = InventoryItem.objects.select_related('category').all()
        for item in inventories:
            writer.writerow([
                item.name,
                item.category.name if item.category else 'Uncategorized',
                item.quantity,
                item.unit,
                item.low_stock_threshold,
                'Active' if item.is_active else 'Inactive',
                item.updated_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
    
    elif report_type == 'assets':
        # Summary statistics
        writer.writerow(['ASSET SUMMARY STATISTICS'])
        writer.writerow(['Total Assets', Asset.objects.count()])
        writer.writerow(['Available', Asset.objects.filter(status='AVAILABLE').count()])
        writer.writerow(['Assigned', Asset.objects.filter(status='ASSIGNED').count()])
        writer.writerow(['Under Repair', Asset.objects.filter(status='UNDER_REPAIR').count()])
        writer.writerow(['Retired', Asset.objects.filter(status='RETIRED').count()])
        writer.writerow([])
        
        # Asset Status Distribution (Chart Data)
        writer.writerow(['ASSET STATUS DISTRIBUTION'])
        writer.writerow(['Status', 'Count'])
        status_data = Asset.objects.values('status').annotate(count=Count('id'))
        for item in status_data:
            writer.writerow([item['status'].replace('_', ' ').title(), item['count']])
        writer.writerow([])
        
        # Asset Assignments Trend (Chart Data)
        writer.writerow(['ASSET ASSIGNMENTS TREND (LAST 30 DAYS)'])
        writer.writerow(['Date', 'Assignments'])
        last_30_days = timezone.now() - timedelta(days=30)
        assignment_trend = AssetAssignment.objects.filter(
            assigned_at__gte=last_30_days
        ).annotate(date=TruncDate('assigned_at')).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        for item in assignment_trend:
            writer.writerow([item['date'].strftime('%Y-%m-%d'), item['count']])
        writer.writerow([])
        
        # Detailed assets list
        writer.writerow(['DETAILED ASSETS LIST'])
        writer.writerow(['Asset Code', 'Name', 'Category', 'Description', 'Status', 'Created At', 'Assigned To'])
        assets = Asset.objects.select_related('category').prefetch_related('assignments')
        for asset in assets:
            latest_assignment = asset.assignments.filter(returned_at__isnull=True).first()
            assigned_to = latest_assignment.assigned_to.username if latest_assignment else 'Unassigned'
            writer.writerow([
                asset.asset_code,
                asset.name,
                asset.category.name if asset.category else 'Uncategorized',
                asset.description or '',
                asset.get_status_display(),
                asset.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                assigned_to
            ])
    
    elif report_type == 'requisitions':
        # Summary statistics
        writer.writerow(['REQUISITION SUMMARY STATISTICS'])
        writer.writerow(['Total Requisitions', Requisition.objects.count()])
        writer.writerow(['Pending', Requisition.objects.filter(status='PENDING').count()])
        writer.writerow(['Approved', Requisition.objects.filter(status='APPROVED').count()])
        writer.writerow(['Rejected', Requisition.objects.filter(status='REJECTED').count()])
        writer.writerow(['Issued', Requisition.objects.filter(status='ISSUED').count()])
        writer.writerow([])
        
        # Requisition Status Distribution (Chart Data)
        writer.writerow(['REQUISITION STATUS DISTRIBUTION'])
        writer.writerow(['Status', 'Count'])
        status_data = Requisition.objects.values('status').annotate(count=Count('id'))
        for item in status_data:
            writer.writerow([item['status'].title(), item['count']])
        writer.writerow([])
        
        # Requisitions Trend (Chart Data)
        writer.writerow(['REQUISITIONS TREND (LAST 30 DAYS)'])
        writer.writerow(['Date', 'Requisitions'])
        last_30_days = timezone.now() - timedelta(days=30)
        req_trend = Requisition.objects.filter(
            created_at__gte=last_30_days
        ).annotate(date=TruncDate('created_at')).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        for item in req_trend:
            writer.writerow([item['date'].strftime('%Y-%m-%d'), item['count']])
        writer.writerow([])
        
        # Detailed requisitions list
        writer.writerow(['DETAILED REQUISITIONS LIST'])
        writer.writerow(['Requisition ID', 'Requested By', 'Purpose', 'Status', 'Item Count', 'Requested Date', 'Approved By', 'Approved Date'])
        requisitions = Requisition.objects.select_related('requested_by', 'approved_by').annotate(
            item_count=Count('items', distinct=True)
        )
        for req in requisitions:
            writer.writerow([
                str(req.id),
                req.requested_by.username,
                req.purpose,
                req.status,
                req.item_count,
                req.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                req.approved_by.username if req.approved_by else 'Pending',
                req.approved_at.strftime('%Y-%m-%d %H:%M:%S') if req.approved_at else ''
            ])
    
    else:  # transactions
        # Summary statistics
        writer.writerow(['TRANSACTION SUMMARY STATISTICS'])
        writer.writerow(['Total Transactions', InventoryTransaction.objects.count()])
        writer.writerow([])
        
        # Transaction Types Distribution (Chart Data)
        writer.writerow(['TRANSACTION TYPES DISTRIBUTION'])
        writer.writerow(['Type', 'Count'])
        trans_type_data = InventoryTransaction.objects.values('transaction_type').annotate(
            count=Count('id')
        )
        for item in trans_type_data:
            writer.writerow([item['transaction_type'].replace('_', ' ').title(), item['count']])
        writer.writerow([])
        
        # Transaction Volume Trend (Chart Data)
        writer.writerow(['TRANSACTION VOLUME TREND (LAST 30 DAYS)'])
        writer.writerow(['Date', 'Transactions'])
        last_30_days = timezone.now() - timedelta(days=30)
        trans_trend = InventoryTransaction.objects.filter(
            created_at__gte=last_30_days
        ).annotate(date=TruncDate('created_at')).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        for item in trans_trend:
            writer.writerow([item['date'].strftime('%Y-%m-%d'), item['count']])
        writer.writerow([])
        
        # Detailed transactions list
        writer.writerow(['DETAILED TRANSACTIONS LIST'])
        writer.writerow(['Date', 'Item', 'Type', 'Quantity', 'Performed By', 'Remarks'])
        transactions = InventoryTransaction.objects.select_related('item', 'performed_by').order_by('-created_at')
        for trans in transactions:
            writer.writerow([
                trans.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                trans.item.name,
                trans.transaction_type,
                trans.quantity,
                trans.performed_by.username,
                trans.remarks or ''
            ])
    
    # Log the action
    Logs.objects.create(
        user=request.user,
        system_name='inventorymanagement',
        action='EXPORT',
        target_model='Reports',
        description=f"Exported {report_type.title()} report",
        hidden_description=f"User '{request.user.username}' exported {report_type} report",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    
    return response

@login_required
@require_system_access
def export_inventory(request):
    """Export inventory items to CSV"""
    items = InventoryItem.objects.select_related('category').all()
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="inventory_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Item Name', 'Category', 'Unit', 'Quantity', 'Low Stock Threshold', 'Status', 'Last Updated'])
    
    for item in items:
        writer.writerow([
            item.name,
            item.category.name,
            item.unit,
            item.quantity,
            item.low_stock_threshold,
            'Active' if item.is_active else 'Inactive',
            item.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    # Log the action
    Logs.objects.create(
        user=request.user,
        system_name='inventorymanagement',
        action='EXPORT',
        target_model='InventoryItem',
        description=f"Exported {items.count()} inventory items",
        hidden_description=f"User '{request.user.username}' exported inventory data",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    
    return response


@login_required
@require_system_access
def get_categories(request):
    """Get all active categories as JSON"""
    categories = InventoryCategory.objects.filter(is_active=True).values('id', 'name')
    return JsonResponse({'categories': list(categories)})


# ===================== REQUISITION MANAGEMENT VIEWS =====================

@login_required
@require_system_access
def create_requisition(request):
    """Create a new requisition"""
    if request.method == 'POST':
        purpose = request.POST.get('purpose', '').strip()
        borrower_first_name = request.POST.get('borrower_first_name', '').strip()
        borrower_middle_initial = request.POST.get('borrower_middle_initial', '').strip()
        borrower_last_name = request.POST.get('borrower_last_name', '').strip()
        borrower_address = request.POST.get('borrower_address', '').strip()
        borrower_contact_no = request.POST.get('borrower_contact_no', '').strip()
        borrower_position = request.POST.get('borrower_position', '').strip()
        event_name = request.POST.get('event_name', '').strip()
        date_borrowed = request.POST.get('date_borrowed', '').strip() or None
        date_returned = request.POST.get('date_returned', '').strip() or None
        time_borrowed = request.POST.get('time_borrowed', '').strip() or None
        time_returned = request.POST.get('time_returned', '').strip() or None
        items_json = request.POST.get('items', '[]')
        
        try:
            items_data = json.loads(items_json)
            
            if not items_data:
                return JsonResponse({'success': False, 'error': 'At least one item is required'})
            
            # Create requisition
            requisition = Requisition.objects.create(
                requested_by=request.user,
                purpose=purpose,
                borrower_first_name=borrower_first_name,
                borrower_middle_initial=borrower_middle_initial,
                borrower_last_name=borrower_last_name,
                borrower_address=borrower_address,
                borrower_contact_no=borrower_contact_no,
                borrower_position=borrower_position,
                event_name=event_name,
                date_borrowed=date_borrowed,
                date_returned=date_returned,
                time_borrowed=time_borrowed,
                time_returned=time_returned,
                status='PENDING'
            )
            
            # Add items to requisition
            for item_data in items_data:
                try:
                    inventory_item = InventoryItem.objects.get(id=item_data['item_id'])
                    RequisitionItem.objects.create(
                        requisition=requisition,
                        inventory_item=inventory_item,
                        quantity_requested=int(item_data['quantity'])
                    )
                except (InventoryItem.DoesNotExist, KeyError, ValueError):
                    continue
            
            # Log the action
            Logs.objects.create(
                user=request.user,
                system_name='inventorymanagement',
                action='CREATE',
                target_model='Requisition',
                target_id=str(requisition.id),
                description=f"Created new requisition with {len(items_data)} items",
                hidden_description=f"User '{request.user.username}' created requisition {requisition.id}",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
            )
            
            return JsonResponse({
                'success': True,
                'requisition_id': str(requisition.id),
                'message': 'Requisition created successfully'
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    # GET request - return form
    categories = InventoryCategory.objects.filter(is_active=True)
    items = InventoryItem.objects.filter(is_active=True).select_related('category')
    return JsonResponse({
        'categories': [{'id': str(c.id), 'name': c.name} for c in categories],
        'items': [
            {
                'id': str(i.id),
                'name': i.name,
                'category': i.category.name,
                'description': i.description,
            }
            for i in items
        ]
    })


@login_required
@require_system_access
def view_requisition(request, requisition_id):
    """View requisition details"""
    requisition = get_object_or_404(Requisition, id=requisition_id)
    items = requisition.items.select_related('inventory_item')
    
    # Check if user is admin
    current_system = request.current_system
    is_admin = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system,
        system_role__in=['admin', 'superadmin']
    ).exists()
    
    return render(request, 'inventorymanagement/pages/requisition_detail.html', {
        'requisition': requisition,
        'items': items,
        'is_admin': is_admin,
    })


@login_required
@require_system_access
def edit_requisition(request, requisition_id):
    """Edit a requisition"""
    requisition = get_object_or_404(Requisition, id=requisition_id)
    
    # Only requester or admins can edit
    current_system = request.current_system
    is_admin = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system,
        system_role__in=['admin', 'superadmin']
    ).exists()
    
    if requisition.requested_by != request.user and not is_admin:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    if request.method == 'POST':
        purpose = request.POST.get('purpose', '').strip()
        
        requisition.purpose = purpose
        requisition.save()
        
        # Log the action
        Logs.objects.create(
            user=request.user,
            system_name='inventorymanagement',
            action='UPDATE',
            target_model='Requisition',
            target_id=str(requisition.id),
            description=f"Updated requisition {requisition.id}",
            hidden_description=f"User '{request.user.username}' updated requisition {requisition.id}",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Requisition updated successfully'
        })
    
    return JsonResponse({'success': False, 'error': 'POST method required'}, status=405)


@login_required
@require_system_access
@require_POST
def delete_requisition(request, requisition_id):
    """Delete a requisition"""
    requisition = get_object_or_404(Requisition, id=requisition_id)
    
    # Only requester or admins can delete
    current_system = request.current_system
    is_admin = SystemMembership.objects.filter(
        user=request.user,
        system_name=current_system,
        system_role__in=['admin', 'superadmin']
    ).exists()
    
    if requisition.requested_by != request.user and not is_admin:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    try:
        req_id = str(requisition.id)
        requisition.delete()
        
        # Log the action
        Logs.objects.create(
            user=request.user,
            system_name='inventorymanagement',
            action='DELETE',
            target_model='Requisition',
            target_id=req_id,
            description=f"Deleted requisition {req_id}",
            hidden_description=f"User '{request.user.username}' deleted requisition {req_id}",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Requisition deleted successfully'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
def approve_requisition(request, requisition_id):
    """Approve a requisition (admin only)"""
    requisition = get_object_or_404(Requisition, id=requisition_id)
    
    if request.method == 'POST':
        requisition.status = 'APPROVED'
        requisition.approved_by = request.user
        requisition.approved_at = timezone.now()
        requisition.save()
        
        # Log the action
        Logs.objects.create(
            user=request.user,
            system_name='inventorymanagement',
            action='UPDATE',
            target_model='Requisition',
            target_id=str(requisition.id),
            description=f"Approved requisition {requisition.id}",
            hidden_description=f"Admin '{request.user.username}' approved requisition {requisition.id}",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        
        messages.success(request, 'Requisition approved successfully')
        return redirect('inventorymanagement:requisitions')
    
    return redirect('inventorymanagement:requisitions')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
def reject_requisition(request, requisition_id):
    """Reject a requisition (admin only)"""
    requisition = get_object_or_404(Requisition, id=requisition_id)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        
        requisition.status = 'REJECTED'
        requisition.purpose = f"{requisition.purpose}\n\nREJECTION REASON: {reason}" if reason else requisition.purpose
        requisition.save()
        
        # Log the action
        Logs.objects.create(
            user=request.user,
            system_name='inventorymanagement',
            action='UPDATE',
            target_model='Requisition',
            target_id=str(requisition.id),
            description=f"Rejected requisition {requisition.id}",
            hidden_description=f"Admin '{request.user.username}' rejected requisition {requisition.id}: {reason}",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        
        messages.success(request, 'Requisition rejected')
        return redirect('inventorymanagement:requisitions')
    
    return redirect('inventorymanagement:requisitions')


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
def issue_requisition(request, requisition_id):
    """Issue items from an approved requisition (admin only)"""
    requisition = get_object_or_404(Requisition, id=requisition_id)
    
    if requisition.status != 'APPROVED':
        messages.error(request, 'Only approved requisitions can be issued')
        return redirect('inventorymanagement:requisitions')
    
    if request.method == 'POST':
        try:
            items = requisition.items.all()
            
            for req_item in items:
                quantity_to_issue = req_item.quantity_requested - req_item.quantity_issued
                
                # Check if sufficient stock
                if req_item.inventory_item.quantity < quantity_to_issue:
                    messages.error(request, f"Insufficient stock for {req_item.inventory_item.name}")
                    return redirect('inventorymanagement:requisitions')
                
                # Deduct from inventory and create transaction
                req_item.inventory_item.quantity -= quantity_to_issue
                req_item.inventory_item.save()
                
                req_item.quantity_issued = req_item.quantity_requested
                req_item.save()
                
                # Create transaction record
                InventoryTransaction.objects.create(
                    item=req_item.inventory_item,
                    transaction_type='ISSUE',
                    quantity=-quantity_to_issue,
                    performed_by=request.user,
                    remarks=f"Issued from requisition {requisition.id}"
                )
            
            requisition.status = 'ISSUED'
            requisition.save()
            
            # Log the action
            Logs.objects.create(
                user=request.user,
                system_name='inventorymanagement',
                action='UPDATE',
                target_model='Requisition',
                target_id=str(requisition.id),
                description=f"Issued items from requisition {requisition.id}",
                hidden_description=f"Admin '{request.user.username}' issued items from requisition {requisition.id}",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
            )
            
            messages.success(request, 'Items issued successfully')
            return redirect('inventorymanagement:requisitions')
        except Exception as e:
            import traceback
            traceback.print_exc()
            messages.error(request, f'Error issuing items: {str(e)}')
            return redirect('inventorymanagement:requisitions')
    
    return redirect('inventorymanagement:requisitions')


@login_required
@require_system_access
def get_requisition_items(request, requisition_id):
    """Get items in a requisition as JSON"""
    requisition = get_object_or_404(Requisition, id=requisition_id)
    items = requisition.items.select_related('inventory_item').values(
        'id',
        'inventory_item__id',
        'inventory_item__name',
        'quantity_requested',
        'quantity_issued'
    )
    
    return JsonResponse({'items': list(items)})


@login_required
@require_system_access
def export_requisitions(request):
    """Export requisitions to CSV"""
    import csv
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="requisitions.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Requisition ID', 'Requested By', 'Status', 'Items Count', 'Purpose', 'Requested Date', 'Approved By', 'Approved Date'])
    
    requisitions = Requisition.objects.select_related('requested_by', 'approved_by').all()
    
    for req in requisitions:
        item_count = req.items.count()
        writer.writerow([
            str(req.id),
            req.requested_by.get_full_name() or req.requested_by.username,
            req.get_status_display(),
            item_count,
            req.purpose[:50],
            req.created_at.strftime('%Y-%m-%d %H:%M'),
            (req.approved_by.get_full_name() or req.approved_by.username) if req.approved_by else '-',
            req.approved_at.strftime('%Y-%m-%d %H:%M') if req.approved_at else '-'
        ])
    
    # Log the action
    Logs.objects.create(
        user=request.user,
        system_name='inventorymanagement',
        action='EXPORT',
        target_model='Requisition',
        description=f"Exported {requisitions.count()} requisitions",
        hidden_description=f"User '{request.user.username}' exported requisition data",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    
    return response


# ===================== ASSET MANAGEMENT VIEWS =====================

@login_required
@require_system_access
def create_asset(request):
    """Create a new asset"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        asset_code = request.POST.get('asset_code', '').strip()
        category_id = request.POST.get('category', '').strip()
        description = request.POST.get('description', '').strip()
        
        if not name or not asset_code or not category_id:
            return JsonResponse({'success': False, 'error': 'Name, asset code, and category are required'})
        
        # Check if asset code already exists
        if Asset.objects.filter(asset_code__iexact=asset_code).exists():
            return JsonResponse({'success': False, 'error': 'Asset code already exists'})
        
        try:
            category = get_object_or_404(AssetCategory, id=category_id)
            asset = Asset.objects.create(
                name=name,
                asset_code=asset_code,
                category=category,
                description=description
            )
            
            # Log the action
            Logs.objects.create(
                user=request.user,
                system_name='inventorymanagement',
                action='CREATE',
                target_model='Asset',
                target_id=asset.id,
                description=f"Created asset '{asset.asset_code}' - {asset.name}",
                hidden_description=f"User '{request.user.username}' created asset '{asset.asset_code}'",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
            )
            
            messages.success(request, f"Asset '{asset.asset_code}' created successfully.")
            return JsonResponse({'success': True, 'asset_id': str(asset.id)})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return render(request, 'inventorymanagement/modals/add_asset_modal.html')


@login_required
@require_system_access
def edit_asset(request, asset_id):
    """Edit an existing asset"""
    asset = get_object_or_404(Asset, id=asset_id)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        asset_code = request.POST.get('asset_code', '').strip()
        category_id = request.POST.get('category', '').strip()
        description = request.POST.get('description', '').strip()
        status = request.POST.get('status', '').strip()
        
        if not name or not asset_code or not category_id:
            return JsonResponse({'success': False, 'error': 'Name, asset code, and category are required'})
        
        # Check if new asset code exists (excluding current asset)
        if Asset.objects.filter(asset_code__iexact=asset_code).exclude(id=asset_id).exists():
            return JsonResponse({'success': False, 'error': 'Asset code already exists'})
        
        try:
            asset.name = name
            asset.asset_code = asset_code
            asset.category = get_object_or_404(AssetCategory, id=category_id)
            asset.description = description
            if status:
                asset.status = status
            asset.save()
            
            # Log the action
            Logs.objects.create(
                user=request.user,
                system_name='inventorymanagement',
                action='UPDATE',
                target_model='Asset',
                target_id=asset.id,
                description=f"Updated asset '{asset.asset_code}' - {asset.name}",
                hidden_description=f"User '{request.user.username}' updated asset '{asset.asset_code}'",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
            )
            
            messages.success(request, f"Asset '{asset.asset_code}' updated successfully.")
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return render(request, 'inventorymanagement/modals/edit_asset_modal.html', {'asset': asset})


@login_required
@require_system_access
@require_POST
def delete_asset(request, asset_id):
    """Delete an asset"""
    asset = get_object_or_404(Asset, id=asset_id)
    asset_code = asset.asset_code
    
    try:
        asset_id_str = str(asset.id)
        asset.delete()
        
        # Log the action
        Logs.objects.create(
            user=request.user,
            system_name='inventorymanagement',
            action='DELETE',
            target_model='Asset',
            target_id=asset_id_str,
            description=f"Deleted asset '{asset_code}'",
            hidden_description=f"User '{request.user.username}' deleted asset '{asset_code}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        
        messages.success(request, f"Asset '{asset_code}' deleted successfully.")
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_system_access
def create_asset_category(request):
    """Create a new asset category"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        
        if not name:
            return JsonResponse({'success': False, 'error': 'Category name is required'})
        
        # Check if category already exists
        if AssetCategory.objects.filter(name__iexact=name).exists():
            return JsonResponse({'success': False, 'error': 'Category already exists'})
        
        try:
            category = AssetCategory.objects.create(name=name)
            
            # Log the action
            Logs.objects.create(
                user=request.user,
                system_name='inventorymanagement',
                action='CREATE',
                target_model='AssetCategory',
                target_id=category.id,
                description=f"Created asset category '{category.name}'",
                hidden_description=f"User '{request.user.username}' created asset category '{category.name}'",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
            )
            
            messages.success(request, f"Category '{category.name}' created successfully.")
            return JsonResponse({'success': True, 'category_id': str(category.id)})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return render(request, 'inventorymanagement/modals/add_asset_category_modal.html')


@login_required
@require_system_access
@require_POST
def delete_asset_category(request, category_id):
    """Delete an asset category"""
    category = get_object_or_404(AssetCategory, id=category_id)
    
    # Check if category has assets
    if category.assets.exists():
        return JsonResponse({'success': False, 'error': 'Cannot delete category with existing assets'})
    
    category_name = category.name
    
    try:
        category_id_str = str(category.id)
        category.delete()
        
        # Log the action
        Logs.objects.create(
            user=request.user,
            system_name='inventorymanagement',
            action='DELETE',
            target_model='AssetCategory',
            target_id=category_id_str,
            description=f"Deleted asset category '{category_name}'",
            hidden_description=f"User '{request.user.username}' deleted asset category '{category_name}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        
        messages.success(request, f"Category '{category_name}' deleted successfully.")
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_system_access
def assign_asset(request, asset_id):
    """Assign an asset to a user"""
    asset = get_object_or_404(Asset, id=asset_id)
    
    if request.method == 'POST':
        user_id = request.POST.get('user', '').strip()
        remarks = request.POST.get('remarks', '').strip()
        
        if not user_id:
            return JsonResponse({'success': False, 'error': 'User is required'})
        
        try:
            User = get_user_model()
            assigned_user = get_object_or_404(User, id=user_id)
            
            # Create assignment
            assignment = AssetAssignment.objects.create(
                asset=asset,
                assigned_to=assigned_user,
                remarks=remarks
            )
            
            # Update asset status
            asset.status = 'ASSIGNED'
            asset.save()
            
            # Log the action
            Logs.objects.create(
                user=request.user,
                system_name='inventorymanagement',
                action='CREATE',
                target_model='AssetAssignment',
                target_id=assignment.id,
                description=f"Assigned asset '{asset.asset_code}' to '{assigned_user.username}'",
                hidden_description=f"User '{request.user.username}' assigned asset '{asset.asset_code}' to '{assigned_user.username}'",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
            )
            
            messages.success(request, f"Asset assigned to {assigned_user.get_full_name() or assigned_user.username}")
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return render(request, 'inventorymanagement/modals/assign_asset_modal.html', {'asset': asset})


@login_required
@require_system_access
@require_POST
def return_asset(request, asset_id):
    """Return an assigned asset"""
    asset = get_object_or_404(Asset, id=asset_id)
    
    try:
        # Get the active assignment
        assignment = asset.assignments.filter(returned_at__isnull=True).first()
        
        if not assignment:
            return JsonResponse({'success': False, 'error': 'Asset is not currently assigned'})
        
        # Mark assignment as returned
        assignment.returned_at = timezone.now()
        assignment.save()
        
        # Update asset status
        asset.status = 'AVAILABLE'
        asset.save()
        
        # Log the action
        Logs.objects.create(
            user=request.user,
            system_name='inventorymanagement',
            action='UPDATE',
            target_model='AssetAssignment',
            target_id=assignment.id,
            description=f"Returned asset '{asset.asset_code}' from '{assignment.assigned_to.username}'",
            hidden_description=f"User '{request.user.username}' marked asset '{asset.asset_code}' as returned",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        
        messages.success(request, f"Asset '{asset.asset_code}' returned successfully.")
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_system_access
def export_assets(request):
    """Export assets to CSV"""
    import csv
    from django.http import HttpResponse
    
    status_filter = request.GET.get('status', '').strip()
    assets = Asset.objects.select_related('category').all()
    
    if status_filter:
        assets = assets.filter(status=status_filter)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="assets_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Asset Code', 'Name', 'Category', 'Status', 'Assigned To', 'Created Date'])
    
    for asset in assets:
        latest_assignment = asset.assignments.filter(returned_at__isnull=True).first()
        assigned_to = latest_assignment.assigned_to.get_full_name() if latest_assignment else 'Not Assigned'
        
        writer.writerow([
            asset.asset_code,
            asset.name,
            asset.category.name,
            asset.get_status_display(),
            assigned_to,
            asset.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    # Log the action
    Logs.objects.create(
        user=request.user,
        system_name='inventorymanagement',
        action='EXPORT',
        target_model='Asset',
        description=f"Exported {assets.count()} assets",
        hidden_description=f"User '{request.user.username}' exported asset data",
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
    )
    
    return response


@login_required
@require_system_access
def get_asset_categories(request):
    """Get all asset categories as JSON"""
    categories = AssetCategory.objects.all().values('id', 'name')
    return JsonResponse({'categories': list(categories)})


@login_required
@login_required
@require_system_access
def get_system_members(request):
    """Get all system members (users with SystemMembership) as JSON"""
    try:
        current_system = request.session.get('current_system', 'core')
        members = SystemMembership.objects.filter(
            system_name=current_system
        ).select_related('user')
        
        users = []
        for member in members:
            user = member.user
            full_name = f"{user.first_name} {user.last_name}".strip()
            users.append({
                'id': str(user.id),
                'username': user.username,
                'full_name': full_name or user.username
            })
        
        return JsonResponse({'users': users})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_system_access
def get_asset_maintenance(request, asset_id):
    """Get maintenance records for a specific asset"""
    asset = get_object_or_404(Asset, id=asset_id)
    maintenance_records = asset.maintenance_records.all().order_by('-maintenance_date')
    
    records = []
    for record in maintenance_records:
        records.append({
            'id': str(record.id),
            'description': record.description,
            'maintenance_date': record.maintenance_date.strftime('%Y-%m-%d'),
            'performed_by': record.performed_by,
        })
    
    return JsonResponse({'maintenance': records})


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
def create_asset_maintenance(request, asset_id):
    """Create maintenance record for an asset"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        asset = get_object_or_404(Asset, id=asset_id)
        description = request.POST.get('description', '').strip()
        maintenance_date = request.POST.get('maintenance_date', '').strip()
        performed_by = request.POST.get('performed_by', '').strip()
        
        if not description or not maintenance_date:
            return JsonResponse({'error': 'Description and maintenance date are required'}, status=400)
        
        maintenance = AssetMaintenance.objects.create(
            asset=asset,
            description=description,
            maintenance_date=maintenance_date,
            performed_by=performed_by or ''
        )
        
        # Log the action
        Logs.objects.create(
            user=request.user,
            system_name='inventorymanagement',
            action='CREATE',
            target_model='AssetMaintenance',
            description=f"Created maintenance record for asset {asset.asset_code}",
            hidden_description=f"User '{request.user.username}' created maintenance record: {description}",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Maintenance record created successfully'
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e), 'success': False}, status=500)


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
def edit_asset_maintenance(request, maintenance_id):
    """Edit maintenance record"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        maintenance = get_object_or_404(AssetMaintenance, id=maintenance_id)
        
        description = request.POST.get('description', '').strip()
        maintenance_date = request.POST.get('maintenance_date', '').strip()
        performed_by = request.POST.get('performed_by', '').strip()
        
        if not description or not maintenance_date:
            return JsonResponse({'error': 'Description and maintenance date are required'}, status=400)
        
        old_description = maintenance.description
        maintenance.description = description
        maintenance.maintenance_date = maintenance_date
        maintenance.performed_by = performed_by or ''
        maintenance.save()
        
        # Log the action
        Logs.objects.create(
            user=request.user,
            system_name='inventorymanagement',
            action='UPDATE',
            target_model='AssetMaintenance',
            description=f"Updated maintenance record for asset {maintenance.asset.asset_code}",
            hidden_description=f"User '{request.user.username}' updated maintenance record from '{old_description}' to '{description}'",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Maintenance record updated successfully'
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e), 'success': False}, status=500)


@login_required
@require_system_access
@require_system_role(['admin', 'superadmin'])
@require_POST
def delete_asset_maintenance(request, maintenance_id):
    """Delete maintenance record"""
    try:
        maintenance = get_object_or_404(AssetMaintenance, id=maintenance_id)
        asset_code = maintenance.asset.asset_code
        maintenance_description = maintenance.description
        maintenance.delete()
        
        # Log the action
        Logs.objects.create(
            user=request.user,
            system_name='inventorymanagement',
            action='DELETE',
            target_model='AssetMaintenance',
            description=f"Deleted maintenance record for asset {asset_code}",
            hidden_description=f"User '{request.user.username}' deleted maintenance record: {maintenance_description}",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Maintenance record deleted successfully'
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e), 'success': False}, status=500)


@login_required
@require_system_role(['admin', 'superadmin'])
def ml_lab(request):
    """ML Lab for inventory management analytics and LSTM time-series forecasting."""
    from django.db.models.functions import TruncDate
    from .lstm_forecast import LSTMForecast

    current_system = getattr(request, 'current_system', None) or 'inventorymanagement'
    systems = request.session.get('accessible_systems', [])

    ml_models = MLInsight.objects.all()

    # Inventory stats
    total_items = InventoryItem.objects.count()
    low_stock = InventoryItem.objects.filter(quantity__lte=F('low_stock_threshold')).count()

    # Asset utilization
    total_assets = Asset.objects.count()
    assigned_assets = Asset.objects.filter(status='assigned').count()
    utilization_rate = round((assigned_assets / total_assets) * 100) if total_assets else 0

    # Requisition approval rate
    total_reqs = Requisition.objects.count()
    approved_reqs = Requisition.objects.filter(status='approved').count()
    approval_rate = round((approved_reqs / total_reqs) * 100) if total_reqs else 0

    # Build a complete 60-day daily transaction series (0-filled for missing dates)
    today = timezone.now().date()
    start_date = today - timedelta(days=59)
    last_60_days = timezone.now() - timedelta(days=60)

    raw_txns = (
        InventoryTransaction.objects
        .filter(created_at__gte=last_60_days)
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )
    date_count_map = {t['date']: t['count'] for t in raw_txns}
    all_dates   = [start_date + timedelta(days=i) for i in range(60)]
    full_series = [date_count_map.get(d, 0) for d in all_dates]

    # LSTM Time Series Forecasting
    lstm_trained    = False
    forecast_labels = []
    forecast_values = []
    forecast_points = []
    lstm_info       = {}

    if sum(full_series) >= 10:
        try:
            model = LSTMForecast(hidden=8, look_back=5, forecast=7, lr=0.02, epochs=50)
            model.fit(full_series)
            forecast_values = model.predict(full_series)
            forecast_labels = [
                (today + timedelta(days=i + 1)).strftime('%b %d')
                for i in range(7)
            ]
            forecast_points = list(zip(forecast_labels, forecast_values))
            lstm_trained = True
            lstm_info = {
                'hidden':           8,
                'look_back':        5,
                'forecast_horizon': 7,
                'n_samples':        len(full_series),
                'epochs':           50,
                'loss':             model._last_loss,
            }
        except Exception:
            pass

    # Last 30 days for the trend display
    trend_labels = [d.strftime('%b %d') for d in all_dates[-30:]]
    trend_values = full_series[-30:]

    context = {
        'systems':          systems,
        'current_system':   current_system,
        'ml_models':        ml_models,
        'total_items':      total_items,
        'low_stock':        low_stock,
        'utilization_rate': utilization_rate,
        'approval_rate':    approval_rate,
        'trend_labels':     json.dumps(trend_labels),
        'trend_values':     json.dumps(trend_values),
        'lstm_trained':     lstm_trained,
        'forecast_labels':  json.dumps(forecast_labels),
        'forecast_values':  json.dumps(forecast_values),
        'forecast_points':  forecast_points,
        'lstm_info':        lstm_info,
    }
    return render(request, 'inventorymanagement/pages/admin/ml_lab.html', context)

