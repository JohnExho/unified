from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from inventorymanagement.models import (
    Asset,
    AssetAssignment,
    AssetCategory,
    AssetMaintenance,
    InventoryCategory,
    InventoryItem,
    InventoryTransaction,
    MLInsight,
    Requisition,
    RequisitionItem,
)


class Command(BaseCommand):
    help = "Seed Inventory Management with sample categories, items, assets, and requisitions."

    def _get_seed_user(self):
        user_model = get_user_model()
        user = user_model.objects.order_by("date_joined").first()
        if user:
            return user

        return user_model.objects.create_user(
            username="seed_user",
            email="seed_user@example.com",
            password="seed-password-123",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        user = self._get_seed_user()

        RequisitionItem.objects.all().delete()
        Requisition.objects.all().delete()
        AssetAssignment.objects.all().delete()
        AssetMaintenance.objects.all().delete()
        InventoryTransaction.objects.all().delete()
        Asset.objects.all().delete()
        AssetCategory.objects.all().delete()
        InventoryItem.objects.all().delete()
        InventoryCategory.objects.all().delete()
        MLInsight.objects.all().delete()

        office_cat = InventoryCategory.objects.create(
            name="Office Supplies",
            description="Consumables for office operations.",
            is_active=True,
        )
        lab_cat = InventoryCategory.objects.create(
            name="Laboratory Supplies",
            description="Items for testing and experiments.",
            is_active=True,
        )

        paper = InventoryItem.objects.create(
            name="Bond Paper A4",
            category=office_cat,
            unit="ream",
            quantity=80,
            low_stock_threshold=20,
        )
        marker = InventoryItem.objects.create(
            name="Whiteboard Marker",
            category=office_cat,
            unit="pcs",
            quantity=120,
            low_stock_threshold=30,
        )
        reagent = InventoryItem.objects.create(
            name="Lab Reagent Kit",
            category=lab_cat,
            unit="box",
            quantity=14,
            low_stock_threshold=5,
        )

        InventoryTransaction.objects.create(
            item=paper,
            transaction_type="ISSUE",
            quantity=10,
            performed_by=user,
            remarks="Issued for registrar office use.",
        )
        InventoryTransaction.objects.create(
            item=marker,
            transaction_type="RETURN",
            quantity=5,
            performed_by=user,
            remarks="Returned unused markers.",
        )
        InventoryTransaction.objects.create(
            item=reagent,
            transaction_type="ADJUST",
            quantity=-1,
            performed_by=user,
            remarks="Damaged box adjustment.",
        )

        ict_assets = AssetCategory.objects.create(name="ICT Equipment")
        furniture_assets = AssetCategory.objects.create(name="Furniture")

        laptop = Asset.objects.create(
            asset_code="ICT-0001",
            name="Faculty Laptop",
            category=ict_assets,
            status="ASSIGNED",
        )
        projector = Asset.objects.create(
            asset_code="ICT-0002",
            name="Multimedia Projector",
            category=ict_assets,
            status="AVAILABLE",
        )
        desk = Asset.objects.create(
            asset_code="FUR-0001",
            name="Office Desk",
            category=furniture_assets,
            status="AVAILABLE",
        )

        AssetAssignment.objects.create(
            asset=laptop,
            assigned_to=user,
            remarks="Assigned to seed user for testing.",
        )

        AssetMaintenance.objects.create(
            asset=projector,
            description="Lens cleaning and alignment.",
            maintenance_date=timezone.localdate(),
            performed_by="Campus ICT Unit",
        )

        requisition = Requisition.objects.create(
            requested_by=user,
            status="APPROVED",
            purpose="Supplies for midterm examinations.",
            approved_by=user,
            approved_at=timezone.now(),
        )
        RequisitionItem.objects.create(
            requisition=requisition,
            inventory_item=paper,
            quantity_requested=15,
            quantity_issued=15,
        )
        RequisitionItem.objects.create(
            requisition=requisition,
            inventory_item=marker,
            quantity_requested=10,
            quantity_issued=8,
        )

        MLInsight.objects.create(
            name="Stock Depletion Forecast",
            target="quantity",
            algorithm="LSTM",
            status="ready",
            score=0.874,
            notes="Seeded forecast insight for Inventory ML Lab.",
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded Inventory Management with categories, items, assets, requisitions, and ML insight."
            )
        )
