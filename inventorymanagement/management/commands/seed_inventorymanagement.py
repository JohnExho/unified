from datetime import timedelta

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
    Requisition,
    RequisitionItem,
    MLInsight,
)


class Command(BaseCommand):
    help = "Seed Inventory Management with assets, inventory items, and requisitions drawn from the provided KNS data."

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

    def _get_seed_approver(self, exclude_user):
        user_model = get_user_model()
        approver = user_model.objects.exclude(pk=exclude_user.pk).order_by("date_joined").first()
        if approver:
            return approver

        return user_model.objects.create_user(
            username="seed_approver",
            email="seed_approver@example.com",
            password="seed-password-123",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        user = self._get_seed_user()
        approver = self._get_seed_approver(user)

        AssetAssignment.objects.all().delete()
        AssetMaintenance.objects.all().delete()
        Asset.objects.all().delete()
        AssetCategory.objects.all().delete()
        InventoryTransaction.objects.all().delete()
        RequisitionItem.objects.all().delete()
        Requisition.objects.all().delete()
        InventoryItem.objects.all().delete()
        InventoryCategory.objects.all().delete()

        ict_assets = AssetCategory.objects.create(name="ICT Equipment")
        furniture_assets = AssetCategory.objects.create(name="Furniture")
        appliance_assets = AssetCategory.objects.create(name="Appliances")
        hospitality_assets = AssetCategory.objects.create(name="Hospitality Equipment")
        laboratory_assets = AssetCategory.objects.create(name="Laboratory Equipment")
        office_equipment = AssetCategory.objects.create(name="Office Equipment")
        facility_assets = AssetCategory.objects.create(name="Facility Equipment")
        kitchen_assets = AssetCategory.objects.create(name="Kitchen Equipment")
        housekeeping_assets = AssetCategory.objects.create(name="Housekeeping Equipment")

        office_supplies = InventoryCategory.objects.create(
            name="Office Supplies",
            description="Office consumables and stationery.",
        )
        cleaning_supplies = InventoryCategory.objects.create(
            name="Cleaning Supplies",
            description="Cleaning and housekeeping materials.",
        )
        kitchen_supplies = InventoryCategory.objects.create(
            name="Kitchen Supplies",
            description="Kitchen and hospitality supplies.",
        )
        laboratory_supplies = InventoryCategory.objects.create(
            name="Laboratory Supplies",
            description="Laboratory consumables for training and demonstrations.",
        )
        hospitality_supplies = InventoryCategory.objects.create(
            name="Hospitality Supplies",
            description="Hospitality service ware and disposable items.",
        )

        assets = [
            ("KNS26-MON-01", "View Plus Monitor", ict_assets, "Black monitor from KNS New Library."),
            ("KNS26-CPU-01", "Power Logic CPU", ict_assets, "Desktop CPU stationed in KNS New Library."),
            ("KNS26-KBD-01", "Delux Keyboard", ict_assets, "Black keyboard from KNS New Library."),
            ("KNS26-MSE-01", "Delux Mouse", ict_assets, "Black mouse from KNS New Library."),
            ("KNS26-MON-02", "View Plus Monitor", ict_assets, "Second monitor from KNS New Library."),
            ("KNS26-CPU-02", "Power Logic CPU", ict_assets, "Second desktop CPU from KNS New Library."),
            ("KNS26-KBD-02", "Delux Keyboard", ict_assets, "Second keyboard from KNS New Library."),
            ("KNS26-MSE-02", "Delux Mouse", ict_assets, "Second mouse from KNS New Library."),
            ("KNS24-PRT-01", "Canon Printer", office_equipment, "Canon printer used by the College President MIS office."),
            ("KNS24-PRT-02", "Epson EcoTank Printer", office_equipment, "Epson L3110 printer from the registrar office."),
            ("KNS24-AC-01", "LG Aircon", appliance_assets, "Window air conditioner located in the registrar office."),
            ("KNS23-MON-01", "AOC Monitor", ict_assets, "AOC monitor in the hospitality management department."),
            ("KNS23-KBD-01", "A4Tech Keyboard", ict_assets, "Black A4Tech keyboard in the hospitality management department."),
            ("KNS23-MSE-01", "Rapoo Mouse", ict_assets, "Black Rapoo mouse in the hospitality management department."),
            ("KNS23-AVR-01", "AVR Unit", office_equipment, "AVR used in the registrar office."),
            ("KNS23-AC-01", "LG Aircon", appliance_assets, "Aircon unit in the registrar office."),
            ("KNS23-LAP-01", "Dell Laptop", ict_assets, "Dell laptop assigned to the air/internet laboratory office."),
            ("KNS23-LAP-02", "Dell Laptop", ict_assets, "Second Dell laptop assigned to the air/internet laboratory office."),
            ("KNS23-LAP-03", "Dell Laptop", ict_assets, "Third Dell laptop assigned to the air/internet laboratory office."),
            ("KNS23-LAP-04", "Dell Laptop", ict_assets, "Fourth Dell laptop assigned to the air/internet laboratory office."),
            ("KNS23-CPU-01", "Trend Sonic CPU", ict_assets, "CPU in the college president MIS office."),
            ("KNS23-CHR-01", "Plastic Cream Chair", furniture_assets, "Plastic cream chair in faculty and conference spaces."),
            ("KNS23-TBL-01", "Long Table", furniture_assets, "White long table from the conference room."),
            ("KNS25-CHR-01", "Rattan Chair", hospitality_assets, "Brown rattan chair used in hospitality management."),
            ("KNS25-TBL-01", "Rattan Table", hospitality_assets, "Brown rattan table used in hospitality management."),
            ("KNS23-PRT-03", "Epson L210 Printer", office_equipment, "Printer for the president/MIS office."),
            ("KNS23-AC-02", "Everest Aircon", appliance_assets, "2HP Everest aircon unit in the president MIS office."),
            ("KNS24-TBL-01", "Office Table", furniture_assets, "Gray table from the registrar office."),
            ("KNS24-CHR-01", "Office Chair", furniture_assets, "Black office chair used in the registrar office."),
            ("KNS23-FAN-01", "Ceiling Fan", appliance_assets, "Fan in the planning office and faculty spaces."),
            ("KNS23-AC-03", "LG White Aircon", appliance_assets, "Aircon installed in the faculty office."),
            ("KNS23-AC-04", "Aircon with Remote", appliance_assets, "Aircon unit with remote control in the conference room."),
            ("KNS23-AC-05", "LG White Aircon", appliance_assets, "LG aircon in faculty spaces."),
            ("KNS23-AC-06", "Window Aircon", appliance_assets, "Additional window aircon from the faculty office."),
            ("KNS23-FAN-02", "Stand Fan", appliance_assets, "Blue stand fan in the faculty office."),
            ("KNS23-WFN-01", "Wall Fan", appliance_assets, "Wall fan in the faculty office."),
            ("KNS23-CHR-02", "Teacher Chair", furniture_assets, "Yellow teacher chair in the planning office."),
            ("KNS23-CHR-03", "Teacher Chair", furniture_assets, "Second teacher chair in the planning office."),
            ("KNS23-TBL-02", "Teacher Table", furniture_assets, "White teacher table in the planning office."),
            ("KNS23-CHR-04", "Conference Room Chair", furniture_assets, "Third chair used in the conference room."),
            ("KNS23-TBL-03", "Conference Room Table", furniture_assets, "Second table used in the conference room."),
            ("KNS25-CHR-02", "Rattan Chair", hospitality_assets, "Second rattan chair used in hospitality management."),
            ("KNS25-CHR-03", "Rattan Chair", hospitality_assets, "Third rattan chair used in hospitality management."),
            ("KNS25-TBL-02", "Rattan Table", hospitality_assets, "Second rattan table used in hospitality management."),
            ("KNS25-BRD-02", "Bread Plate", hospitality_assets, "Second bread plate used in food service."),
            ("KNS25-BRD-03", "Bread Plate", hospitality_assets, "Third bread plate used in food service."),
            ("KNS25-BLD-02", "Eureka Blender", hospitality_assets, "Second Eureka blender in hospitality management."),
            ("KNS25-ACW-02", "Aircon Window Type", appliance_assets, "Second window-type aircon for hospitality training."),
            ("KNS25-AEP-02", "Airpot Electric", kitchen_assets, "Second electric airpot used in hospitality management."),
            ("KNS25-BSP-02", "Baking Spatula", kitchen_assets, "Second baking spatula used in hospitality kitchen."),
            ("KNS25-BKN-02", "Baking Knife", kitchen_assets, "Second baking knife used in hospitality training."),
            ("KNS24-CRT-01", "Cake Molder", kitchen_assets, "Cake molder used in hospitality kitchen."),
            ("KNS24-BSP-01", "Butter Spreader", kitchen_assets, "Butter spreader used in hotel kitchen."),
            ("KNS24-BKN-01", "Butcher Knife", kitchen_assets, "Butcher knife used in hospitality training."),
            ("KNS24-BKT-01", "Bucket", housekeeping_assets, "Cleaning bucket used in housekeeping."),
            ("KNS24-BRM-01", "Brooms", housekeeping_assets, "Brooms used in facility cleaning."),
            ("KNS24-BGL-01", "Breeze Glass", hospitality_assets, "Breeze glass used in hospitality lab display."),
            ("KNS24-BKN-02", "Brandy Knife", hospitality_assets, "Brandy knife used in hospitality training."),
            ("KNS23-SHF-01", "Filing Cabinet", office_equipment, "Filing cabinet used in faculty office."),
            ("KNS25-BRD-01", "Bread Plate", hospitality_assets, "Silver bread plate used in food service."),
            ("KNS24-LDR-01", "Three-Step Ladder", facility_assets, "White three-step ladder for maintenance."),
            ("KNS24-SHF-01", "Four-Layer Shelves", facility_assets, "White 4-layer shelf unit in facility storage."),
            ("KNS25-BKSP-01", "Baking Spatula", kitchen_assets, "Baking spatula used in hospitality kitchen."),
            ("KNS25-BRCK-01", "Baking Rack", kitchen_assets, "Baking rack in hospitality management."),
            ("KNS25-BM-01", "Bain Marie", kitchen_assets, "Bain Marie for food preparation."),
            ("KNS25-ATH-01", "Ashtray", hospitality_assets, "Ashtray used in hospitality training."),
            ("KNS25-APR-01", "Apron Plate", hospitality_assets, "Apron plate used in hospitality kitchen."),
            ("KNS25-ACW-01", "Aircon Window Type", appliance_assets, "Window type aircon for hospitality training."),
            ("KNS25-AEP-01", "Airpot Electric", kitchen_assets, "Electric airpot used in hospitality management."),
            ("KNS25-AGB-01", "Advance Globe", hospitality_assets, "Decorative globe used in hospitality display."),
            ("KNS24-EKT-01", "Electric Kettle", kitchen_assets, "Electric kettle used in lab kitchen."),
            ("KNS24-EFH-01", "Electric Food Heater", kitchen_assets, "Food heater used in hospitality labs."),
            ("KNS24-DVD-01", "DVD Player", office_equipment, "DVD player used for presentations."),
            ("KNS24-DPN-01", "Dust Pan", housekeeping_assets, "Dust pan for housekeeping use."),
            ("KNS24-DCT-01", "Dough Cutter", kitchen_assets, "Dough cutter used in hospitality kitchen."),
            ("KNS24-DPL-01", "Dinner Plate", hospitality_assets, "Dinner plate used in hospitality service."),
            ("KNS24-DFN-01", "Desk Fan", appliance_assets, "Desk fan used in lab offices."),
            ("KNS24-CTB-01", "Cutting Board", kitchen_assets, "Cutting board used in hospitality kitchen."),
            ("KNS24-CR8-01", "Crates", housekeeping_assets, "Storage crates for kitchen supplies."),
            ("KNS25-LGH-01", "Lights", facility_assets, "Facility lighting equipment."),
            ("KNS25-EML-01", "Emergency Lights", facility_assets, "Emergency lights for facility areas."),
            ("KNS25-LKL-01", "Lucky Light", facility_assets, "Special-purpose lucky light in hospitality."),
            ("KNS23-SFA-01", "Sofa", furniture_assets, "Brown sofa in the faculty office."),
            ("KNS23-CAB-01", "Cabinet", furniture_assets, "Metal cabinet in the faculty office."),
            ("KNS23-FLC-01", "Filling Cabinet", furniture_assets, "Filling cabinet in the faculty office."),
            ("KNS23-FIL-01", "File Organizer", office_equipment, "Three-layer file organizer used in the College President MIS office."),
        ]

        created_assets = {}
        for code, name, category, desc in assets:
            created_assets[code] = Asset.objects.create(
                asset_code=code,
                name=name,
                category=category,
                description=desc,
                status="AVAILABLE",
            )

        AssetAssignment.objects.create(
            asset=created_assets["KNS23-LAP-01"],
            assigned_to=user,
            remarks="Assigned laptop used by air/internet laboratory office.",
        )
        AssetAssignment.objects.create(
            asset=created_assets["KNS23-CPU-01"],
            assigned_to=user,
            remarks="Assigned MIS office desktop CPU for testing.",
        )

        AssetMaintenance.objects.create(
            asset=created_assets["KNS23-AC-01"],
            description="Aircon filter and remote check.",
            maintenance_date=timezone.localdate(),
            performed_by="Property/Supplies Office",
        )
        AssetMaintenance.objects.create(
            asset=created_assets["KNS24-PRT-02"],
            description="Printer head cleaning and paper feed adjustment.",
            maintenance_date=timezone.localdate(),
            performed_by="Office Equipment Team",
        )

        inventory_items_data = [
            ("Printer Toner", office_supplies, "Replacement toner for Canon and Epson printers.", "pcs", 12, 3),
            ("A4 Paper Ream", office_supplies, "Ream of A4 printing paper.", "reams", 24, 8),
            ("File Organizer", office_supplies, "File organizer for office document storage.", "pcs", 3, 3),
            ("Dust Pan", cleaning_supplies, "Dust pan for housekeeping use.", "pcs", 14, 5),
            ("Brooms", cleaning_supplies, "Housekeeping broom for sweeping floors.", "pcs", 9, 3),
            ("Garbage Bags", cleaning_supplies, "Black garbage bags for waste disposal.", "rolls", 18, 6),
            ("Bread Plate", hospitality_supplies, "Bread plates for hospitality service.", "pcs", 30, 10),
            ("Dinner Plate", hospitality_supplies, "Dinner plates for guest service.", "pcs", 25, 8),
            ("Electric Kettle", kitchen_supplies, "Electric kettle for kitchen preparation.", "pcs", 2, 2),
            ("Cutting Board", kitchen_supplies, "Cutting board used in hospitality kitchen.", "pcs", 4, 4),
            ("Baking Rack", kitchen_supplies, "Baking rack for hospitality baking tasks.", "pcs", 8, 2),
            ("Dish Soap", kitchen_supplies, "Liquid dish soap for kitchen cleaning.", "liters", 12, 4),
            ("Apron Plate", hospitality_supplies, "Apron plate used in hospitality training.", "pcs", 3, 3),
        ]

        created_inventory_items = {}
        for name, category, desc, unit, qty, threshold in inventory_items_data:
            created_inventory_items[name] = InventoryItem.objects.create(
                name=name,
                category=category,
                description=desc,
                unit=unit,
                quantity=qty,
                low_stock_threshold=threshold,
            )

        InventoryTransaction.objects.create(
            item=created_inventory_items["Printer Toner"],
            transaction_type="ISSUE",
            quantity=-2,
            performed_by=user,
            remarks="Issued toner to the registrar office.",
        )
        InventoryTransaction.objects.create(
            item=created_inventory_items["A4 Paper Ream"],
            transaction_type="ISSUE",
            quantity=-6,
            performed_by=user,
            remarks="Issued paper to the president MIS office.",
        )
        InventoryTransaction.objects.create(
            item=created_inventory_items["Dust Pan"],
            transaction_type="ISSUE",
            quantity=-3,
            performed_by=user,
            remarks="Issued dust pans to housekeeping staff.",
        )
        InventoryTransaction.objects.create(
            item=created_inventory_items["Bread Plate"],
            transaction_type="ISSUE",
            quantity=-12,
            performed_by=user,
            remarks="Issued bread plates for hospitality student service.",
        )
        InventoryTransaction.objects.create(
            item=created_inventory_items["Dinner Plate"],
            transaction_type="RETURN",
            quantity=3,
            performed_by=user,
            remarks="Returned dinner plates from event service.",
        )
        InventoryTransaction.objects.create(
            item=created_inventory_items["Dish Soap"],
            transaction_type="ADJUST",
            quantity=4,
            performed_by=user,
            remarks="Stock correction after new delivery.",
        )
        InventoryTransaction.objects.create(
            item=created_inventory_items["Brooms"],
            transaction_type="TRANSFER",
            quantity=-2,
            performed_by=user,
            remarks="Transferred brooms to the hospitality training area.",
        )

        requisition_pending = Requisition.objects.create(
            requested_by=user,
            status="PENDING",
            purpose="Request additional hospitality plates for student training.",
        )
        requisition_approved = Requisition.objects.create(
            requested_by=user,
            status="APPROVED",
            purpose="Request more stationery and file organizers for office staff.",
            approved_by=approver,
            approved_at=timezone.now() - timedelta(days=1),
        )
        requisition_issued = Requisition.objects.create(
            requested_by=user,
            status="ISSUED",
            purpose="Issue kitchen supplies for weekend culinary lab.",
            approved_by=approver,
            approved_at=timezone.now() - timedelta(days=2),
        )
        requisition_rejected = Requisition.objects.create(
            requested_by=user,
            status="REJECTED",
            purpose="Request extra cleaning brooms for facility team.",
            approved_by=approver,
            approved_at=timezone.now() - timedelta(days=1),
        )

        RequisitionItem.objects.create(
            requisition=requisition_pending,
            inventory_item=created_inventory_items["Dinner Plate"],
            quantity_requested=20,
            quantity_issued=0,
        )
        RequisitionItem.objects.create(
            requisition=requisition_pending,
            inventory_item=created_inventory_items["Bread Plate"],
            quantity_requested=15,
            quantity_issued=0,
        )
        RequisitionItem.objects.create(
            requisition=requisition_approved,
            inventory_item=created_inventory_items["A4 Paper Ream"],
            quantity_requested=10,
            quantity_issued=10,
        )
        RequisitionItem.objects.create(
            requisition=requisition_approved,
            inventory_item=created_inventory_items["File Organizer"],
            quantity_requested=4,
            quantity_issued=4,
        )
        RequisitionItem.objects.create(
            requisition=requisition_issued,
            inventory_item=created_inventory_items["Dish Soap"],
            quantity_requested=6,
            quantity_issued=6,
        )
        RequisitionItem.objects.create(
            requisition=requisition_issued,
            inventory_item=created_inventory_items["Cutting Board"],
            quantity_requested=5,
            quantity_issued=5,
        )
        RequisitionItem.objects.create(
            requisition=requisition_rejected,
            inventory_item=created_inventory_items["Brooms"],
            quantity_requested=4,
            quantity_issued=0,
        )

        MLInsight.objects.create(
            name="KNS Inventory Insight",
            target="asset categorization",
            algorithm="logistic regression",
            status="ready",
            notes=(
                "Seeded core ICT, furniture, appliance, hospitality, and facility assets from KNS inventory images "
                "while preserving machine learning insight metadata."
            ),
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded Inventory Management with assets, inventory items, transactions, and requisitions from KNS data."
            )
        )
