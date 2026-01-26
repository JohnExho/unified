# views.py
from django.shortcuts import render
from django.http import HttpResponse
from .models import (
    Library,
    Book,
    BorrowingTransaction,
    Reservation,
    UserActivity,
    BookRecommendation,
    TrendingBook,
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
    return render(request, "librarymanagement/pages/books_list.html", {"books": books})


def transactions_list(request):
    """List borrowing transactions"""
    transactions = BorrowingTransaction.objects.all()
    return render(
        request,
        "librarymanagement/transactions_list.html",
        {"transactions": transactions},
    )


def reservations_list(request):
    """List reservations"""
    reservations = Reservation.objects.all()
    return render(
        request,
        "librarymanagement/reservations_list.html",
        {"reservations": reservations},
    )


def user_activities(request):
    """Track user activity"""
    activities = UserActivity.objects.all()
    return render(
        request, "librarymanagement/user_activities.html", {"activities": activities}
    )


def recommendations_dashboard(request):
    """Book recommendations"""
    recommendations = BookRecommendation.objects.all()
    return render(
        request,
        "librarymanagement/recommendations_dashboard.html",
        {"recommendations": recommendations},
    )


def trending_books(request):
    """Trending / popular books"""
    trending = TrendingBook.objects.all()
    return render(
        request, "librarymanagement/trending_books.html", {"trending": trending}
    )


def reports_dashboard(request):
    """Reports dashboard"""
    return HttpResponse("Reports dashboard coming soon.")


def library_settings(request):
    """Library system settings"""
    return HttpResponse("Settings page coming soon.")
