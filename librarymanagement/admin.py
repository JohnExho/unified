from django.contrib import admin
from .models import (
    Library,
    Category,
    Author,
    Publisher,
    Book,
    BorrowingTransaction,
    Reservation,
    UserActivity,
    BookRecommendation,
    TrendingBook,
    UserCluster,
    LibraryReport,
    Notification,
)


@admin.register(Library)
class LibraryAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "contact_email", "contact_phone", "created_at")
    search_fields = ("name", "location", "contact_email")
    list_filter = ("created_at",)
    ordering = ("name",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent_category", "created_at")
    search_fields = ("name", "description")
    list_filter = ("parent_category", "created_at")
    ordering = ("name",)


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ("full_name", "nationality", "birth_date", "created_at")
    search_fields = ("first_name", "last_name", "nationality")
    list_filter = ("nationality", "created_at")
    ordering = ("last_name", "first_name")


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "website", "created_at")
    search_fields = ("name", "email", "website")
    list_filter = ("created_at",)
    ordering = ("name",)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "accession_number",
        "isbn",
        "library",
        "status",
        "available_copies",
        "total_copies",
        "publication_year",
    )
    search_fields = ("title", "isbn", "accession_number", "subject")
    list_filter = ("status", "resource_type", "library", "language", "publication_year")
    filter_horizontal = ("authors", "categories")
    ordering = ("title",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(BorrowingTransaction)
class BorrowingTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "book",
        "borrowed_date",
        "due_date",
        "return_date",
        "status",
        "fine_amount",
        "renewal_count",
    )
    search_fields = ("user__username", "book__title", "book__accession_number")
    list_filter = ("status", "borrowed_date", "due_date")
    readonly_fields = ("borrowed_date", "days_overdue")
    ordering = ("-borrowed_date",)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "book",
        "reservation_date",
        "expiry_date",
        "status",
        "notified",
        "fulfilled_date",
    )
    search_fields = ("user__username", "book__title")
    list_filter = ("status", "notified", "reservation_date")
    readonly_fields = ("reservation_date", "fulfilled_date", "notified_at")
    ordering = ("-reservation_date",)


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ("user", "activity_type", "book", "timestamp", "session_id")
    search_fields = ("user__username", "book__title", "search_query")
    list_filter = ("activity_type", "timestamp")
    readonly_fields = ("timestamp",)
    ordering = ("-timestamp",)


@admin.register(BookRecommendation)
class BookRecommendationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "book",
        "score",
        "reason",
        "viewed",
        "actioned",
        "created_at",
    )
    search_fields = ("user__username", "book__title", "reason")
    list_filter = ("viewed", "actioned", "created_at")
    readonly_fields = ("created_at",)
    ordering = ("-score", "-created_at")


@admin.register(TrendingBook)
class TrendingBookAdmin(admin.ModelAdmin):
    list_display = (
        "book",
        "period_type",
        "period_start",
        "period_end",
        "popularity_score",
        "borrow_count",
        "view_count",
    )
    search_fields = ("book__title",)
    list_filter = ("period_type", "period_start")
    readonly_fields = ("created_at",)
    ordering = ("-popularity_score", "-period_start")


@admin.register(UserCluster)
class UserClusterAdmin(admin.ModelAdmin):
    list_display = ("user", "cluster_id", "cluster_name", "assigned_at", "updated_at")
    search_fields = ("user__username", "cluster_name")
    list_filter = ("cluster_id", "assigned_at")
    readonly_fields = ("assigned_at", "updated_at")
    ordering = ("cluster_id", "user__username")


@admin.register(LibraryReport)
class LibraryReportAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "report_type",
        "period_start",
        "period_end",
        "generated_by",
        "generated_at",
    )
    search_fields = ("title", "summary")
    list_filter = ("report_type", "period_start", "generated_at")
    readonly_fields = ("generated_at",)
    ordering = ("-generated_at",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "notification_type",
        "title",
        "is_read",
        "is_sent",
        "created_at",
        "sent_at",
    )
    search_fields = ("user__username", "title", "message")
    list_filter = ("notification_type", "is_read", "is_sent", "created_at")
    readonly_fields = ("created_at", "sent_at", "read_at")
    ordering = ("-created_at",)
