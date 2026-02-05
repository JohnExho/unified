from django.contrib import admin
from .models import (
    Service,
    Member,
    MembershipHistory,
    DuesPayment,
    Contribution,
    Activity,
    Attendance,
    DocumentRecord,
    MLInsight,
)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "start_date", "end_date")


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("last_name", "first_name", "classification", "status")
    list_filter = ("classification", "status")
    search_fields = ("first_name", "last_name", "email")


@admin.register(MembershipHistory)
class MembershipHistoryAdmin(admin.ModelAdmin):
    list_display = ("member", "status", "changed_at")
    list_filter = ("status",)


@admin.register(DuesPayment)
class DuesPaymentAdmin(admin.ModelAdmin):
    list_display = ("member", "amount", "status", "due_date")
    list_filter = ("status", "method")


@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display = ("member", "title", "category", "date")
    list_filter = ("category",)


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("title", "start_date", "status")
    list_filter = ("status",)


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("member", "activity", "attended")
    list_filter = ("attended",)


@admin.register(DocumentRecord)
class DocumentRecordAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "created_at", "is_sensitive")
    list_filter = ("category", "is_sensitive")


@admin.register(MLInsight)
class MLInsightAdmin(admin.ModelAdmin):
    list_display = ("name", "target", "status", "generated_at")
    list_filter = ("status",)
