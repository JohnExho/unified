# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.contrib import messages
from librarymanagement.services import (
    CategoryServices,
    BookServices,
    AuthorServices,
    PublisherServices,
    TransactionServices,
    ReservationServices,
    NotificationServices,
    DashboardServices,
)
from django.db import transaction
from django.contrib import messages
from django.views.decorators.http import require_POST, require_http_methods
import uuid
from datetime import timedelta
from django.utils import timezone

from librarymanagement.forms import (
    BookForm,
    AuthorForm,
    PublisherForm,
    BorrowingTransactionForm,
    ReturnBookForm,
    RenewBookForm,
    ReservationForm,
)
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


def dashboard(request):
    """Library dashboard"""
    system_name = "librarymanagement"

    libraries = Library.objects.all()
    systems = request.session.get("accessible_systems", [])

    # Get activity days from query params, default to 7
    activity_days = int(request.GET.get("days", 7))

    # Get dashboard statistics using DashboardServices
    stats = DashboardServices.get_overview_stats()
    recent_transactions = DashboardServices.get_recent_transactions(limit=4)
    popular_books = DashboardServices.get_popular_books(limit=4)
    activity_summary = DashboardServices.get_activity_summary(days=activity_days)

    return render(
        request,
        "librarymanagement/dashboard.html",
        {
            "libraries": libraries,
            "systems": systems,
            "system_name": system_name,
            "user": request.user,
            # Statistics
            "total_books": stats["total_books"],
            "available_books": stats["available_books"],
            "borrowed_books": stats["borrowed_books"],
            "overdue_books": stats["overdue_books"],
            # Recent data
            "recent_transactions": recent_transactions,
            "popular_books": popular_books,
            # Activity summary
            "activity_summary": activity_summary,
        },
    )


# Main Modules
def books_list(request):
    """List all books"""
    books = (
        Book.objects.all()
        .select_related("library", "publisher")
        .prefetch_related("authors", "categories")
    )
    categories = Category.objects.all()
    authors = Author.objects.all()
    publishers = Publisher.objects.all()
    libraries = Library.objects.all()

    # Calculate statistics
    total_books = books.count()
    available_books = books.filter(status="available").count()
    borrowed_books = books.filter(status="borrowed").count()
    reserved_books = books.filter(status="reserved").count()

    context = {
        "books": books,
        "categories": categories,
        "authors": authors,
        "publishers": publishers,
        "libraries": libraries,
        "total_books": total_books,
        "available_books": available_books,
        "borrowed_books": borrowed_books,
        "reserved_books": reserved_books,
    }
    return render(request, "librarymanagement/pages/books_list.html", context)


def transactions_list(request):
    """List borrowing transactions"""
    from django.utils import timezone
    from django.db.models import Q

    transactions = (
        BorrowingTransaction.objects.all()
        .select_related("user", "book", "issued_by")
        .order_by("-borrowed_date")
    )

    # Get today's date range
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = timezone.now().replace(
        hour=23, minute=59, second=59, microsecond=999999
    )

    context = {
        "transactions": transactions,
        "active_count": transactions.filter(status="active").count(),
        "overdue_count": transactions.filter(status="overdue").count(),
        "returned_today_count": transactions.filter(
            status="returned",
            return_date__gte=today_start,
            return_date__lte=today_end,
        ).count(),
    }

    return render(
        request,
        "librarymanagement/pages/transactions_list.html",
        context,
    )


def reservations_list(request):
    """List reservations"""
    reservations = (
        Reservation.objects.all()
        .select_related("user", "book")
        .prefetch_related("book__authors")
        .order_by("-reservation_date")
    )

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
    activities = (
        UserActivity.objects.all()
        .select_related("user", "book")
        .order_by("-timestamp")[:100]
    )
    view_count = UserActivity.objects.filter(activity_type="view").count()
    search_count = UserActivity.objects.filter(activity_type="search").count()
    borrow_count = UserActivity.objects.filter(activity_type="borrow").count()
    reserve_count = UserActivity.objects.filter(activity_type="reserve").count()

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
    recommendations = (
        BookRecommendation.objects.all()
        .select_related("user", "book")
        .prefetch_related("book__authors")
        .order_by("-score", "-created_at")[:50]
    )
    actioned_count = BookRecommendation.objects.filter(actioned=True).count()
    total_count = BookRecommendation.objects.count()
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
    # Get period type from query params, default to weekly
    period_type = request.GET.get("period", "weekly")

    trending = (
        TrendingBook.objects.filter(period_type=period_type)
        .select_related("book")
        .prefetch_related("book__authors")
        .order_by("-popularity_score", "-period_start")[:20]
    )

    return render(
        request,
        "librarymanagement/pages/trending_books.html",
        {
            "trending": trending,
            "period_type": period_type,
        },
    )


