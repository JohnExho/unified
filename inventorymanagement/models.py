from django.db import models
from django.conf import settings
import uuid

class InventoryCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class InventoryItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=150)
    category = models.ForeignKey(
        InventoryCategory,
        on_delete=models.PROTECT,
        related_name="items"
    )

    description = models.TextField(blank=True)
    unit = models.CharField(max_length=50)  # pcs, box, liter, etc.

    quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=5)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_low_stock(self):
        return self.quantity <= self.low_stock_threshold

    def __str__(self):
        return self.name

class InventoryTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('ISSUE', 'Issue'),
        ('RETURN', 'Return'),
        ('TRANSFER', 'Transfer'),
        ('DISPOSE', 'Dispose'),
        ('ADJUST', 'Adjust'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name="transactions"
    )

    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField()  # negative allowed for adjustments

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    remarks = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type} - {self.item.name}"

class AssetCategory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Asset(models.Model):
    ASSET_STATUS = [
        ('AVAILABLE', 'Available'),
        ('ASSIGNED', 'Assigned'),
        ('UNDER_REPAIR', 'Under Repair'),
        ('RETIRED', 'Retired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    asset_code = models.CharField(max_length=50, unique=True)

    name = models.CharField(max_length=150)
    category = models.ForeignKey(
        AssetCategory,
        on_delete=models.PROTECT,
        related_name="assets"
    )

    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=ASSET_STATUS, default='AVAILABLE')

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.asset_code} - {self.name}"

class AssetAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="assignments"
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    assigned_at = models.DateTimeField(auto_now_add=True)
    returned_at = models.DateTimeField(blank=True, null=True)

    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"{self.asset.asset_code} → {self.assigned_to}"

class AssetMaintenance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    asset = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="maintenance_records"
    )

    description = models.TextField()
    maintenance_date = models.DateField()
    performed_by = models.CharField(max_length=150, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Maintenance - {self.asset.asset_code}"

class Requisition(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('ISSUED', 'Issued'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requisitions"
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    purpose = models.TextField(blank=True)
    borrower_first_name = models.CharField(max_length=100, blank=True)
    borrower_middle_initial = models.CharField(max_length=10, blank=True)
    borrower_last_name = models.CharField(max_length=100, blank=True)
    borrower_address = models.TextField(blank=True)
    borrower_contact_no = models.CharField(max_length=50, blank=True)
    borrower_position = models.CharField(max_length=150, blank=True)
    event_name = models.CharField(max_length=200, blank=True)
    date_borrowed = models.DateField(null=True, blank=True)
    date_returned = models.DateField(null=True, blank=True)
    time_borrowed = models.TimeField(null=True, blank=True)
    time_returned = models.TimeField(null=True, blank=True)

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_requisitions"
    )

    approved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Requisition {self.id}"


class RequisitionItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    requisition = models.ForeignKey(
        Requisition,
        on_delete=models.CASCADE,
        related_name="items"
    )

    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT
    )

    quantity_requested = models.PositiveIntegerField()
    quantity_issued = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.inventory_item.name} ({self.quantity_requested})"


class MLInsight(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('training', 'Training'),
        ('ready', 'Ready'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    target = models.CharField(max_length=120)
    algorithm = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    score = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name
