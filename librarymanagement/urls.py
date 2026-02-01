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
    path("settings/", views.library_settings, name="library_settings"),
]