def reports_dashboard(request):
    """Reports dashboard with report generation"""
    from librarymanagement.models import LibraryReport
    from librarymanagement.forms import LibraryReportForm
    from librarymanagement.services import ReportServices

    if request.method == "POST":
        form = LibraryReportForm(request.POST)
        if form.is_valid():
            try:
                report = ReportServices.generate_report(
                    report_type=form.cleaned_data["report_type"],
                    title=form.cleaned_data.get("title"),
                    period_start=form.cleaned_data["period_start"],
                    period_end=form.cleaned_data["period_end"],
                    generated_by=request.user,
                )
                messages.success(
                    request, f"Report '{report.title}' has been generated successfully!"
                )
            except Exception as e:
                messages.error(request, f"Error generating report: {str(e)}")
        else:
            messages.error(request, "Please correct the errors in the form.")

        return redirect("librarymanagement:reports_dashboard")

    # GET request - display dashboard
    recent_reports = LibraryReport.objects.all().select_related("generated_by")[:10]
    report_stats = ReportServices.get_report_statistics()

    context = {
        "recent_reports": recent_reports,
        "report_stats": report_stats,
    }

    return render(request, "librarymanagement/pages/reports_dashboard.html", context)


def library_settings(request):
    """User profile and settings page"""
    from django.contrib.auth import update_session_auth_hash
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "update_profile":
            # Update profile information
            try:
                user = request.user
                user.email = request.POST.get("email", user.email)
                user.first_name = request.POST.get("first_name", "")
                user.middle_name = request.POST.get("middle_name", "")
                user.last_name = request.POST.get("last_name", "")
                user.phone_number = request.POST.get("phone_number", "")
                user.bio = request.POST.get("bio", "")

                # Handle avatar upload
                if request.FILES.get("avatar"):
                    user.avatar = request.FILES["avatar"]

                user.save()
                messages.success(request, "Profile updated successfully!")
            except Exception as e:
                messages.error(request, f"Error updating profile: {str(e)}")

        elif action == "change_password":
            # Change password
            try:
                user = request.user
                current_password = request.POST.get("current_password")
                new_password = request.POST.get("new_password")
                confirm_password = request.POST.get("confirm_password")

                # Verify current password
                if not user.check_password(current_password):
                    messages.error(request, "Current password is incorrect.")
                    return redirect("librarymanagement:library_settings")

                # Check if new passwords match
                if new_password != confirm_password:
                    messages.error(request, "New passwords do not match.")
                    return redirect("librarymanagement:library_settings")

                # Validate new password
                try:
                    validate_password(new_password, user)
                except ValidationError as e:
                    messages.error(request, " ".join(e.messages))
                    return redirect("librarymanagement:library_settings")

                # Set new password
                user.set_password(new_password)
                user.save()

                # Update session to prevent logout
                update_session_auth_hash(request, user)

                messages.success(request, "Password changed successfully!")
            except Exception as e:
                messages.error(request, f"Error changing password: {str(e)}")

        return redirect("librarymanagement:library_settings")

    # GET request - display settings page
    # Get user statistics
    user_stats = {
        "total_borrowed": BorrowingTransaction.objects.filter(
            user=request.user
        ).count(),
        "currently_reading": BorrowingTransaction.objects.filter(
            user=request.user, status__in=["active", "overdue"]
        ).count(),
        "total_reservations": Reservation.objects.filter(user=request.user).count(),
        "overdue_books": BorrowingTransaction.objects.filter(
            user=request.user, status="overdue"
        ).count(),
    }

    context = {
        "user_stats": user_stats,
    }

    return render(request, "librarymanagement/pages/user-settings.html", context)


