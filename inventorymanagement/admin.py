from django.contrib import admin
from .models import (
    InventoryCategory,
    InventoryItem,
    InventoryTransaction,
    AssetCategory,
    Asset,
    AssetAssignment,
    AssetMaintenance,
    Requisition,
    RequisitionItem,
)

@admin.register(InventoryCategory)
class InventoryCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    search_fields = ("name",)
    list_filter = ("is_active",)

@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "quantity",
        "low_stock_threshold",
        "is_active",
        "created_at",
    )
    search_fields = ("name",)
    list_filter = ("category", "is_active")
    readonly_fields = ("created_at", "updated_at")


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "item",
        "transaction_type",
        "quantity",
        "performed_by",
        "created_at",
    )
    search_fields = ("item__name", "performed_by__username")
    list_filter = ("transaction_type", "created_at")
    readonly_fields = ("created_at",)


@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = (
        "asset_code",
        "name",
        "category",
        "status",
        "created_at",
    )
    search_fields = ("asset_code", "name")
    list_filter = ("category", "status")
    readonly_fields = ("created_at",)


@admin.register(AssetAssignment)
class AssetAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "asset",
        "assigned_to",
        "assigned_at",
        "returned_at",
    )
    search_fields = (
        "asset__asset_code",
        "assigned_to__username",
    )
    list_filter = ("assigned_at", "returned_at")


@admin.register(AssetMaintenance)
class AssetMaintenanceAdmin(admin.ModelAdmin):
    list_display = (
        "asset",
        "maintenance_date",
        "performed_by",
        "created_at",
    )
    search_fields = ("asset__asset_code", "performed_by")
    list_filter = ("maintenance_date",)
    readonly_fields = ("created_at",)


class RequisitionItemInline(admin.TabularInline):
    model = RequisitionItem
    extra = 0


@admin.register(Requisition)
class RequisitionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "requested_by",
        "status",
        "approved_by",
        "created_at",
    )
    search_fields = (
        "requested_by__username",
        "approved_by__username",
    )
    list_filter = ("status", "created_at")
    readonly_fields = ("created_at",)
    inlines = [RequisitionItemInline]



@admin.register(RequisitionItem)
class RequisitionItemAdmin(admin.ModelAdmin):
    list_display = (
        "requisition",
        "inventory_item",
        "quantity_requested",
        "quantity_issued",
    )
    search_fields = ("inventory_item__name",)
