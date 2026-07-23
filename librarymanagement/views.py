# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from core.decorators import require_system_role

from core.services import Services
from librarymanagement.services import (
    BookServices,
    TransactionServices,
    ReservationServices,
    NotificationServices,
    DashboardServices,
    ReportServices,
    RecommendationServices,
    LibrarySettingsServices,
    DataMiningServices,
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


@login_required(login_url="/librarymanagement/login")
@require_system_role(["admin", "superadmin"])
def authors_publishers_management(request):
    if not Services.has_access(request.user, "librarymanagement"):
        return render(request, "404.html", status=404)

    """Manage authors and publishers"""
    authors = Author.objects.all()
    publishers = Publisher.objects.all()

    # Calculate statistics
    total_authors = authors.count()
    active_authors = authors.filter(active=True).count()
    total_publishers = publishers.count()
    active_publishers = publishers.filter(active=True).count()

    return render(
        request,
        "librarymanagement/pages/authors_publishers.html",
        {
            "authors": authors,
            "publishers": publishers,
            "total_authors": total_authors,
            "active_authors": active_authors,
            "total_publishers": total_publishers,
            "active_publishers": active_publishers,
        },
    )


@login_required(login_url="/librarymanagement/login")
@require_system_role(["user", "admin", "superadmin"])
def dashboard(request):
    """Library dashboard"""

    system_name = "librarymanagement"

    libraries = Library.objects.all()
    systems = request.session.get("accessible_systems", [])

    if not Services.has_access(request.user, "librarymanagement"):
        return render(request, "404.html", status=404)

    # Get activity days from query params, default to 7
    activity_days = int(request.GET.get("days", 7))

    # Get dashboard statistics using DashboardServices
    stats = DashboardServices.get_overview_stats()
    recent_transactions = DashboardServices.get_recent_transactions(limit=4)
    popular_books = DashboardServices.get_popular_books(limit=4)

    library = Library.objects.first()
    settings = (
        LibrarySettingsServices.get_or_create_settings(library) if library else None
    )
    if settings and not settings.enable_user_analytics:
        activity_summary = {
            "borrowed_count": 0,
            "borrowed_percentage": 0,
            "returned_count": 0,
            "returned_percentage": 0,
            "reservations_count": 0,
            "reservations_percentage": 0,
            "days": activity_days,
        }
        activity_disabled_message = (
            "User activity tracking is disabled in Library Settings. "
            "Enable it to see analytics and usage panels."
        )
    else:
        activity_summary = DashboardServices.get_activity_summary(days=activity_days)
        activity_disabled_message = None

    demand_forecast_snapshot = DataMiningServices.get_demand_forecast_snapshot(limit=5)
    can_train_forecast_model = (
        request.user.is_superuser
        or Services.has_access(
            request.user,
            "librarymanagement",
            role="admin",
        )
        or Services.has_access(
            request.user,
            "librarymanagement",
            role="superadmin",
        )
    )

    return render(
        request,
        "librarymanagement/pages/dashboard.html",
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
            "activity_tracking_enabled": not settings or settings.enable_user_analytics,
            "activity_disabled_message": activity_disabled_message,
            # Random Forest demand forecasting
            "demand_forecasts": demand_forecast_snapshot["forecasts"],
            "rf_model_ready": demand_forecast_snapshot["model_ready"],
            "demand_uses_fallback": demand_forecast_snapshot["uses_fallback"],
            "can_train_forecast_model": can_train_forecast_model,
        },
    )


@login_required(login_url="/librarymanagement/login")
@require_system_role(["admin", "superadmin"])
@require_POST
def train_demand_forecast_model(request):
    """Train Random Forest demand forecasting model from dashboard action."""
    days_raw = request.POST.get("days", "90")

    try:
        days = int(days_raw)
    except (TypeError, ValueError):
        days = 90

    if days <= 0:
        days = 90

    result = DataMiningServices.train_random_forest_demand_model(period_days=days)

    if result.get("trained"):
        accuracy = result.get("accuracy")
        if accuracy is not None:
            messages.success(
                request,
                f"Demand model retrained successfully (accuracy: {accuracy}).",
            )
        else:
            messages.success(request, "Demand model retrained successfully.")
    else:
        messages.warning(
            request,
            f"Model training skipped: {result.get('reason', 'insufficient data')}",
        )

    return redirect("librarymanagement:library_dashboard")