@require_POST
def add_library(request):
    """Add a new library"""
    name = request.POST.get("name", "").strip()
    location = request.POST.get("location", "").strip()
    contact_email = request.POST.get("contact_email", "").strip()
    contact_phone = request.POST.get("contact_phone", "").strip()
    description = request.POST.get("description", "").strip()

    if not name:
        messages.error(request, "Library name is required.")
        return redirect("librarymanagement:books_list")

    try:
        # Check if library with same name already exists
        if Library.objects.filter(name__iexact=name).exists():
            messages.warning(
                request, f"A library with the name '{name}' already exists."
            )
            return redirect("librarymanagement:books_list")

        # Create new library
        library = Library.objects.create(
            name=name,
            location=location,
            contact_email=contact_email,
            contact_phone=contact_phone,
            description=description,
        )

        messages.success(
            request, f"Library '{library.name}' has been added successfully!"
        )
    except Exception as e:
        messages.error(request, f"Error adding library: {str(e)}")

    return redirect("librarymanagement:books_list")


@require_POST
def add_book(request):
    """Add a new book to the library"""
    book, errors = BookServices.create_book_from_request(request.POST, request.user)

    if errors:
        # Display all validation errors
        for error in errors:
            messages.error(request, error)
        return redirect("librarymanagement:books_list")

    messages.success(request, f"Book '{book.title}' has been added successfully!")
    return redirect("librarymanagement:books_list")


@require_POST
def create_transaction(request):
    """Create a new borrowing transaction"""
    from librarymanagement.forms import BorrowingTransactionForm

    form = BorrowingTransactionForm(request.POST)

    if form.is_valid():
        try:
            # Use service layer for business logic
            transaction = TransactionServices.create_transaction(
                form=form, user=request.user, issued_by=request.user
            )

            messages.success(
                request,
                f"Book '{transaction.book.title}' has been borrowed successfully! Due date: {transaction.due_date.strftime('%B %d, %Y')}",
            )
            return redirect("librarymanagement:transactions_list")

        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"Error creating transaction: {str(e)}")
    else:
        # Display form validation errors
        for field, errors in form.errors.items():
            for error in errors:
                if field == "__all__":
                    messages.error(request, str(error))
                else:
                    field_name = (
                        form.fields.get(field).label if field in form.fields else field
                    )
                    messages.error(request, f"{field_name}: {error}")

    return redirect("librarymanagement:books_list")


@require_POST
def add_author(request):
    # Get form fields
    first_name = request.POST.get("first_name", "").strip()
    last_name = request.POST.get("last_name", "").strip()
    middle_name = request.POST.get("middle_name", "").strip()
    birth_date = request.POST.get("birth_date", None)
    nationality = request.POST.get("nationality", "").strip()
    bio = request.POST.get("bio", "").strip()

    if not first_name or not last_name:
        messages.error(request, "First name and last name are required.")
        return redirect("librarymanagement:authors_publishers_management")

    try:
        # Check if author already exists
        author, created = Author.objects.get_or_create(
            first_name=first_name,
            last_name=last_name,
            defaults={
                "middle_name": middle_name,
                "birth_date": birth_date if birth_date else None,
                "nationality": nationality,
                "bio": bio,
            },
        )

        if created:
            messages.success(
                request, f"Author '{author.full_name}' has been added successfully!"
            )
        else:
            messages.info(request, f"Author '{author.full_name}' already exists.")
    except Exception as e:
        messages.error(request, f"Error adding author: {str(e)}")

    return redirect("librarymanagement:authors_publishers_management")


@require_POST
def add_publisher(request):
    # Get form fields
    name = request.POST.get("name", "").strip()
    address = request.POST.get("address", "").strip()
    website = request.POST.get("website", "").strip()
    email = request.POST.get("email", "").strip()

    if not name:
        messages.error(request, "Publisher name is required.")
        return redirect("librarymanagement:authors_publishers_management")

    try:
        # Check if publisher already exists
        publisher, created = Publisher.objects.get_or_create(
            name=name,
            defaults={
                "address": address,
                "website": website,
                "email": email,
            },
        )

        if created:
            messages.success(
                request, f"Publisher '{publisher.name}' has been added successfully!"
            )
        else:
            messages.info(request, f"Publisher '{publisher.name}' already exists.")
    except Exception as e:
        messages.error(request, f"Error adding publisher: {str(e)}")

    return redirect("librarymanagement:authors_publishers_management")


