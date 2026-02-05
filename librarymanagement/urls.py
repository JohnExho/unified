# urls.py
from django.shortcuts import redirect
from django.urls import path
from . import views

app_name = "librarymanagement"

urlpatterns = [
    path(
        "",
        lambda request: redirect("librarymanagement:library_dashboard"),
        name="library_root",
    ),
    path("dashboard/", views.dashboard, name="library_dashboard"),
    # Libraries
    path("libraries/add/", views.add_library, name="add_library"),
    # Books
    path("books/", views.books_list, name="books_list"),
    path("books/add/", views.add_book, name="add_book"),
    # Transactions
    path("transactions/", views.transactions_list, name="transactions_list"),
    path("transactions/create/", views.create_transaction, name="create_transaction"),
    path(
        "transactions/<uuid:transaction_id>/",
        views.transaction_detail,
        name="transaction_detail",
    ),
    path(
        "transactions/<uuid:transaction_id>/return/",
        views.return_book,
        name="return_book",
    ),
    path(
        "transactions/<uuid:transaction_id>/renew/", views.renew_book, name="renew_book"
    ),
    # Reservations
    path("reservations/", views.reservations_list, name="reservations_list"),
    path(
        "reservations/<uuid:reservation_id>/ready/",
        views.mark_reservation_ready,
        name="mark_reservation_ready",
    ),
    path(
        "reservations/<uuid:reservation_id>/fulfill/",
        views.fulfill_reservation,
        name="fulfill_reservation",
    ),
    path(
        "reservations/<uuid:reservation_id>/cancel/",
        views.cancel_reservation,
        name="cancel_reservation",
    ),
    path(
        "reservations/<uuid:reservation_id>/notify/",
        views.notify_user_reservation,
        name="notify_user_reservation",
    ),
    # Authors & Publishers
    path(
        "authors-publishers/",
        views.authors_publishers_management,
        name="authors_publishers_management",
    ),
    path("authors/add/", views.add_author, name="add_author"),
    path("publishers/add/", views.add_publisher, name="add_publisher"),
    # Other features
    path("user-activity/", views.user_activities, name="user_activities"),
    path(
        "recommendations/",
        views.recommendations_dashboard,
        name="recommendations_dashboard",
    ),
    path("trending/", views.trending_books, name="trending_books"),
    path("reports/", views.reports_dashboard, name="reports_dashboard"),
    path(
        "reports/<uuid:report_id>/download/",
        views.download_report,
        name="download_report",
    ),
    path("settings/", views.library_settings, name="library_settings"),
    path("settings/user/", views.user_settings, name="user_settings"),
    path(
        "settings/user/profile/",
        views.user_profile_data,
        name="user_profile_data",
    ),
    path(
        "settings/user/activity/",
        views.user_activity_stats,
        name="user_activity_stats",
    ),
    path(
        "settings/manage/",
        views.manage_library_settings,
        name="manage_library_settings",
    ),
    # Book Management
    path("books/<uuid:book_id>/edit/", views.edit_book, name="edit_book"),
    path("books/<uuid:book_id>/delete/", views.delete_book, name="delete_book"),
    path(
        "books/<uuid:book_id>/toggle-status/",
        views.toggle_book_status,
        name="toggle_book_status",
    ),
    path("books/import/", views.bulk_import_books, name="bulk_import_books"),
    path("books/export/", views.export_books, name="export_books"),
    # Category Management
    path("categories/", views.categories_list, name="categories_list"),
    path("categories/add/", views.add_category, name="add_category"),
    path(
        "categories/<uuid:category_id>/edit/",
        views.edit_category,
        name="edit_category",
    ),
    path(
        "categories/<uuid:category_id>/delete/",
        views.delete_category,
        name="delete_category",
    ),
    # Author Management
    path("authors/<uuid:author_id>/edit/", views.edit_author, name="edit_author"),
    path("authors/<uuid:author_id>/delete/", views.delete_author, name="delete_author"),
    path(
        "authors/<uuid:author_id>/toggle-status/",
        views.toggle_author_status,
        name="toggle_author_status",
    ),
    # Publisher Management
    path(
        "publishers/<uuid:publisher_id>/edit/",
        views.edit_publisher,
        name="edit_publisher",
    ),
    path(
        "publishers/<uuid:publisher_id>/delete/",
        views.delete_publisher,
        name="delete_publisher",
    ),
    path(
        "publishers/<uuid:publisher_id>/toggle-status/",
        views.toggle_publisher_status,
        name="toggle_publisher_status",
    ),
    # Transaction Management
    path(
        "transactions/<uuid:transaction_id>/mark-lost/",
        views.mark_book_lost,
        name="mark_book_lost",
    ),
    path(
        "transactions/<uuid:transaction_id>/waive-fine/",
        views.waive_fine,
        name="waive_fine",
    ),
    path(
        "transactions/<uuid:transaction_id>/pay-fine/",
        views.pay_fine,
        name="pay_fine",
    ),
    path(
        "transactions/<uuid:transaction_id>/extend-due-date/",
        views.extend_due_date,
        name="extend_due_date",
    ),
    path(
        "transactions/bulk-return/", views.bulk_return_books, name="bulk_return_books"
    ),
    # Advanced Search
    path("search/advanced/", views.advanced_search, name="advanced_search"),
    # User Profile
    path(
        "profile/borrowing-history/",
        views.user_borrowing_history,
        name="user_borrowing_history",
    ),
    path(
        "profile/reservation-history/",
        views.user_reservation_history,
        name="user_reservation_history",
    ),
    path("profile/export-data/", views.export_user_data, name="export_user_data"),
    # Notifications
    path(
        "notifications/<uuid:notification_id>/read/",
        views.mark_notification_read,
        name="mark_notification_read",
    ),
    path(
        "notifications/<uuid:notification_id>/delete/",
        views.delete_notification,
        name="delete_notification",
    ),
    path("notifications/", views.user_notifications, name="user_notifications"),
]