# Main Modules
@login_required(login_url="/librarymanagement/login")
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

    # Apply search and filter parameters
    search_query = request.GET.get("search", "").strip()
    category_filter = request.GET.get("category", "").strip()
    status_filter = request.GET.get("status", "").strip()
    resource_type = request.GET.get("type", "").strip()

    if search_query:
        books = books.filter(
            Q(title__icontains=search_query)
            | Q(isbn__icontains=search_query)
            | Q(authors__full_name__icontains=search_query)
            | Q(publisher__name__icontains=search_query)
        ).distinct()

    if category_filter:
        books = books.filter(categories__id=category_filter)

    if status_filter:
        books = books.filter(status=status_filter)

    if resource_type:
        books = books.filter(resource_type=resource_type)

    # Calculate statistics for the current result set
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
        "search_query": search_query,
        "category_filter": category_filter,
        "status_filter": status_filter,
        "resource_type": resource_type,
    }
    return render(request, "librarymanagement/pages/books_list.html", context)


@login_required(login_url="/librarymanagement/login")
def transactions_list(request):
    """List borrowing transactions"""
    from django.utils import timezone

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


@login_required(login_url="/librarymanagement/login")
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


@login_required(login_url="/librarymanagement/login")
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


@login_required(login_url="/librarymanagement/login")
@require_system_role(["user", "admin", "superadmin"])
def recommendations_dashboard(request):
    """Book recommendations"""
    library = Library.objects.first()
    settings = (
        LibrarySettingsServices.get_or_create_settings(library) if library else None
    )
    disabled_message = None

    if settings and not settings.enable_book_recommendations:
        recommendations = BookRecommendation.objects.none()
        disabled_message = (
            "Book recommendation functionality is disabled in Library Settings. "
            "Enable it to see AI-driven suggestions."
        )
    else:
        recommendations = (
            BookRecommendation.objects.filter(user=request.user)
            .select_related("user", "book")
            .prefetch_related("book__authors")
            .order_by("-score", "-created_at")[:50]
        )

        if not recommendations.exists():
            RecommendationServices.refresh_recommendations(request.user)
            recommendations = (
                BookRecommendation.objects.filter(user=request.user)
                .select_related("user", "book")
                .prefetch_related("book__authors")
                .order_by("-score", "-created_at")[:50]
            )

    actioned_count = (
        BookRecommendation.objects.filter(user=request.user, actioned=True).count()
    )
    total_count = BookRecommendation.objects.filter(user=request.user).count()
    success_rate = int((actioned_count / total_count) * 100) if total_count > 0 else 0

    return render(
        request,
        "librarymanagement/pages/recommendations_dashboard.html",
        {
            "recommendations": recommendations,
            "actioned_count": actioned_count,
            "success_rate": success_rate,
            "total_count": total_count,
            "recommendations_enabled": not settings or settings.enable_book_recommendations,
            "disabled_message": disabled_message,
            "view_type": "recommendations",
        },
    )


@login_required(login_url="/librarymanagement/login")
@require_system_role(["user", "admin", "superadmin"])
def refresh_recommendations(request):
    """Regenerate personalized recommendations for the current user"""
    library = Library.objects.first()
    settings = (
        LibrarySettingsServices.get_or_create_settings(library) if library else None
    )

    if settings and not settings.enable_book_recommendations:
        messages.error(
            request,
            "Book recommendation feature is disabled in Library Settings. Enable it first.",
        )
        return redirect("librarymanagement:recommendations_dashboard")

    RecommendationServices.refresh_recommendations(request.user)
    messages.success(request, "Personalized recommendations have been refreshed.")
    return redirect("librarymanagement:recommendations_dashboard")