@require_POST
def return_book(request, transaction_id):
    try:
        apply_fine = request.POST.get("apply_fine", "false") == "true"
        condition_notes = request.POST.get("condition_notes", "")

        borrowing_transaction = TransactionServices.return_book(
            transaction_id=transaction_id,
            return_date=timezone.now(),
            condition_notes=condition_notes,
            apply_fine=apply_fine,
        )

        fine_message = (
            f" Fine applied: ₱{borrowing_transaction.fine_amount}"
            if borrowing_transaction.fine_amount > 0
            else ""
        )
        messages.success(
            request,
            f"Book '{borrowing_transaction.book.title}' has been returned successfully!{fine_message}",
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Book returned successfully",
                "fine_amount": str(borrowing_transaction.fine_amount),
            }
        )
    except ValueError as e:
        messages.error(request, str(e))
        return JsonResponse({"success": False, "message": str(e)}, status=400)
    except Exception as e:
        messages.error(request, f"Error returning book: {str(e)}")
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@require_POST
def renew_book(request, transaction_id):
    try:
        extend_days = int(request.POST.get("extend_days", 14))

        borrowing_transaction = TransactionServices.renew_transaction(
            transaction_id=transaction_id, extend_days=extend_days
        )

        messages.success(
            request,
            f"Book '{borrowing_transaction.book.title}' has been renewed! New due date: {borrowing_transaction.due_date.strftime('%B %d, %Y')}",
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Book renewed successfully",
                "new_due_date": borrowing_transaction.due_date.isoformat(),
            }
        )
    except ValueError as e:
        messages.error(request, str(e))
        return JsonResponse({"success": False, "message": str(e)}, status=400)
    except Exception as e:
        messages.error(request, f"Error renewing book: {str(e)}")
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@require_POST
def mark_reservation_ready(request, reservation_id):
    try:
        notify = request.POST.get("notify", "true") == "true"

        reservation = ReservationServices.mark_reservation_ready(
            reservation_id=reservation_id, notify=notify
        )

        messages.success(
            request,
            f"Reservation for '{reservation.book.title}' has been marked as ready!",
        )

        return JsonResponse({"success": True, "message": "Reservation marked as ready"})
    except ValueError as e:
        messages.error(request, str(e))
        return JsonResponse({"success": False, "message": str(e)}, status=400)
    except Exception as e:
        messages.error(request, f"Error marking reservation ready: {str(e)}")
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@require_POST
def fulfill_reservation(request, reservation_id):
    try:
        borrowing_transaction, reservation = ReservationServices.fulfill_reservation(
            reservation_id=reservation_id, issued_by=request.user
        )

        messages.success(
            request,
            f"Reservation fulfilled! Book '{reservation.book.title}' has been checked out to {reservation.user.username}.",
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Reservation fulfilled successfully",
                "transaction_id": str(borrowing_transaction.id),
            }
        )
    except ValueError as e:
        messages.error(request, str(e))
        return JsonResponse({"success": False, "message": str(e)}, status=400)
    except Exception as e:
        messages.error(request, f"Error fulfilling reservation: {str(e)}")
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@require_POST
def cancel_reservation(request, reservation_id):
    try:
        reason = request.POST.get("reason", "")

        reservation = ReservationServices.cancel_reservation(
            reservation_id=reservation_id, reason=reason
        )

        messages.success(
            request, f"Reservation for '{reservation.book.title}' has been cancelled."
        )

        return JsonResponse(
            {"success": True, "message": "Reservation cancelled successfully"}
        )
    except ValueError as e:
        messages.error(request, str(e))
        return JsonResponse({"success": False, "message": str(e)}, status=400)
    except Exception as e:
        messages.error(request, f"Error cancelling reservation: {str(e)}")
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@require_POST
def notify_user_reservation(request, reservation_id):
    try:
        reservation = get_object_or_404(Reservation, id=reservation_id)

        # Create notification
        notification = NotificationServices.create_reservation_ready_notification(
            reservation
        )

        # Update reservation
        reservation.notified = True
        reservation.notified_at = timezone.now()
        reservation.save()

        messages.success(request, f"Notification sent to {reservation.user.username}!")

        return JsonResponse({"success": True, "message": "User notified successfully"})
    except Exception as e:
        messages.error(request, f"Error sending notification: {str(e)}")
        return JsonResponse({"success": False, "message": str(e)}, status=500)


def transaction_detail(request, transaction_id):
    transaction_obj = get_object_or_404(BorrowingTransaction, id=transaction_id)

    context = {
        "transaction": transaction_obj,
    }

    return render(request, "librarymanagement/pages/transaction_detail.html", context)
