from django.test import TestCase
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from core.models import SystemMembership
from .models import Asset, AssetAssignment, AssetCategory, InventoryCategory, InventoryItem, InventoryTransaction, Requisition, RequisitionItem


class InventoryAccessRestrictionTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(username='regularuser', password='testpass123')
        self.admin = self.User.objects.create_user(username='inventoryadmin', password='testpass123')

        SystemMembership.objects.create(user=self.user, system_name='inventorymanagement', system_role='user')
        SystemMembership.objects.create(user=self.admin, system_name='inventorymanagement', system_role='admin')

    def test_user_role_is_redirected_from_inventory_page(self):
        self.client.force_login(self.user)
        session = self.client.session
        session['current_system'] = 'inventorymanagement'
        session.save()

        response = self.client.get('/inventorymanagement/inventory/')

        self.assertRedirects(response, '/inventorymanagement/requisitions/')

    def test_user_role_is_redirected_from_assets_page(self):
        self.client.force_login(self.user)
        session = self.client.session
        session['current_system'] = 'inventorymanagement'
        session.save()

        response = self.client.get('/inventorymanagement/assets/')

        self.assertRedirects(response, '/inventorymanagement/requisitions/')

    def test_requisition_modal_does_not_mark_date_fields_required(self):
        html = render_to_string('inventorymanagement/modals/add_requisition_modal.html')

        self.assertNotIn('id="dateBorrowed" required', html)
        self.assertNotIn('id="dateReturned" required', html)
        self.assertNotIn('id="timeBorrowed" required', html)
        self.assertNotIn('id="timeReturned" required', html)
        self.assertNotIn('Date Borrowed', html)
        self.assertNotIn('Date Returned', html)


class InventoryRequisitionFlowTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.requester = self.User.objects.create_user(username='requester', password='testpass123')
        self.admin = self.User.objects.create_user(username='inventoryadmin', password='testpass123')

        SystemMembership.objects.create(user=self.requester, system_name='inventorymanagement', system_role='user')
        SystemMembership.objects.create(user=self.admin, system_name='inventorymanagement', system_role='admin')

        self.category = InventoryCategory.objects.create(name='Supplies')
        self.item = InventoryItem.objects.create(
            name='Projector Cable',
            category=self.category,
            unit='pcs',
            quantity=5,
            low_stock_threshold=2,
        )

    def _set_inventory_session(self):
        session = self.client.session
        session['current_system'] = 'inventorymanagement'
        session['accessible_systems'] = ['inventorymanagement']
        session.save()

    def test_approve_requisition_auto_issues_inventory_and_logs_transaction(self):
        requisition = Requisition.objects.create(requested_by=self.requester, status='PENDING')
        RequisitionItem.objects.create(requisition=requisition, inventory_item=self.item, quantity_requested=3)

        self.client.force_login(self.admin)
        self._set_inventory_session()

        response = self.client.post(reverse('inventorymanagement:approve_requisition', args=[requisition.id]))

        self.assertEqual(response.status_code, 302)

        requisition.refresh_from_db()
        self.item.refresh_from_db()
        req_item = requisition.items.get()

        self.assertEqual(requisition.status, 'ISSUED')
        self.assertEqual(requisition.approved_by, self.admin)
        self.assertIsNotNone(requisition.approved_at)
        self.assertEqual(req_item.quantity_issued, 3)
        self.assertEqual(self.item.quantity, 2)

        transaction = InventoryTransaction.objects.get(item=self.item, transaction_type='ISSUE')
        self.assertEqual(transaction.quantity, -3)

    def test_approve_requisition_rejects_insufficient_stock(self):
        requisition = Requisition.objects.create(requested_by=self.requester, status='PENDING')
        RequisitionItem.objects.create(requisition=requisition, inventory_item=self.item, quantity_requested=6)

        self.client.force_login(self.admin)
        self._set_inventory_session()

        response = self.client.post(reverse('inventorymanagement:approve_requisition', args=[requisition.id]))

        self.assertEqual(response.status_code, 302)

        requisition.refresh_from_db()
        self.item.refresh_from_db()
        req_item = requisition.items.get()

        self.assertEqual(requisition.status, 'PENDING')
        self.assertIsNone(requisition.approved_by)
        self.assertEqual(req_item.quantity_issued, 0)
        self.assertEqual(self.item.quantity, 5)
        self.assertFalse(InventoryTransaction.objects.filter(item=self.item, transaction_type='ISSUE').exists())

    def test_dashboard_and_ml_lab_use_live_statuses_and_quantities(self):
        InventoryTransaction.objects.create(
            item=self.item,
            transaction_type='ISSUE',
            quantity=-4,
            performed_by=self.admin,
            remarks='Issued today',
        )
        InventoryTransaction.objects.create(
            item=self.item,
            transaction_type='RETURN',
            quantity=2,
            performed_by=self.admin,
            remarks='Returned today',
        )

        asset_category = AssetCategory.objects.create(name='Electronics')
        assigned_asset = Asset.objects.create(asset_code='AST-001', name='Laptop', category=asset_category, status='ASSIGNED')
        returned_asset = Asset.objects.create(asset_code='AST-002', name='Speaker', category=asset_category, status='AVAILABLE')
        AssetAssignment.objects.create(asset=assigned_asset, assigned_to=self.requester, assigned_to_name='Requester')
        returned_assignment = AssetAssignment.objects.create(
            asset=returned_asset,
            assigned_to=self.requester,
            assigned_to_name='Requester',
            returned_at=timezone.now(),
        )
        AssetAssignment.objects.filter(id=returned_assignment.id).update(assigned_at=timezone.now() - timedelta(days=1))

        approved_requisition = Requisition.objects.create(
            requested_by=self.requester,
            status='ISSUED',
            approved_by=self.admin,
            approved_at=timezone.now(),
        )
        RequisitionItem.objects.create(requisition=approved_requisition, inventory_item=self.item, quantity_requested=1, quantity_issued=1)
        Requisition.objects.create(requested_by=self.requester, status='REJECTED')

        self.client.force_login(self.admin)
        self._set_inventory_session()

        dashboard_response = self.client.get(reverse('inventorymanagement:inventory-dashboard'))
        ml_lab_response = self.client.get(reverse('inventorymanagement:ml_lab'))

        self.assertEqual(dashboard_response.context['issued_today'], 5)
        self.assertEqual(dashboard_response.context['returned_today'], 3)
        self.assertEqual(ml_lab_response.context['utilization_rate'], 50)
        self.assertEqual(ml_lab_response.context['approval_rate'], 50)
