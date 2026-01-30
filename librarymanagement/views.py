def authors_publishers_management(request):
    """Manage authors and publishers"""
    authors = Author.objects.all()
    publishers = Publisher.objects.all()
    return render(
        request,
        "librarymanagement/pages/authors_publishers.html",
        {
            "authors": authors,
            "publishers": publishers,
        },
    )


# views.py
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.contrib import messages
from librarymanagement.services import CategoryServices
from django.db import transaction
from django.contrib import messages
from django.views.decorators.http import require_POST
import uuid

from librarymanagement.forms import BookForm
from librarymanagement.services import BookServices
from .models import (
    Library,
    Book,
    BorrowingTransaction,
    Reservation,
    UserActivity,
    BookRecommendation,
    TrendingBook,
    Author,
    Publisher,
    Category,
)


def dashboard(request):
    """Library dashboard"""
    system_name = "librarymanagement"

    libraries = Library.objects.all()
    systems = request.session.get("accessible_systems", [])
    return render(
        request,
        "librarymanagement/dashboard.html",
        {
            "libraries": libraries,
            "systems": systems,
            "system_name": system_name,
            "user": request.user,
        },
    )


# Main Modules
def books_list(request):
    """List all books"""
    books = Book.objects.all()
    categories = Category.objects.all()
    authors = Author.objects.all()
    publishers = Publisher.objects.all()
    libraries = Library.objects.all()

    context = {
        "books": books,
        "categories": categories,
        "authors": authors,
        "publishers": publishers,
        "libraries": libraries,
    }
    return render(request, "librarymanagement/pages/books_list.html", context)


def transactions_list(request):
    """List borrowing transactions"""
    from django.utils import timezone

    transactions = BorrowingTransaction.objects.all()

    context = {
        "transactions": transactions,
        "active_count": transactions.count(),
        "overdue_count": transactions.filter(status="overdue").count(),
        "returned_today_count": transactions.filter(
            status="returned",
            return_date=timezone.now().date(),
        ).count(),
    }

    return render(
        request,
        "librarymanagement/pages/transactions_list.html",
        context,
    )


def reservations_list(request):
    """List reservations"""
    reservations = Reservation.objects.all()
    pending_count = reservations.filter(status="pending").count()
    ready_count = reservations.filter(status="ready").count()
    fulfilled_count = reservations.filter(status="fulfilled").count()
    expired_count = reservations.filter(status="expired").count()
    return render(
        request,
        "librarymanagement/pages/reservations_list.html",
        {
            "reservations": reservations,
            "pending_count": pending_count,
            "ready_count": ready_count,
            "fulfilled_count": fulfilled_count,
            "expired_count": expired_count,
        },
    )


def user_activities(request):
    """Track user activity"""
    activities = UserActivity.objects.all()
    view_count = activities.filter(activity_type="view").count()
    search_count = activities.filter(activity_type="search").count()
    borrow_count = activities.filter(activity_type="borrow").count()
    reserve_count = activities.filter(activity_type="reserve").count()
    return render(
        request,
        "librarymanagement/pages/user_activities.html",
        {
            "activities": activities,
            "view_count": view_count,
            "search_count": search_count,
            "borrow_count": borrow_count,
            "reserve_count": reserve_count,
        },
    )


def recommendations_dashboard(request):
    """Book recommendations"""
    recommendations = BookRecommendation.objects.all()
    actioned_count = recommendations.filter(actioned=True).count()
    total_count = recommendations.count()
    success_rate = int((actioned_count / total_count) * 100) if total_count > 0 else 0
    return render(
        request,
        "librarymanagement/pages/recommendations_dashboard.html",
        {
            "recommendations": recommendations,
            "actioned_count": actioned_count,
            "success_rate": success_rate,
            "total_count": total_count,
        },
    )


def trending_books(request):
    """Trending / popular books"""
    trending = TrendingBook.objects.all()
    return render(
        request, "librarymanagement/pages/trending_books.html", {"trending": trending}
    )


def reports_dashboard(request):
    """Reports dashboard"""
    return HttpResponse("Reports dashboard coming soon.")


def library_settings(request):
    """Library system settings"""
    return HttpResponse("Settings page coming soon.")


@require_POST
def add_book(request):
    form = BookForm(request.POST)

    if not form.is_valid():
        messages.error(request, "Please correct the errors in the form.")
        return redirect("librarymanagement:books_list")

    category_names = form.cleaned_data.get("categories", [])
    categories = CategoryServices.get_or_create_categories_from_strings(category_names)
    form.cleaned_data["categories"] = categories

    book = BookServices.create_book(form, request.user)

    messages.success(request, f"Book '{book.title}' has been added successfully!")
    return redirect("librarymanagement:books_list")
