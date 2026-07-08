from django.test import TestCase
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from core.models import SystemMembership


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
