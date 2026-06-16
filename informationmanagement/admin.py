from django.contrib import admin
from .models import (
    Information,
    Project,
    BeneficiaryGroup,
    Partner,
    Activity,
    Report,
    ReportTemplate,
    MLModel,
    MLPipeline,
    MLExperiment,
    ContributionFund,
    FundAllocation,
    FundExpense,
    MemberContributionRecord,
    MasterDataDepartment,
)


# ============================================================================
# Existing Information Management Models
# ============================================================================


@admin.register(Information)
class InformationAdmin(admin.ModelAdmin):
    list_display = ["name", "start_date", "end_date"]
    search_fields = ["name", "description"]


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "status", "start_date", "end_date"]
    list_filter = ["status", "category"]
    search_fields = ["name", "lead"]


@admin.register(BeneficiaryGroup)
class BeneficiaryGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "segment", "priority", "households"]
    list_filter = ["priority"]
    search_fields = ["name", "segment"]


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ["name", "partner_type", "status", "engagement"]
    list_filter = ["status", "partner_type", "engagement"]
    search_fields = ["name", "contact_person"]


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ["title", "date", "status", "owner", "participants"]
    list_filter = ["status", "date"]
    search_fields = ["title", "owner"]


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ["title", "period", "status", "owner"]
    list_filter = ["status"]
    search_fields = ["title", "owner"]


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


@admin.register(MLModel)
class MLModelAdmin(admin.ModelAdmin):
    list_display = ["name", "model_type", "status", "metric"]
    list_filter = ["status"]
    search_fields = ["name"]


@admin.register(MLPipeline)
class MLPipelineAdmin(admin.ModelAdmin):
    list_display = ["name", "status"]
    list_filter = ["status"]
    search_fields = ["name"]


@admin.register(MLExperiment)
class MLExperimentAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "status", "updated_at"]
    list_filter = ["status"]
    search_fields = ["name", "owner"]


# ============================================================================
# Feature 1: Contribution Allocation Management - Admin
# ============================================================================


@admin.register(ContributionFund)
class ContributionFundAdmin(admin.ModelAdmin):
    list_display = ["name", "project", "budget_required", "status", "created_at"]
    list_filter = ["status", "project", "created_at"]
    search_fields = ["name", "description", "project__name"]
    readonly_fields = ["created_at", "updated_at"]
    
    fieldsets = (
        ("Fund Information", {
            "fields": ("project", "name", "description")
        }),
        ("Financial Details", {
            "fields": ("budget_required",)
        }),
        ("Status", {
            "fields": ("start_date", "status")
        }),
        ("Metadata", {
            "fields": ("created_by", "created_at", "updated_at")
        }),
    )


@admin.register(FundAllocation)
class FundAllocationAdmin(admin.ModelAdmin):
    list_display = ["fund", "amount", "allocated_date", "allocated_by"]
    list_filter = ["fund", "allocated_date"]
    search_fields = ["fund__name", "notes"]
    readonly_fields = ["created_at"]
    
    fieldsets = (
        ("Allocation Details", {
            "fields": ("fund", "amount", "allocated_date")
        }),
        ("Additional Info", {
            "fields": ("notes", "allocated_by")
        }),
        ("Metadata", {
            "fields": ("created_at",)
        }),
    )


@admin.register(FundExpense)
class FundExpenseAdmin(admin.ModelAdmin):
    list_display = ["fund", "category", "description", "amount", "expense_date"]
    list_filter = ["fund", "category", "expense_date"]
    search_fields = ["fund__name", "description", "reference_no"]
    readonly_fields = ["created_at"]
    
    fieldsets = (
        ("Expense Details", {
            "fields": ("fund", "category", "description", "amount", "expense_date")
        }),
        ("Reference", {
            "fields": ("reference_no", "recorded_by")
        }),
        ("Metadata", {
            "fields": ("created_at",)
        }),
    )


# ============================================================================
# Feature 3: Member Contribution Monitoring - Admin
# ============================================================================


@admin.register(MemberContributionRecord)
class MemberContributionRecordAdmin(admin.ModelAdmin):
    list_display = [
        "member_name",
        "employee_id",
        "department",
        "project",
        "total_contributions",
        "payment_status",
    ]
    list_filter = ["payment_status", "department", "project", "updated_at"]
    search_fields = ["member_name", "employee_id", "department__name", "project__name"]
    readonly_fields = ["created_at", "updated_at"]
    
    fieldsets = (
        ("Member Information", {
            "fields": ("project", "member_name", "employee_id", "department")
        }),
        ("Financial Summary", {
            "fields": (
                "total_contributions",
                "current_balance",
                "due_amount",
                "late_payment_penalties",
            )
        }),
        ("Status", {
            "fields": ("payment_status", "last_payment_date")
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at")
        }),
    )


@admin.register(MasterDataDepartment)
class MasterDataDepartmentAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "description"]
    readonly_fields = ["created_at"]
