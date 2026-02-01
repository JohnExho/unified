# Business logics

from librarymanagement.models import (
    Book,
    Author,
    Publisher,
    BorrowingTransaction,
    Reservation,
    Notification,
    Library,
    Category,
    TrendingBook,
    UserActivity,
)  # Import here to avoid circular imports
from django.db import transaction
from django.utils import timezone
from librarymanagement.utils import BookUtils
from datetime import timedelta, datetime
from decimal import Decimal
from django.db.models import Count, Q, Sum, Avg, F
from django.db.models.functions import TruncDate


class ReportServices:
    """Services for generating and managing library reports"""

    @staticmethod
    def generate_report(report_type, title, period_start, period_end, generated_by):
        """Generate a library report based on type and date range"""
        from librarymanagement.models import LibraryReport

        # Generate title if not provided
        if not title:
            report_names = dict(LibraryReport.REPORT_TYPES)
            title = f"{report_names.get(report_type, 'Report')} - {period_start.strftime('%B %Y')}"

        # Generate report data based on type
        data = {}
        summary = ""

        if report_type == "usage":
            data, summary = ReportServices._generate_usage_report(
                period_start, period_end
            )
        elif report_type == "circulation":
            data, summary = ReportServices._generate_circulation_report(
                period_start, period_end
            )
        elif report_type == "trending":
            data, summary = ReportServices._generate_trending_report(
                period_start, period_end
            )
        elif report_type == "user_behavior":
            data, summary = ReportServices._generate_user_behavior_report(
                period_start, period_end
            )
        elif report_type == "inventory":
            data, summary = ReportServices._generate_inventory_report(
                period_start, period_end
            )
        elif report_type == "acquisition":
            data, summary = ReportServices._generate_acquisition_report(
                period_start, period_end
            )

        # Create report record
        report = LibraryReport.objects.create(
            report_type=report_type,
            title=title,
            period_start=period_start,
            period_end=period_end,
            data=data,
            summary=summary,
            generated_by=generated_by,
        )

        return report

    @staticmethod
    def _generate_usage_report(period_start, period_end):
        """Generate usage statistics report"""
        borrows = BorrowingTransaction.objects.filter(
            borrowed_date__date__gte=period_start,
            borrowed_date__date__lte=period_end,
        )

        total_borrows = borrows.count()
        unique_users = borrows.values("user").distinct().count()
        unique_books = borrows.values("book").distinct().count()
        avg_duration = borrows.filter(return_date__isnull=False).aggregate(
            avg_days=Avg(F("return_date") - F("borrowed_date"))
        )["avg_days"]

        data = {
            "total_borrows": total_borrows,
            "unique_users": unique_users,
            "unique_books": unique_books,
            "avg_borrow_duration_days": str(avg_duration) if avg_duration else "N/A",
            "period": {"start": str(period_start), "end": str(period_end)},
        }

        summary = f"During this period, {total_borrows} books were borrowed by {unique_users} unique users, covering {unique_books} different titles."
        return data, summary

    @staticmethod
    def _generate_circulation_report(period_start, period_end):
        """Generate circulation metrics report"""
        transactions = BorrowingTransaction.objects.filter(
            borrowed_date__date__gte=period_start,
            borrowed_date__date__lte=period_end,
        )

        total_checkouts = transactions.count()
        total_returns = transactions.filter(status="returned").count()
        overdue = transactions.filter(status="overdue").count()
        active = transactions.filter(status="active").count()

        data = {
            "total_checkouts": total_checkouts,
            "total_returns": total_returns,
            "overdue_count": overdue,
            "active_loans": active,
            "return_rate": (
                round((total_returns / total_checkouts * 100), 2)
                if total_checkouts > 0
                else 0
            ),
        }

        summary = f"Circulation summary: {total_checkouts} checkouts, {total_returns} returns ({data['return_rate']}% return rate), {overdue} overdue, {active} active loans."
        return data, summary

    @staticmethod
    def _generate_trending_report(period_start, period_end):
        """Generate trending books analysis"""
        top_books = (
            BorrowingTransaction.objects.filter(
                borrowed_date__date__gte=period_start,
                borrowed_date__date__lte=period_end,
            )
            .values("book__title", "book__id")
            .annotate(borrow_count=Count("id"))
            .order_by("-borrow_count")[:10]
        )

        data = {
            "top_books": list(top_books),
            "total_trending": len(top_books),
        }

        summary = (
            f"Top {len(top_books)} most borrowed books identified during this period."
        )
        return data, summary

    @staticmethod
    def _generate_user_behavior_report(period_start, period_end):
        """Generate user behavior analysis"""
        activities = UserActivity.objects.filter(
            timestamp__date__gte=period_start,
            timestamp__date__lte=period_end,
        )

        activity_breakdown = (
            activities.values("activity_type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        total_activities = activities.count()
        unique_users = activities.values("user").distinct().count()

        data = {
            "total_activities": total_activities,
            "unique_users": unique_users,
            "activity_breakdown": list(activity_breakdown),
        }

        summary = f"{total_activities} activities recorded from {unique_users} users during this period."
        return data, summary

    @staticmethod
    def _generate_inventory_report(period_start, period_end):
        """Generate inventory status report"""
        total_books = Book.objects.count()
        available = Book.objects.filter(status="available").count()
        borrowed = Book.objects.filter(status="borrowed").count()
        reserved = Book.objects.filter(status="reserved").count()
        maintenance = Book.objects.filter(status="maintenance").count()

        data = {
            "total_books": total_books,
            "available": available,
            "borrowed": borrowed,
            "reserved": reserved,
            "maintenance": maintenance,
            "availability_rate": (
                round((available / total_books * 100), 2) if total_books > 0 else 0
            ),
        }

        summary = f"Total collection: {total_books} books. Available: {available} ({data['availability_rate']}%), Borrowed: {borrowed}, Reserved: {reserved}, Maintenance: {maintenance}."
        return data, summary

    @staticmethod
    def _generate_acquisition_report(period_start, period_end):
        """Generate acquisition recommendations"""
        # Analyze most requested but unavailable books
        reservations = Reservation.objects.filter(
            reservation_date__date__gte=period_start,
            reservation_date__date__lte=period_end,
        )

        high_demand_books = (
            reservations.values("book__title", "book__id")
            .annotate(reservation_count=Count("id"))
            .order_by("-reservation_count")[:10]
        )

        data = {
            "high_demand_books": list(high_demand_books),
            "recommendations": "Consider acquiring more copies of high-demand titles",
        }

        summary = f"Identified {len(high_demand_books)} high-demand titles that may benefit from additional copies."
        return data, summary

    @staticmethod
    def get_report_statistics():
        """Get statistics about generated reports"""
        from librarymanagement.models import LibraryReport

        total_reports = LibraryReport.objects.count()
        report_type_counts = LibraryReport.objects.values("report_type").annotate(
            count=Count("id")
        )

        last_generated = {}
        for report_type, _ in LibraryReport.REPORT_TYPES:
            last_report = LibraryReport.objects.filter(report_type=report_type).first()
            if last_report:
                days_ago = (
                    timezone.now().date() - last_report.generated_at.date()
                ).days
                if days_ago == 0:
                    last_generated[report_type] = "today"
                elif days_ago == 1:
                    last_generated[report_type] = "yesterday"
                elif days_ago < 7:
                    last_generated[report_type] = f"{days_ago} days ago"
                elif days_ago < 30:
                    weeks = days_ago // 7
                    last_generated[report_type] = (
                        f"{weeks} week{'s' if weeks > 1 else ''} ago"
                    )
                else:
                    months = days_ago // 30
                    last_generated[report_type] = (
                        f"{months} month{'s' if months > 1 else ''} ago"
                    )
            else:
                last_generated[report_type] = "never"

        return {
            "total_reports": total_reports,
            "report_type_counts": {
                item["report_type"]: item["count"] for item in report_type_counts
            },
            "last_generated": last_generated,
        }


class DashboardServices:
    """Services for dashboard data aggregation and analytics"""

    @staticmethod
    def get_overview_stats():
        """Get main dashboard overview statistics"""
        total_books = Book.objects.count()
        available_books = Book.objects.filter(status="available").count()
        borrowed_books = BorrowingTransaction.objects.filter(
            status__in=["active", "overdue"]
        ).count()
        overdue_books = BorrowingTransaction.objects.filter(status="overdue").count()

        # Calculate percentage changes (mock for now, can be enhanced)
        return {
            "total_books": total_books,
            "available_books": available_books,
            "borrowed_books": borrowed_books,
            "overdue_books": overdue_books,
        }

    @staticmethod
    def get_recent_transactions(limit=5):
        """Get recent borrowing transactions"""
        return (
            BorrowingTransaction.objects.select_related("user", "book")
            .prefetch_related("book__authors")
            .order_by("-borrowed_date")[:limit]
        )

    @staticmethod
    def get_popular_books(limit=5):
        """Get most borrowed/popular books"""
        # Get books with most borrows
        popular = (
            TrendingBook.objects.select_related("book")
            .prefetch_related("book__authors")
            .order_by("-borrow_count")[:limit]
        )

        return popular

    @staticmethod
    def get_activity_summary(days=7):
        """Get activity summary for the specified number of days"""
        from_date = timezone.now() - timedelta(days=days)

        # Books borrowed in period
        borrowed_count = BorrowingTransaction.objects.filter(
            borrowed_date__gte=from_date
        ).count()

        # Books returned in period
        returned_count = BorrowingTransaction.objects.filter(
            return_date__gte=from_date, status="returned"
        ).count()

        # New reservations in period
        reservations_count = Reservation.objects.filter(
            reservation_date__gte=from_date
        ).count()

        # Calculate percentages (relative to total possible)
        total_books = Book.objects.count()
        borrowed_percentage = (
            int((borrowed_count / total_books * 100)) if total_books > 0 else 0
        )
        returned_percentage = (
            int((returned_count / borrowed_count * 100)) if borrowed_count > 0 else 0
        )

        return {
            "borrowed_count": borrowed_count,
            "borrowed_percentage": min(borrowed_percentage, 100),
            "returned_count": returned_count,
            "returned_percentage": min(returned_percentage, 100),
            "reservations_count": reservations_count,
            "reservations_percentage": min(
                int(reservations_count / 10), 100
            ),  # Relative scale
            "days": days,
        }

    @staticmethod
    def get_pending_reservations(limit=10):
        """Get pending reservations"""
        return (
            Reservation.objects.filter(status="pending")
            .select_related("user", "book")
            .order_by("-reservation_date")[:limit]
        )

    @staticmethod
    def get_overdue_transactions(limit=10):
        """Get overdue transactions"""
        return (
            BorrowingTransaction.objects.filter(status="overdue")
            .select_related("user", "book")
            .order_by("due_date")[:limit]
        )


class BookServices:

    @staticmethod
    def process_tagify_data(raw_data):
        """
        Parse Tagify JSON data and extract values.
        Returns a list of strings extracted from [{"value":"name"}] format.
        Falls back to comma-separated parsing if JSON decode fails.
        """
        import json

        if not raw_data:
            return []

        try:
            data = json.loads(raw_data)
            if isinstance(data, list):
                # Extract 'value' from Tagify JSON objects
                return [
                    tag.get("value", "").strip()
                    for tag in data
                    if isinstance(tag, dict) and tag.get("value", "").strip()
                ]
        except (json.JSONDecodeError, Exception):
            # Fallback: treat as comma-separated string
            return [name.strip() for name in raw_data.split(",") if name.strip()]

        return []

    @staticmethod
    def create_book_from_request(post_data, user):
        """
        Create a Book from raw POST data.
        Handles Tagify JSON parsing for categories and authors,
        auto-creates related objects, and validates the form.
        Returns (book, error_messages) tuple.
        """
        from librarymanagement.forms import BookForm

        # Create mutable copy
        data = post_data.copy()

        # Extract category and author names from Tagify JSON
        category_names = BookServices.process_tagify_data(data.get("categories", ""))
        author_names = BookServices.process_tagify_data(data.get("authors", ""))

        # Remove categories and authors from validation (we'll add them after)
        data.pop("categories", None)
        data.pop("authors", None)

        # Auto-set available_copies to total_copies for new books
        if not data.get("available_copies") and data.get("total_copies"):
            data["available_copies"] = data["total_copies"]

        # Auto-set status to available for new books
        if not data.get("status"):
            data["status"] = "available"

        # Validate form
        form = BookForm(data)

        # Make categories and authors optional for validation
        form.fields["categories"].required = False
        form.fields["authors"].required = False

        if not form.is_valid():
            # Collect error messages
            error_messages = []
            for field, errors in form.errors.items():
                for error in errors:
                    if field == "__all__":
                        error_messages.append(str(error))
                    else:
                        field_name = (
                            form.fields.get(field).label
                            if field in form.fields
                            else field
                        )
                        error_messages.append(f"{field_name}: {error}")
            return None, error_messages

        # Get or create categories and authors
        if category_names:
            categories = CategoryServices.get_or_create_categories_from_strings(
                category_names
            )
            form.cleaned_data["categories"] = categories
        else:
            form.cleaned_data["categories"] = []

        if author_names:
            authors = AuthorServices.get_or_create_authors_from_strings(author_names)
            form.cleaned_data["authors"] = authors
        else:
            form.cleaned_data["authors"] = []

        # Create the book
        book = BookServices.create_book(form, user)

        return book, None

    @staticmethod
    def create_book(form, user):
        """
        Create a Book instance from a BookForm.
        Handles M2M relations, metadata, and saves in a transaction.
        Automatically creates authors if they do not exist.
        """
        book_data = form.cleaned_data

        with transaction.atomic():
            # Ensure authors exist or create them with basic information
            author_objects = AuthorServices.get_or_create_authors_from_strings(
                book_data.get("authors", [])
            )

            # Create the book
            book = Book.objects.create(
                library=book_data["library"],
                title=book_data["title"],
                isbn=book_data["isbn"],
                publication_year=book_data.get("publication_year"),
                edition=book_data.get("edition"),
                language=book_data.get("language", "English"),
                pages=book_data.get("pages"),
                resource_type=book_data.get("resource_type", "physical"),
                total_copies=book_data.get("total_copies", 1),
                available_copies=book_data.get("total_copies", 1),
                description=book_data.get("description", ""),
                shelf_location=book_data.get("shelf_location", ""),
                accession_number=book_data.get("accession_number")
                or BookUtils.generate_accession_number(),
                created_by=user if user.is_authenticated else None,
            )

            book.categories.set(book_data.get("categories", []))
            book.authors.set(author_objects)

            if book_data.get("publisher"):
                book.publisher = book_data["publisher"]
                book.save()

        return book


class LibraryServices:

    @staticmethod
    def create_library(form, user=None):
        """
        Create a Library instance from a LibraryForm.
        """
        library_data = form.cleaned_data

        with transaction.atomic():
            library = Library.objects.create(
                name=library_data["name"],
                description=library_data.get("description", ""),
                location=library_data.get("location", ""),
                contact_email=library_data.get("contact_email", ""),
                contact_phone=library_data.get("contact_phone", ""),
            )

        return library

    @staticmethod
    def update_library(library, form):
        """
        Update an existing Library instance from a LibraryForm.
        """
        library_data = form.cleaned_data

        with transaction.atomic():
            library.name = library_data["name"]
            library.description = library_data.get("description", "")
            library.location = library_data.get("location", "")
            library.contact_email = library_data.get("contact_email", "")
            library.contact_phone = library_data.get("contact_phone", "")
            library.save()

        return library


class TransactionServices:

    @staticmethod
    def create_transaction(form, user, issued_by=None):
        """
        Create a new borrowing transaction.
        Decrements available copies and creates the transaction record.
        """
        transaction_data = form.cleaned_data
        book = transaction_data["book"]

        with transaction.atomic():
            # Check if book is available
            if not book.is_available:
                raise ValueError(f"Book '{book.title}' is not available for borrowing.")

            # Create transaction
            borrowing_transaction = BorrowingTransaction.objects.create(
                user=transaction_data["user"],
                book=book,
                due_date=transaction_data["due_date"],
                status="active",
                notes=transaction_data.get("notes", ""),
                issued_by=issued_by,
            )

            # Decrement available copies
            book.available_copies -= 1
            if book.available_copies == 0:
                book.status = "borrowed"
            book.save()

        return borrowing_transaction

    @staticmethod
    def return_book(
        transaction_id, return_date=None, condition_notes="", apply_fine=False
    ):
        """
        Mark a book as returned and update book availability.
        Optionally calculate and apply fines for overdue returns.
        """
        with transaction.atomic():
            borrowing_transaction = (
                BorrowingTransaction.objects.select_for_update().get(id=transaction_id)
            )

            if borrowing_transaction.status == "returned":
                raise ValueError("This book has already been returned.")

            # Set return date
            if return_date is None:
                return_date = timezone.now()

            borrowing_transaction.return_date = return_date
            borrowing_transaction.status = "returned"

            # Calculate fine if overdue and apply_fine is True
            if apply_fine and return_date > borrowing_transaction.due_date:
                days_overdue = (return_date - borrowing_transaction.due_date).days
                fine_per_day = Decimal("10.00")  # ₱10 per day
                borrowing_transaction.fine_amount = days_overdue * fine_per_day
                borrowing_transaction.days_overdue = days_overdue

            # Add condition notes if provided
            if condition_notes:
                borrowing_transaction.notes += f"\n[Return Condition] {condition_notes}"

            borrowing_transaction.save()

            # Increment available copies
            book = borrowing_transaction.book
            book.available_copies += 1
            if book.status == "borrowed" and book.available_copies > 0:
                book.status = "available"
            book.save()

        return borrowing_transaction

    @staticmethod
    def renew_transaction(transaction_id, extend_days=14):
        """
        Renew a borrowing transaction by extending the due date.
        """
        with transaction.atomic():
            borrowing_transaction = (
                BorrowingTransaction.objects.select_for_update().get(id=transaction_id)
            )

            if borrowing_transaction.status not in ["active", "overdue"]:
                raise ValueError("Only active or overdue transactions can be renewed.")

            # Check renewal limit (e.g., max 3 renewals)
            if borrowing_transaction.renewal_count >= 3:
                raise ValueError("Maximum renewal limit reached.")

            # Extend due date
            borrowing_transaction.due_date += timedelta(days=extend_days)
            borrowing_transaction.renewal_count += 1

            # Reset status if it was overdue
            if borrowing_transaction.status == "overdue":
                borrowing_transaction.status = "active"
                borrowing_transaction.days_overdue = 0

            borrowing_transaction.save()

        return borrowing_transaction

    @staticmethod
    def check_and_update_overdue_transactions():
        """
        Check all active transactions and mark overdue ones.
        Calculate fines for overdue transactions.
        """
        now = timezone.now()
        active_transactions = BorrowingTransaction.objects.filter(
            status="active", due_date__lt=now
        )

        updated_count = 0
        with transaction.atomic():
            for trans in active_transactions:
                days_overdue = (now - trans.due_date).days
                fine_per_day = Decimal("10.00")

                trans.status = "overdue"
                trans.days_overdue = days_overdue
                trans.fine_amount = days_overdue * fine_per_day
                trans.save()

                # Create notification
                NotificationServices.create_overdue_notification(trans)

                updated_count += 1

        return updated_count


class ReservationServices:

    @staticmethod
    def create_reservation(form, user):
        """
        Create a new book reservation.
        """
        reservation_data = form.cleaned_data
        book = reservation_data["book"]

        with transaction.atomic():
            # Check if user already has active reservation for this book
            existing = Reservation.objects.filter(
                user=user, book=book, status__in=["pending", "ready"]
            ).exists()

            if existing:
                raise ValueError(
                    "You already have an active reservation for this book."
                )

            # Create reservation
            reservation = Reservation.objects.create(
                user=reservation_data["user"],
                book=book,
                expiry_date=reservation_data["expiry_date"],
                status="pending",
                notes=reservation_data.get("notes", ""),
            )

            # Update book status if all copies are borrowed
            if book.available_copies == 0 and book.status != "reserved":
                book.status = "reserved"
                book.save()

        return reservation

    @staticmethod
    def mark_reservation_ready(reservation_id, notify=True):
        """
        Mark a reservation as ready for pickup.
        Optionally send notification to user.
        """
        with transaction.atomic():
            reservation = Reservation.objects.select_for_update().get(id=reservation_id)

            if reservation.status != "pending":
                raise ValueError("Only pending reservations can be marked as ready.")

            reservation.status = "ready"
            reservation.save()

            # Create notification
            if notify:
                NotificationServices.create_reservation_ready_notification(reservation)
                reservation.notified = True
                reservation.notified_at = timezone.now()
                reservation.save()

        return reservation

    @staticmethod
    def fulfill_reservation(reservation_id, issued_by=None):
        """
        Fulfill a reservation by creating a borrowing transaction.
        """
        with transaction.atomic():
            reservation = Reservation.objects.select_for_update().get(id=reservation_id)

            if reservation.status != "ready":
                raise ValueError("Only ready reservations can be fulfilled.")

            # Create borrowing transaction
            due_date = timezone.now() + timedelta(days=14)  # 14 days loan period

            borrowing_transaction = BorrowingTransaction.objects.create(
                user=reservation.user,
                book=reservation.book,
                due_date=due_date,
                status="active",
                notes=f"Fulfilled from reservation {reservation.id}",
                issued_by=issued_by,
            )

            # Update reservation
            reservation.status = "fulfilled"
            reservation.fulfilled_date = timezone.now()
            reservation.save()

            # Decrement available copies
            book = reservation.book
            book.available_copies -= 1
            if book.available_copies == 0:
                book.status = "borrowed"
            book.save()

        return borrowing_transaction, reservation

    @staticmethod
    def cancel_reservation(reservation_id, reason=""):
        """
        Cancel a reservation.
        """
        with transaction.atomic():
            reservation = Reservation.objects.select_for_update().get(id=reservation_id)

            if reservation.status in ["fulfilled", "cancelled"]:
                raise ValueError(
                    "Cannot cancel a fulfilled or already cancelled reservation."
                )

            reservation.status = "cancelled"
            if reason:
                reservation.notes += f"\n[Cancellation Reason] {reason}"
            reservation.save()

            # Update book status if needed
            book = reservation.book
            if book.status == "reserved":
                # Check if there are other active reservations
                has_other_reservations = (
                    Reservation.objects.filter(
                        book=book, status__in=["pending", "ready"]
                    )
                    .exclude(id=reservation_id)
                    .exists()
                )

                if not has_other_reservations and book.available_copies > 0:
                    book.status = "available"
                    book.save()

        return reservation

    @staticmethod
    def check_and_expire_reservations():
        """
        Check all ready reservations and mark expired ones.
        """
        now = timezone.now()
        ready_reservations = Reservation.objects.filter(
            status="ready", expiry_date__lt=now
        )

        expired_count = 0
        with transaction.atomic():
            for reservation in ready_reservations:
                reservation.status = "expired"
                reservation.save()
                expired_count += 1

        return expired_count


class NotificationServices:

    @staticmethod
    def create_overdue_notification(borrowing_transaction):
        """
        Create an overdue notification for a transaction.
        """
        notification = Notification.objects.create(
            user=borrowing_transaction.user,
            notification_type="overdue",
            title="Book Overdue",
            message=f"Your borrowed book '{borrowing_transaction.book.title}' is {borrowing_transaction.days_overdue} day(s) overdue. Please return it as soon as possible.",
            related_transaction=borrowing_transaction,
        )
        return notification

    @staticmethod
    def create_due_soon_notification(borrowing_transaction):
        """
        Create a due soon notification for a transaction.
        """
        notification = Notification.objects.create(
            user=borrowing_transaction.user,
            notification_type="due_soon",
            title="Book Due Soon",
            message=f"Your borrowed book '{borrowing_transaction.book.title}' is due on {borrowing_transaction.due_date.strftime('%B %d, %Y')}.",
            related_transaction=borrowing_transaction,
        )
        return notification

    @staticmethod
    def create_reservation_ready_notification(reservation):
        """
        Create a reservation ready notification.
        """
        notification = Notification.objects.create(
            user=reservation.user,
            notification_type="reservation_ready",
            title="Book Ready for Pickup",
            message=f"Your reserved book '{reservation.book.title}' is now ready for pickup. Please collect it before {reservation.expiry_date.strftime('%B %d, %Y')}.",
            related_reservation=reservation,
        )
        return notification

    @staticmethod
    def create_reservation_expiring_notification(reservation):
        """
        Create a reservation expiring notification.
        """
        notification = Notification.objects.create(
            user=reservation.user,
            notification_type="reservation_expiring",
            title="Reservation Expiring Soon",
            message=f"Your reservation for '{reservation.book.title}' will expire on {reservation.expiry_date.strftime('%B %d, %Y')}. Please collect it soon.",
            related_reservation=reservation,
        )
        return notification


class AuthorServices:

    @staticmethod
    def create_author(form, user=None):
        """
        Create an Author instance from an AuthorForm.
        Handles all author fields and metadata.
        """
        author_data = form.cleaned_data

        with transaction.atomic():
            author = Author.objects.create(
                first_name=author_data["first_name"],
                last_name=author_data["last_name"],
                middle_name=author_data.get("middle_name", ""),
                bio=author_data.get("bio", ""),
                birth_date=author_data.get("birth_date"),
                nationality=author_data.get("nationality", ""),
            )

        return author

    @staticmethod
    def update_author(author, form):
        """
        Update an existing Author instance from an AuthorForm.
        """
        author_data = form.cleaned_data

        with transaction.atomic():
            author.first_name = author_data["first_name"]
            author.last_name = author_data["last_name"]
            author.middle_name = author_data.get("middle_name", "")
            author.bio = author_data.get("bio", "")
            author.birth_date = author_data.get("birth_date")
            author.nationality = author_data.get("nationality", "")
            author.save()

        return author

    @staticmethod
    def get_or_create_authors_from_strings(author_names):
        """
        Accepts a list of author name strings (e.g., ["John Doe", "Jane Smith"]).
        Parses each name, creates author if doesn't exist, and returns Author instances.
        Name format: "FirstName LastName" or "FirstName MiddleName LastName"
        """
        from librarymanagement.models import Author

        authors = []
        for full_name in author_names:
            # Skip if already an Author object (defensive check)
            if isinstance(full_name, Author):
                authors.append(full_name)
                continue

            # Convert to string and strip whitespace
            full_name = str(full_name).strip()
            if not full_name:
                continue

            # Split name into parts
            name_parts = full_name.split()

            if len(name_parts) == 1:
                # Single name - use as last name
                first_name = ""
                last_name = name_parts[0]
                middle_name = ""
            elif len(name_parts) == 2:
                # First and last name
                first_name = name_parts[0]
                last_name = name_parts[1]
                middle_name = ""
            else:
                # First, middle, and last name
                first_name = name_parts[0]
                middle_name = " ".join(name_parts[1:-1])
                last_name = name_parts[-1]

            # Get or create author
            author, _ = Author.objects.get_or_create(
                first_name=first_name,
                last_name=last_name,
                defaults={"middle_name": middle_name},
            )
            authors.append(author)

        return authors


class CategoryServices:
    @staticmethod
    def get_or_create_category(name):
        """Get or create a category by name"""
        category, _ = Category.objects.get_or_create(name=name)
        return category

    @staticmethod
    def get_or_create_categories_from_strings(category_names):
        """
        Accepts a list of category name strings (e.g., ["Fiction", "Science"]).
        Ensures each category exists and returns a list of Category instances.
        """
        categories = []
        for name in category_names:
            category, _ = Category.objects.get_or_create(name=name.strip())
            categories.append(category)
        return categories


class PublisherServices:

    @staticmethod
    def create_publisher(form, user=None):
        """
        Create a Publisher instance from a PublisherForm.
        Handles all publisher fields and metadata.
        """
        publisher_data = form.cleaned_data

        with transaction.atomic():
            publisher = Publisher.objects.create(
                name=publisher_data["name"],
                address=publisher_data.get("address", ""),
                website=publisher_data.get("website", ""),
                email=publisher_data.get("email", ""),
            )

        return publisher

    @staticmethod
    def update_publisher(publisher, form):
        """
        Update an existing Publisher instance from a PublisherForm.
        """
        publisher_data = form.cleaned_data

        with transaction.atomic():
            publisher.name = publisher_data["name"]
            publisher.address = publisher_data.get("address", "")
            publisher.website = publisher_data.get("website", "")
            publisher.email = publisher_data.get("email", "")
            publisher.save()

        return publisher

    @staticmethod
    def get_or_create_publisher(name):
        """Get or create a publisher by name"""
        publisher, created = Publisher.objects.get_or_create(
            name=name,
            defaults={
                "address": "",
                "website": "",
                "email": "",
            },
        )
        return publisher