@login_required(login_url="/librarymanagement/login")
@require_system_role(["user", "admin", "superadmin"])
def trending_books(request):
    """Trending / popular books"""
    from librarymanagement.services import LibrarySettingsServices

    library = Library.objects.first()
    settings = (
        LibrarySettingsServices.get_or_create_settings(library) if library else None
    )
    disabled_message = None

    period_type = request.GET.get("period", "weekly")

    if settings and not settings.enable_trending_analysis:
        trending = TrendingBook.objects.none()
        disabled_message = (
            "Trending analysis is disabled in Library Settings. "
            "Enable it to see popular books and trends."
        )
    else:
        trending = (
            TrendingBook.objects.filter(period_type=period_type)
            .select_related("book")
            .prefetch_related("book__authors")
            .order_by("-popularity_score", "-period_start")[:20]
        )

        if not trending.exists():
            DataMiningServices.analyze_trending_books(period_type=period_type)
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
            "trending_enabled": not settings or settings.enable_trending_analysis,
            "disabled_message": disabled_message,
            "view_type": "trending",
        },
    )


@login_required(login_url="/librarymanagement/login")
@require_system_role(["admin", "superadmin"])
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


@login_required(login_url="/librarymanagement/login")
@require_system_role(["admin", "superadmin"])
def download_report(request, report_id):
    """Download generated report in the requested format."""
    from librarymanagement.models import LibraryReport

    report = get_object_or_404(LibraryReport, id=report_id)
    export_format = request.GET.get("format", "csv")

    try:
        content, content_type, filename = ReportServices.export_report(
            report, export_format
        )
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("librarymanagement:reports_dashboard")

    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required(login_url="/librarymanagement/login")
@require_system_role(["admin", "superadmin"])
def library_settings(request):
    """Library configuration settings page"""
    library = Library.objects.first()
    settings = None
    form = None

    if library:
        settings = LibrarySettingsServices.get_or_create_settings(library)
        from librarymanagement.forms import LibrarySettingsForm

        if request.method == "POST":
            form = LibrarySettingsForm(request.POST, instance=settings)
            if form.is_valid():
                form.save()
                messages.success(request, "Library settings updated successfully!")
                return redirect("librarymanagement:library_settings")
            messages.error(request, "Please correct the errors in the form.")
        else:
            form = LibrarySettingsForm(instance=settings)
    else:
        messages.warning(request, "No library found. Please create a library first.")

    context = {
        "library": library,
        "settings": settings,
        "form": form,
    }

    return render(request, "librarymanagement/pages/library_settings.html", context)


def user_settings(request):
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
                    return redirect("librarymanagement:user_settings")

                # Check if new passwords match
                if new_password != confirm_password:
                    messages.error(request, "New passwords do not match.")
                    return redirect("librarymanagement:user_settings")

                # Validate new password
                try:
                    validate_password(new_password, user)
                except ValidationError as e:
                    messages.error(request, " ".join(e.messages))
                    return redirect("librarymanagement:user_settings")

                # Set new password
                user.set_password(new_password)
                user.save()

                # Update session to prevent logout
                update_session_auth_hash(request, user)

                messages.success(request, "Password changed successfully!")
            except Exception as e:
                messages.error(request, f"Error changing password: {str(e)}")

        return redirect("librarymanagement:user_settings")

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


@login_required(login_url="/librarymanagement/login")
def user_profile_data(request):
    """Return current user's profile data as JSON."""
    user = request.user
    avatar_url = ""
    if getattr(user, "avatar", None):
        try:
            avatar_url = user.avatar.url
        except Exception:
            avatar_url = ""
    if not avatar_url:
        avatar_url = getattr(user, "avatar_url", "") or ""

    return JsonResponse(
        {
            "success": True,
            "profile": {
                "id": str(user.id),
                "username": user.username or "",
                "email": user.email or "",
                "first_name": user.first_name or "",
                "middle_name": user.middle_name or "",
                "last_name": user.last_name or "",
                "phone_number": user.phone_number or "",
                "bio": user.bio or "",
                "avatar_url": avatar_url,
                "is_email_verified": bool(getattr(user, "is_email_verified", False)),
            },
        }
    )


