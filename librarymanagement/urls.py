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
    path("books/", views.books_list, name="books_list"),
    path("books/add/", views.add_book, name="add_book"),
    path("transactions/", views.transactions_list, name="transactions_list"),
    path("reservations/", views.reservations_list, name="reservations_list"),
    path("user-activity/", views.user_activities, name="user_activities"),
    path(
        "authors-publishers/",
        views.authors_publishers_management,
        name="authors_publishers_management",
    ),
    path(
        "recommendations/",
        views.recommendations_dashboard,
        name="recommendations_dashboard",
    ),
    path("trending/", views.trending_books, name="trending_books"),
    path("reports/", views.reports_dashboard, name="reports_dashboard"),
    path("settings/", views.library_settings, name="library_settings"),
]