@login_required(login_url="/librarymanagement/login")
def user_activity_stats(request):
    """Return current user's activity stats as JSON."""
    stats = {
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

    return JsonResponse({"success": True, "stats": stats})


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

    if book:
        messages.success(request, f"Book '{book.title}' has been added successfully!")
    else:
        messages.error(request, "Failed to create book. Please try again.")

    return redirect("librarymanagement:books_list")


@require_POST
def create_transaction(request):
    """Create a new borrowing transaction"""
    from librarymanagement.forms import BorrowingTransactionForm

    form = BorrowingTransactionForm(request.POST)

    if form.is_valid():
        try:
            # Use service layer for business logic
            transaction_obj = TransactionServices.create_transaction(
                form=form, user=request.user, issued_by=request.user
            )

            messages.success(
                request,
                f"Book '{transaction_obj.book.title}' has been borrowed successfully! Due date: {transaction_obj.due_date.strftime('%B %d, %Y')}",
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
                    field_label = (
                        form.fields[field].label if field in form.fields else field
                    )
                    messages.error(request, f"{field_label}: {error}")

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
        NotificationServices.create_reservation_ready_notification(reservation)

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


# Book Management Views
import csv
from librarymanagement.services import (
    LibrarySettingsServices,
    AdvancedSearchServices,
    UserActivityServices,
    UserProfileServices,
    TrendingServices,
    CategoryServices,
    AuthorServices,
    PublisherServices,
)


@login_required(login_url="/librarymanagement/login")
@require_system_role(["admin", "superadmin"])
def edit_book(request, book_id):
    """Edit book details"""
    book = get_object_or_404(Book, id=book_id)

    if request.method == "POST":
        try:
            files = request.FILES
            data = request.POST.dict()

            updated_book = BookServices.update_book(book_id, data, files)

            messages.success(
                request, f"Book '{updated_book.title}' updated successfully!"
            )
            return redirect("librarymanagement:books_list")

        except Exception as e:
            messages.error(request, f"Error updating book: {str(e)}")

    # GET request - render edit form
    from librarymanagement.forms import BookForm

    form = BookForm(instance=book)

    return render(
        request,
        "librarymanagement/pages/edit_book.html",
        {"form": form, "book": book},
    )


@login_required(login_url="/librarymanagement/login")
@require_system_role(["admin", "superadmin"])
@require_POST
def delete_book(request, book_id):
    """Delete a book"""
    try:
        BookServices.delete_book(book_id)
        messages.success(request, "Book deleted successfully!")
        return JsonResponse({"success": True, "message": "Book deleted"})
    except ValueError as e:
        messages.error(request, str(e))
        return JsonResponse({"success": False, "message": str(e)}, status=400)
    except Exception as e:
        messages.error(request, f"Error deleting book: {str(e)}")
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required(login_url="/librarymanagement/login")
@require_system_role(["admin", "superadmin"])
@require_POST
def toggle_book_status(request, book_id):
    """Toggle book status"""
    try:
        new_status = request.POST.get("status")
        book = BookServices.toggle_book_status(book_id, new_status)

        messages.success(request, f"Book status updated to {new_status}!")
        return JsonResponse(
            {"success": True, "message": "Status updated", "new_status": book.status}
        )
    except Exception as e:
        messages.error(request, f"Error updating status: {str(e)}")
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required(login_url="/librarymanagement/login")
@require_system_role(["admin", "superadmin"])
def bulk_import_books(request):
    """Bulk import books from CSV"""
    if request.method == "POST":
        from librarymanagement.forms import BulkBookImportForm

        form = BulkBookImportForm(request.POST, request.FILES)

        if form.is_valid():
            try:
                file = request.FILES["file"]
                library = form.cleaned_data["library"]

                # Save uploaded file temporarily
                import tempfile
                import os

                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                    for chunk in file.chunks():
                        tmp.write(chunk)
                    tmp_path = tmp.name

                # Import books
                books_created, errors = BookServices.bulk_import_books(
                    tmp_path, library, request.user
                )

                # Clean up temp file
                os.unlink(tmp_path)

                if errors:
                    messages.warning(
                        request,
                        f"Imported {len(books_created)} books with {len(errors)} errors.",
                    )
                else:
                    messages.success(
                        request, f"Successfully imported {len(books_created)} books!"
                    )

                return redirect("librarymanagement:books_list")

            except Exception as e:
                messages.error(request, f"Error importing books: {str(e)}")
    else:
        from librarymanagement.forms import BulkBookImportForm

        form = BulkBookImportForm()

    return render(
        request, "librarymanagement/pages/bulk_import_books.html", {"form": form}
    )


@login_required(login_url="/librarymanagement/login")
@require_system_role(["admin", "superadmin"])
def export_books(request):
    """Export books to the requested format"""
    try:
        library_id = request.GET.get("library_id")
        export_format = request.GET.get("format", "csv")
        content, content_type, filename = BookServices.export_books(
            library_id, export_format
        )

        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("librarymanagement:books_list")
    except Exception as e:
        messages.error(request, f"Error exporting books: {str(e)}")
        return redirect("librarymanagement:books_list")


# Category Management Views
@login_required(login_url="/librarymanagement/login")
@require_system_role(["admin", "superadmin"])
def categories_list(request):
    """List all categories"""
    categories = Category.objects.all().prefetch_related("subcategories")

    return render(
        request,
        "librarymanagement/pages/categories_list.html",
        {"categories": categories},
    )


@login_required(login_url="/librarymanagement/login")
@require_system_role(["admin", "superadmin"])
def add_category(request):
    """Add new category"""
    if request.method == "POST":
        from librarymanagement.forms import CategoryForm

        form = CategoryForm(request.POST)

        if form.is_valid():
            try:
                category = form.save()
                messages.success(
                    request, f"Category '{category.name}' created successfully!"
                )
                return redirect("librarymanagement:categories_list")
            except Exception as e:
                messages.error(request, f"Error creating category: {str(e)}")
    else:
        from librarymanagement.forms import CategoryForm

        form = CategoryForm()

    return render(request, "librarymanagement/pages/add_category.html", {"form": form})


@login_required(login_url="/librarymanagement/login")
@require_system_role(["admin", "superadmin"])
def edit_category(request, category_id):
    """Edit category"""
    category = get_object_or_404(Category, id=category_id)

    if request.method == "POST":
        from librarymanagement.forms import CategoryForm

        form = CategoryForm(request.POST, instance=category)

        if form.is_valid():
            try:
                category = form.save()
                messages.success(
                    request, f"Category '{category.name}' updated successfully!"
                )
                return redirect("librarymanagement:categories_list")
            except Exception as e:
                messages.error(request, f"Error updating category: {str(e)}")
    else:
        from librarymanagement.forms import CategoryForm

        form = CategoryForm(instance=category)

    return render(
        request,
        "librarymanagement/pages/edit_category.html",
        {"form": form, "category": category},
    )


@login_required(login_url="/librarymanagement/login")
@require_system_role(["admin", "superadmin"])
@require_POST
def delete_category(request, category_id):
    """Delete category"""
    try:
        CategoryServices.delete_category(category_id)
        messages.success(request, "Category deleted successfully!")
        return JsonResponse({"success": True, "message": "Category deleted"})
    except ValueError as e:
        messages.error(request, str(e))
        return JsonResponse({"success": False, "message": str(e)}, status=400)
    except Exception as e:
        messages.error(request, f"Error deleting category: {str(e)}")
        return JsonResponse({"success": False, "message": str(e)}, status=500)


# Author Management Views
@login_required(login_url="/librarymanagement/login")
@require_system_role(["admin", "superadmin"])
def edit_author(request, author_id):
    """Edit author"""
    author = get_object_or_404(Author, id=author_id)

    if request.method == "POST":
        from librarymanagement.forms import AuthorForm

        form = AuthorForm(request.POST, instance=author)

        if form.is_valid():
            try:
                author = AuthorServices.update_author(author, form)
                messages.success(
                    request, f"Author '{author.full_name}' updated successfully!"
                )
                return redirect("librarymanagement:authors_publishers_management")
            except Exception as e:
                messages.error(request, f"Error updating author: {str(e)}")
    else:
        from librarymanagement.forms import AuthorForm

        form = AuthorForm(instance=author)

    return render(
        request,
        "librarymanagement/pages/edit_author.html",
        {"form": form, "author": author},
    )


@login_required(login_url="/librarymanagement/login")
@require_system_role(["admin", "superadmin"])
@require_POST
def delete_author(request, author_id):
    """Delete author"""
    try:
        AuthorServices.delete_author(author_id)
        messages.success(request, "Author deleted successfully!")
        return JsonResponse({"success": True, "message": "Author deleted"})
    except ValueError as e:
        messages.error(request, str(e))
        return JsonResponse({"success": False, "message": str(e)}, status=400)
    except Exception as e:
        messages.error(request, f"Error deleting author: {str(e)}")
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required(login_url="/librarymanagement/login")
@require_system_role(["admin", "superadmin"])
@require_POST
def toggle_author_status(request, author_id):
    """Toggle author status"""
    try:
        author = AuthorServices.toggle_author_status(author_id)
        messages.success(request, f"Author status updated!")
        return JsonResponse(
            {"success": True, "message": "Status toggled", "active": author.active}
        )
    except Exception as e:
        messages.error(request, f"Error toggling status: {str(e)}")
        return JsonResponse({"success": False, "message": str(e)}, status=500)


# Publisher Management Views
@login_required(login_url="/librarymanagement/login")
@require_system_role(["admin", "superadmin"])
def edit_publisher(request, publisher_id):
    """Edit publisher"""
    publisher = get_object_or_404(Publisher, id=publisher_id)

    if request.method == "POST":
        from librarymanagement.forms import PublisherForm

        form = PublisherForm(request.POST, instance=publisher)

        if form.is_valid():
            try:
                publisher = PublisherServices.update_publisher(publisher, form)
                messages.success(
                    request, f"Publisher '{publisher.name}' updated successfully!"
                )
                return redirect("librarymanagement:authors_publishers_management")
            except Exception as e:
                messages.error(request, f"Error updating publisher: {str(e)}")
    else:
        from librarymanagement.forms import PublisherForm

        form = PublisherForm(instance=publisher)

    return render(
        request,
        "librarymanagement/pages/edit_publisher.html",
        {"form": form, "publisher": publisher},
    )


@login_required(login_url="/librarymanagement/login")
@require_system_role(["admin", "superadmin"])
@require_POST
def delete_publisher(request, publisher_id):
    """Delete publisher"""
    try:
        PublisherServices.delete_publisher(publisher_id)
        messages.success(request, "Publisher deleted successfully!")
        return JsonResponse({"success": True, "message": "Publisher deleted"})
    except ValueError as e:
        messages.error(request, str(e))
        return JsonResponse({"success": False, "message": str(e)}, status=400)
    except Exception as e:
        messages.error(request, f"Error deleting publisher: {str(e)}")
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required(login_url="/librarymanagement/login")
@require_system_role(["admin", "superadmin"])
@require_POST
def toggle_publisher_status(request, publisher_id):
    """Toggle publisher status"""
    try:
        publisher = PublisherServices.toggle_publisher_status(publisher_id)
        messages.success(request, "Publisher status updated!")
        return JsonResponse(
            {"success": True, "message": "Status toggled", "active": publisher.active}
        )
    except Exception as e:
        messages.error(request, f"Error toggling status: {str(e)}")
        return JsonResponse({"success": False, "message": str(e)}, status=500)


# Transaction Management Views
@login_required(login_url="/librarymanagement/login")
@require_system_role(["admin", "superadmin"])
@require_POST
def mark_book_lost(request, transaction_id):
    """Mark book as lost"""
    try:
        notes = request.POST.get("notes", "")
        trans = TransactionServices.mark_book_lost(transaction_id, notes)

        messages.success(request, "Transaction marked as lost!")
        return JsonResponse({"success": True, "message": "Book marked as lost"})
    except Exception as e:
        messages.error(request, f"Error marking book as lost: {str(e)}")
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required(login_url="/librarymanagement/login")
@require_system_role(["admin", "superadmin"])
@require_POST
def waive_fine(request, transaction_id):
    """Waive fine"""
    try:
        from librarymanagement.forms import WaiveFineForm

        form = WaiveFineForm(request.POST)

        if form.is_valid():
            waive_amount = form.cleaned_data.get("waive_amount")
            reason = form.cleaned_data["reason"]

            trans = TransactionServices.waive_fine(transaction_id, waive_amount, reason)

            messages.success(request, "Fine waived successfully!")
            return JsonResponse(
                {
                    "success": True,
                    "message": "Fine waived",
                    "remaining_fine": str(trans.fine_amount),
                }
            )
        else:
            return JsonResponse(
                {"success": False, "message": "Invalid form data"}, status=400
            )
    except Exception as e:
        messages.error(request, f"Error waiving fine: {str(e)}")
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required(login_url="/librarymanagement/login")
@require_system_role(["admin", "superadmin"])
@require_POST
def pay_fine(request, transaction_id):
    """Record fine payment"""
    try:
        from librarymanagement.forms import FinePaymentForm

        form = FinePaymentForm(request.POST)

        if form.is_valid():
            amount_paid = form.cleaned_data["amount_paid"]
            payment_method = form.cleaned_data["payment_method"]

            trans = TransactionServices.pay_fine(
                transaction_id, amount_paid, payment_method
            )

            messages.success(request, "Payment recorded successfully!")
            return JsonResponse(
                {
                    "success": True,
                    "message": "Payment recorded",
                    "remaining_fine": str(trans.fine_amount),
                }
            )
        else:
            return JsonResponse(
                {"success": False, "message": "Invalid form data"}, status=400
            )
    except Exception as e:
        messages.error(request, f"Error recording payment: {str(e)}")
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required(login_url="/librarymanagement/login")
@require_system_role(["admin", "superadmin"])
@require_POST
def extend_due_date(request, transaction_id):
    """Extend due date"""
    try:
        additional_days = int(request.POST.get("additional_days", 7))

        trans = TransactionServices.extend_due_date(transaction_id, additional_days)

        messages.success(request, "Due date extended successfully!")
        return JsonResponse(
            {
                "success": True,
                "message": "Due date extended",
                "new_due_date": trans.due_date.isoformat(),
            }
        )
    except Exception as e:
        messages.error(request, f"Error extending due date: {str(e)}")
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required(login_url="/librarymanagement/login")
@require_system_role(["admin", "superadmin"])
@require_POST
def bulk_return_books(request):
    """Bulk return books"""
    try:
        transaction_ids = request.POST.get("transaction_ids", "").split(",")
        transaction_ids = [tid.strip() for tid in transaction_ids if tid.strip()]

        results = TransactionServices.bulk_return_books(transaction_ids)

        messages.success(
            request,
            f"Returned {len(results['success'])} books successfully! {len(results['errors'])} errors.",
        )
        return JsonResponse(
            {
                "success": True,
                "message": "Bulk return completed",
                "results": {
                    "success_count": len(results["success"]),
                    "error_count": len(results["errors"]),
                },
            }
        )
    except Exception as e:
        messages.error(request, f"Error bulk returning books: {str(e)}")
        return JsonResponse({"success": False, "message": str(e)}, status=500)


# Library Settings Views
@login_required(login_url="/librarymanagement/login")
@require_system_role(["admin", "superadmin"])
def manage_library_settings(request):
    """Manage library settings"""
    library = Library.objects.first()  # Get first library or handle multiple
    settings = LibrarySettingsServices.get_or_create_settings(library)

    if request.method == "POST":
        from librarymanagement.forms import LibrarySettingsForm

        form = LibrarySettingsForm(request.POST, instance=settings)

        if form.is_valid():
            form.save()
            messages.success(request, "Library settings updated successfully!")
            return redirect("librarymanagement:manage_library_settings")
    else:
        from librarymanagement.forms import LibrarySettingsForm

        form = LibrarySettingsForm(instance=settings)

    return render(
        request,
        "librarymanagement/pages/library_settings.html",
        {"form": form, "settings": settings, "library": library},
    )


# Advanced Search Views
@login_required(login_url="/librarymanagement/login")
def advanced_search(request):
    """Advanced book search"""
    from librarymanagement.forms import AdvancedSearchForm

    form = AdvancedSearchForm(request.GET or None)
    books = []

    if form.is_valid():
        books = AdvancedSearchServices.search_books(
            query=form.cleaned_data.get("query"),
            category_ids=[c.id for c in form.cleaned_data.get("categories", [])],
            author_ids=[a.id for a in form.cleaned_data.get("authors", [])],
            publisher_id=(
                form.cleaned_data.get("publisher").id
                if form.cleaned_data.get("publisher")
                else None
            ),
            status=form.cleaned_data.get("status"),
            resource_type=form.cleaned_data.get("resource_type"),
            year_from=form.cleaned_data.get("year_from"),
            year_to=form.cleaned_data.get("year_to"),
            language=form.cleaned_data.get("language"),
        )

    return render(
        request,
        "librarymanagement/pages/advanced_search.html",
        {"form": form, "books": books},
    )


# User Profile Views
@login_required(login_url="/librarymanagement/login")
def user_borrowing_history(request):
    """View user's borrowing history"""
    transactions = UserProfileServices.get_borrowing_history(request.user)

    return render(
        request,
        "librarymanagement/pages/user_borrowing_history.html",
        {"transactions": transactions},
    )


@login_required(login_url="/librarymanagement/login")
def user_reservation_history(request):
    """View user's reservation history"""
    reservations = UserProfileServices.get_reservation_history(request.user)

    return render(
        request,
        "librarymanagement/pages/user_reservation_history.html",
        {"reservations": reservations},
    )


@login_required(login_url="/librarymanagement/login")
def export_user_data(request):
    """Export user's library data"""
    try:
        json_data = UserProfileServices.export_user_data(request.user)

        response = HttpResponse(json_data, content_type="application/json")
        response["Content-Disposition"] = (
            f'attachment; filename="user_data_{request.user.username}.json"'
        )

        return response
    except Exception as e:
        messages.error(request, f"Error exporting data: {str(e)}")
        return redirect("librarymanagement:user_settings")


# Notification Views
@login_required(login_url="/librarymanagement/login")
@require_POST
def mark_notification_read(request, notification_id):
    """Mark notification as read"""
    try:
        NotificationServices.mark_notification_read(notification_id)
        return JsonResponse({"success": True, "message": "Notification marked as read"})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required(login_url="/librarymanagement/login")
@require_POST
def delete_notification(request, notification_id):
    """Delete notification"""
    try:
        NotificationServices.delete_notification(notification_id)
        return JsonResponse({"success": True, "message": "Notification deleted"})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)


@login_required(login_url="/librarymanagement/login")
def user_notifications(request):
    """View user's notifications"""
    notifications = NotificationServices.get_user_notifications(request.user, limit=50)
    unread_count = NotificationServices.get_unread_count(request.user)

    return render(
        request,
        "librarymanagement/pages/user_notifications.html",
        {"notifications": notifications, "unread_count": unread_count},
    )
