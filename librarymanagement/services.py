# Business logics

from librarymanagement.models import (
    Book,
    Author,
    Publisher,
    BorrowingTransaction,
    Reservation,
    Reservation,
    Notification,
    Library,
    Category,
    TrendingBook,
    UserActivity,
    BookRecommendation,
)  # Import here to avoid circular imports
from django.db import transaction
from django.utils import timezone
from librarymanagement.utils import BookUtils
from datetime import timedelta
from decimal import Decimal
from django.db.models import Count, Avg, F


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
    def export_report(report, export_format="csv"):
        """Export report data to the requested format."""
        import csv
        import io
        import json
        import html

        export_format = (export_format or "csv").lower()
        if export_format not in {"csv", "html", "xls"}:
            raise ValueError("Unsupported export format.")

        metadata = {
            "title": report.title,
            "report_type": report.report_type,
            "period_start": report.period_start,
            "period_end": report.period_end,
            "generated_at": report.generated_at,
            "generated_by": (
                report.generated_by.username if report.generated_by else "System"
            ),
        }

        def normalize_value(value):
            if isinstance(value, (dict, list)):
                return json.dumps(value, default=str)
            return str(value)

        report_data = report.data or {}

        if export_format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["field", "value"])
            for key, value in metadata.items():
                writer.writerow([key, normalize_value(value)])
            writer.writerow([])
            writer.writerow(["data_key", "data_value"])
            for key, value in report_data.items():
                writer.writerow([key, normalize_value(value)])

            filename = f"report_{report.id}.csv"
            return output.getvalue(), "text/csv", filename

        def render_rows(source):
            return "".join(
                f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(normalize_value(value))}</td></tr>"
                for key, value in source.items()
            )

        html_content = (
            "<html><head><meta charset='utf-8'></head><body>"
            "<h1>Library Report</h1>"
            "<h2>Metadata</h2>"
            "<table border='1'>"
            f"{render_rows(metadata)}"
            "</table>"
            "<h2>Data</h2>"
            "<table border='1'>"
            f"{render_rows(report_data)}"
            "</table>"
            "</body></html>"
        )

        if export_format == "html":
            filename = f"report_{report.id}.html"
            return html_content, "text/html", filename

        filename = f"report_{report.id}.xls"
        return html_content, "application/vnd.ms-excel", filename

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
                        field_obj = form.fields.get(field)
                        field_name = (
                            field_obj.label
                            if field_obj and hasattr(field_obj, "label")
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


    @staticmethod
    def update_book(book_id, data, files=None):
        """Update existing book"""
        book = Book.objects.get(id=book_id)

        # Update basic fields
        for field in [
            "title",
            "subtitle",
            "isbn",
            "publication_year",
            "edition",
            "language",
            "pages",
            "resource_type",
            "total_copies",
            "available_copies",
            "description",
            "shelf_location",
            "accession_number",
            "subject",
        ]:
            if field in data:
                setattr(book, field, data[field])

        # Update publisher
        if "publisher" in data and data["publisher"]:
            book.publisher_id = data["publisher"]

        # Handle file uploads
        if files:
            if "cover_image" in files:
                book.cover_image = files["cover_image"]
            if "digital_file" in files:
                book.digital_file = files["digital_file"]

        book.save()

        # Update M2M relations
        if "categories" in data:
            category_names = BookServices.process_tagify_data(data.get("categories", ""))
            if category_names:
                categories = CategoryServices.get_or_create_categories_from_strings(
                    category_names
                )
                book.categories.set(categories)

        if "authors" in data:
            author_names = BookServices.process_tagify_data(data.get("authors", ""))
            if author_names:
                authors = AuthorServices.get_or_create_authors_from_strings(author_names)
                book.authors.set(authors)

        return book

    @staticmethod
    def delete_book(book_id):
        """Delete a book"""
        book = Book.objects.get(id=book_id)
        # Check if book has active transactions
        active_transactions = BorrowingTransaction.objects.filter(
            book=book, status__in=["active", "overdue"]
        ).exists()

        if active_transactions:
            raise ValueError("Cannot delete book with active borrowing transactions")

        book.delete()
        return True

    @staticmethod
    def toggle_book_status(book_id, new_status):
        """Toggle book status"""
        book = Book.objects.get(id=book_id)
        book.status = new_status
        book.save()
        return book

    @staticmethod
    def upload_cover_image(book_id, image_file):
        """Upload book cover image"""
        book = Book.objects.get(id=book_id)
        book.cover_image = image_file
        book.save()
        return book

    @staticmethod
    def upload_digital_file(book_id, digital_file):
        """Upload digital book file"""
        book = Book.objects.get(id=book_id)
        book.digital_file = digital_file
        book.save()
        return book

    @staticmethod
    def bulk_import_books(file_path, library, user):
        """Import books from CSV file"""
        import csv

        books_created = []
        errors = []

        try:
            with open(file_path, "r", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)

                for row in reader:
                    try:
                        # Create book
                        book = Book.objects.create(
                            library=library,
                            title=row.get("title", ""),
                            isbn=row.get("isbn", ""),
                            publication_year=(
                                int(row.get("publication_year"))
                                if row.get("publication_year")
                                else None
                            ),
                            edition=row.get("edition", ""),
                            language=row.get("language", "English"),
                            pages=(
                                int(row.get("pages")) if row.get("pages") else None
                            ),
                            resource_type=row.get("resource_type", "physical"),
                            total_copies=(
                                int(row.get("total_copies", 1))
                                if row.get("total_copies")
                                else 1
                            ),
                            available_copies=(
                                int(row.get("available_copies", 1))
                                if row.get("available_copies")
                                else 1
                            ),
                            description=row.get("description", ""),
                            shelf_location=row.get("shelf_location", ""),
                            accession_number=row.get("accession_number")
                            or BookUtils.generate_accession_number(),
                            created_by=user,
                        )

                        # Handle authors
                        if row.get("authors"):
                            author_names = [
                                name.strip() for name in row["authors"].split(";")
                            ]
                            authors = (
                                AuthorServices.get_or_create_authors_from_strings(
                                    author_names
                                )
                            )
                            book.authors.set(authors)

                        # Handle categories
                        if row.get("categories"):
                            category_names = [
                                name.strip() for name in row["categories"].split(";")
                            ]
                            categories = (
                                CategoryServices.get_or_create_categories_from_strings(
                                    category_names
                                )
                            )
                            book.categories.set(categories)

                        books_created.append(book)

                    except Exception as e:
                        errors.append(f"Row error: {str(e)}")

        except Exception as e:
            errors.append(f"File error: {str(e)}")

        return books_created, errors

    @staticmethod
    def export_books(library_id=None, export_format="csv"):
        """Export books to the requested format"""
        import csv
        import io
        import html

        export_format = (export_format or "csv").lower()
        if export_format not in {"csv", "html", "xls"}:
            raise ValueError("Unsupported export format.")

        books = Book.objects.all()
        if library_id:
            books = books.filter(library_id=library_id)

        headers = [
            "accession_number",
            "title",
            "isbn",
            "authors",
            "publisher",
            "publication_year",
            "categories",
            "language",
            "pages",
            "resource_type",
            "status",
            "total_copies",
            "available_copies",
            "shelf_location",
        ]

        rows = []
        for book in books.select_related("publisher").prefetch_related(
            "authors", "categories"
        ):
            rows.append(
                [
                    book.accession_number or "",
                    book.title,
                    book.isbn or "",
                    "; ".join([str(author) for author in book.authors.all()]),
                    str(book.publisher) if book.publisher else "",
                    book.publication_year or "",
                    "; ".join([cat.name for cat in book.categories.all()]),
                    book.language,
                    book.pages or "",
                    book.resource_type,
                    book.status,
                    book.total_copies,
                    book.available_copies,
                    book.shelf_location or "",
                ]
            )

        if export_format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(headers)
            writer.writerows(rows)
            return output.getvalue(), "text/csv", "books_export.csv"

        header_html = "".join(f"<th>{html.escape(header)}</th>" for header in headers)
        body_rows = "".join(
            "<tr>"
            + "".join(f"<td>{html.escape(str(value))}</td>" for value in row)
            + "</tr>"
            for row in rows
        )
        html_content = (
            "<html><head><meta charset='utf-8'></head><body>"
            "<table border='1'>"
            f"<thead><tr>{header_html}</tr></thead>"
            f"<tbody>{body_rows}</tbody>"
            "</table>"
            "</body></html>"
        )

        if export_format == "html":
            return html_content, "text/html", "books_export.html"

        return html_content, "application/vnd.ms-excel", "books_export.xls"



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

    @staticmethod
    def update_transaction(transaction_id, **kwargs):
        """Update transaction details"""
        trans = BorrowingTransaction.objects.get(id=transaction_id)

        for key, value in kwargs.items():
            if hasattr(trans, key):
                setattr(trans, key, value)

        trans.save()
        return trans

    @staticmethod
    def mark_book_lost(transaction_id, notes=""):
        """Mark a transaction/book as lost"""
        with transaction.atomic():
            trans = BorrowingTransaction.objects.select_for_update().get(
                id=transaction_id
            )

            trans.status = "lost"
            if notes:
                trans.notes += f"\n[Lost] {notes}"
            trans.save()

            # Update book status
            book = trans.book
            book.status = "lost"
            book.total_copies -= 1
            if book.available_copies > 0:
                book.available_copies -= 1
            book.save()

        return trans

    @staticmethod
    def waive_fine(transaction_id, waive_amount=None, reason=""):
        """Waive or reduce fine amount"""
        trans = BorrowingTransaction.objects.get(id=transaction_id)

        if waive_amount is None:
            # Waive entire fine
            trans.fine_amount = Decimal("0.00")
        else:
            # Reduce fine by specified amount
            trans.fine_amount = max(
                Decimal("0.00"), trans.fine_amount - Decimal(str(waive_amount))
            )

        if reason:
            trans.notes += f"\n[Fine Waived] {reason}"

        trans.save()
        return trans

    @staticmethod
    def pay_fine(transaction_id, amount_paid, payment_method="cash"):
        """Record fine payment"""
        trans = BorrowingTransaction.objects.get(id=transaction_id)

        # Deduct payment from fine
        trans.fine_amount = max(Decimal("0.00"), trans.fine_amount - Decimal(str(amount_paid)))

        trans.notes += f"\n[Payment] {payment_method}: ₱{amount_paid}"
        trans.save()

        return trans

    @staticmethod
    def extend_due_date(transaction_id, additional_days):
        """Manually extend due date"""
        trans = BorrowingTransaction.objects.get(id=transaction_id)

        trans.due_date = trans.due_date + timedelta(days=additional_days)

        # Reset overdue status if applicable
        if trans.status == "overdue" and trans.due_date > timezone.now():
            trans.status = "active"
            trans.days_overdue = 0

        trans.notes += f"\n[Due Date Extended] +{additional_days} days"
        trans.save()

        return trans

    @staticmethod
    def bulk_return_books(transaction_ids, return_date=None):
        """Return multiple books at once"""
        results = {"success": [], "errors": []}

        for trans_id in transaction_ids:
            try:
                trans = TransactionServices.return_book(
                    trans_id, return_date=return_date
                )
                results["success"].append(trans)
            except Exception as e:
                results["errors"].append({"transaction_id": trans_id, "error": str(e)})

        return results


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

    @staticmethod
    def update_reservation(reservation_id, **kwargs):
        """Update reservation details"""
        reservation = Reservation.objects.get(id=reservation_id)

        for key, value in kwargs.items():
            if hasattr(reservation, key):
                setattr(reservation, key, value)

        reservation.save()
        return reservation

    @staticmethod
    def extend_reservation_expiry(reservation_id, additional_days):
        """Extend reservation pickup deadline"""
        reservation = Reservation.objects.get(id=reservation_id)

        if reservation.status != "ready":
            raise ValueError("Only ready reservations can be extended")

        reservation.expiry_date = reservation.expiry_date + timedelta(
            days=additional_days
        )
        reservation.notes += f"\n[Expiry Extended] +{additional_days} days"
        reservation.save()

        return reservation


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

    @staticmethod
    def send_due_soon_notifications():
        """Scheduled task to send due soon notifications"""
        from datetime import timedelta

        # Get transactions due in 3 days
        target_date = timezone.now() + timedelta(days=3)
        transactions = BorrowingTransaction.objects.filter(
            status="active",
            due_date__date=target_date.date(),
        )

        count = 0
        for trans in transactions:
            # Check if notification already exists
            existing = Notification.objects.filter(
                user=trans.user,
                notification_type="due_soon",
                related_transaction=trans,
            ).exists()

            if not existing:
                NotificationServices.create_due_soon_notification(trans)
                count += 1

        return count

    @staticmethod
    def send_overdue_notifications():
        """Scheduled task to send overdue notifications"""
        transactions = BorrowingTransaction.objects.filter(status="overdue")

        count = 0
        for trans in transactions:
            # Send notification only if not sent today
            today = timezone.now().date()
            existing_today = Notification.objects.filter(
                user=trans.user,
                notification_type="overdue",
                related_transaction=trans,
                created_at__date=today,
            ).exists()

            if not existing_today:
                NotificationServices.create_overdue_notification(trans)
                count += 1

        return count

    @staticmethod
    def send_reservation_expiring_notifications():
        """Scheduled task to send reservation expiring notifications"""
        from datetime import timedelta

        # Get reservations expiring in 1 day
        target_date = timezone.now() + timedelta(days=1)
        reservations = Reservation.objects.filter(
            status="ready", expiry_date__date=target_date.date()
        )

        count = 0
        for reservation in reservations:
            # Check if notification already exists
            existing = Notification.objects.filter(
                user=reservation.user,
                notification_type="reservation_expiring",
                related_reservation=reservation,
            ).exists()

            if not existing:
                NotificationServices.create_reservation_expiring_notification(
                    reservation
                )
                count += 1

        return count

    @staticmethod
    def mark_notification_read(notification_id):
        """Mark notification as read"""
        notification = Notification.objects.get(id=notification_id)
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        return notification

    @staticmethod
    def delete_notification(notification_id):
        """Delete a notification"""
        notification = Notification.objects.get(id=notification_id)
        notification.delete()
        return True

    @staticmethod
    def get_unread_count(user):
        """Get count of unread notifications for user"""
        return Notification.objects.filter(user=user, is_read=False).count()

    @staticmethod
    def get_user_notifications(user, unread_only=False, limit=None):
        """Get user notifications"""
        notifications = Notification.objects.filter(user=user)

        if unread_only:
            notifications = notifications.filter(is_read=False)

        notifications = notifications.order_by("-created_at")

        if limit:
            notifications = notifications[:limit]

        return notifications


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

    @staticmethod
    def delete_author(author_id):
        """Delete an author"""
        author = Author.objects.get(id=author_id)

        # Check if author has books
        if author.books.exists():
            raise ValueError(
                "Cannot delete author with associated books. Remove books first."
            )

        author.delete()
        return True

    @staticmethod
    def toggle_author_status(author_id):
        """Toggle author active status"""
        author = Author.objects.get(id=author_id)
        author.active = not author.active
        author.save()
        return author


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

    @staticmethod
    def create_category(data):
        """Create a new category"""
        category = Category.objects.create(
            name=data["name"],
            description=data.get("description", ""),
            parent_category_id=data.get("parent_category"),
        )
        return category

    @staticmethod
    def update_category(category_id, data):
        """Update existing category"""
        category = Category.objects.get(id=category_id)
        category.name = data.get("name", category.name)
        category.description = data.get("description", category.description)

        if "parent_category" in data:
            category.parent_category_id = data["parent_category"]

        category.save()
        return category

    @staticmethod
    def delete_category(category_id):
        """Delete a category"""
        category = Category.objects.get(id=category_id)

        # Check if category has books
        if category.books.exists():
            raise ValueError(
                "Cannot delete category with associated books. Remove books first."
            )

        # Check if category has subcategories
        if category.subcategories.exists():
            raise ValueError(
                "Cannot delete category with subcategories. Remove subcategories first."
            )

        category.delete()
        return True


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

    @staticmethod
    def delete_publisher(publisher_id):
        """Delete a publisher"""
        publisher = Publisher.objects.get(id=publisher_id)

        # Check if publisher has books
        if publisher.books.exists():
            raise ValueError(
                "Cannot delete publisher with associated books. Remove books first."
            )

        publisher.delete()
        return True

    @staticmethod
    def toggle_publisher_status(publisher_id):
        """Toggle publisher active status"""
        publisher = Publisher.objects.get(id=publisher_id)
        publisher.active = not publisher.active
        publisher.save()
        return publisher


class RecommendationServices:
    """Services for generating personalized book recommendations"""

    @staticmethod
    def generate_recommendations_for_user(user, limit=10):
        """
        Generate personalized book recommendations based on user's borrowing history
        Uses collaborative filtering approach
        """
        from librarymanagement.models import BookRecommendation

        # Get user's borrowing history
        user_books = (
            BorrowingTransaction.objects.filter(user=user)
            .values_list("book_id", flat=True)
            .distinct()
        )

        if not user_books:
            # New user - recommend trending books
            return RecommendationServices._recommend_trending_books(user, limit)

        # Get categories user has borrowed from
        from django.db.models import Count

        user_categories = (
            Book.objects.filter(id__in=user_books)
            .values_list("categories", flat=True)
            .distinct()
        )

        # Find books in same categories that user hasn't borrowed
        recommended_books = (
            Book.objects.filter(categories__in=user_categories, status="available")
            .exclude(id__in=user_books)
            .annotate(category_match_count=Count("categories"))
            .order_by("-category_match_count")[:limit]
        )

        # Create recommendation records
        recommendations = []
        for book in recommended_books:
            score = min(100.0, book.category_match_count * 25.0)
            recommendation, created = BookRecommendation.objects.get_or_create(
                user=user,
                book=book,
                defaults={"score": score, "reason": "Based on your reading history"},
            )
            recommendations.append(recommendation)

        return recommendations

    @staticmethod
    def _recommend_trending_books(user, limit=10):
        """Recommend trending books for new users"""
        from librarymanagement.models import BookRecommendation

        trending = (
            TrendingBook.objects.filter(period_type="weekly", book__status="available")
            .select_related("book")
            .order_by("-popularity_score")[:limit]
        )

        recommendations = []
        for trend in trending:
            recommendation, created = BookRecommendation.objects.get_or_create(
                user=user,
                book=trend.book,
                defaults={
                    "score": min(100.0, float(trend.popularity_score)),
                    "reason": "Currently trending",
                },
            )
            recommendations.append(recommendation)

        return recommendations

    @staticmethod
    def update_all_recommendations():
        """Update recommendations for all active users"""
        from django.contrib.auth import get_user_model

        User = get_user_model()

        active_users = User.objects.filter(is_active=True)
        count = 0

        for user in active_users:
            RecommendationServices.generate_recommendations_for_user(user)
            count += 1

        return count

    @staticmethod
    def refresh_recommendations(user):
        """Regenerate recommendations for a specific user"""
        # Delete existing recommendations
        BookRecommendation.objects.filter(user=user).delete()

        # Generate new recommendations
        return RecommendationServices.generate_recommendations_for_user(user)

    @staticmethod
    def dismiss_recommendation(recommendation_id):
        """Remove a recommendation"""
        recommendation = BookRecommendation.objects.get(id=recommendation_id)
        recommendation.delete()
        return True

    @staticmethod
    def mark_recommendation_viewed(recommendation_id):
        """Mark recommendation as viewed"""
        recommendation = BookRecommendation.objects.get(id=recommendation_id)
        recommendation.viewed = True
        recommendation.save()
        return recommendation


class DataMiningServices:
    """Services for data mining and analytics"""

    @staticmethod
    def analyze_user_patterns():
        """
        Analyze user borrowing patterns and create user clusters
        Groups users based on their reading preferences
        """
        from librarymanagement.models import UserCluster
        from django.contrib.auth import get_user_model
        from collections import defaultdict

        User = get_user_model()
        users = User.objects.filter(is_active=True)

        # Gather user borrowing patterns
        user_patterns = defaultdict(
            lambda: {
                "categories": defaultdict(int),
                "total_borrows": 0,
                "avg_duration": 0,
            }
        )

        for user in users:
            transactions = BorrowingTransaction.objects.filter(user=user)

            if not transactions.exists():
                continue

            user_patterns[user.id]["total_borrows"] = transactions.count()

            # Analyze categories
            for trans in transactions:
                for category in trans.book.categories.all():
                    user_patterns[user.id]["categories"][category.name] += 1

        # Simple clustering based on dominant category
        clusters = defaultdict(list)

        for user_id, pattern in user_patterns.items():
            if not pattern["categories"]:
                clusters[0].append(user_id)  # Cluster 0 for users with no clear pattern
                continue

            # Find dominant category
            dominant_category = max(pattern["categories"].items(), key=lambda x: x[1])[
                0
            ]

            # Assign cluster based on category
            cluster_mapping = {
                "Fiction": 1,
                "Science": 2,
                "History": 3,
                "Technology": 4,
                "Arts": 5,
            }
            cluster_id = cluster_mapping.get(dominant_category, 6)
            clusters[cluster_id].append(user_id)

        # Save cluster assignments
        for cluster_id, user_ids in clusters.items():
            cluster_name = f"Cluster {cluster_id}"
            if cluster_id == 1:
                cluster_name = "Fiction Enthusiasts"
            elif cluster_id == 2:
                cluster_name = "Science Readers"
            elif cluster_id == 3:
                cluster_name = "History Buffs"
            elif cluster_id == 4:
                cluster_name = "Tech Readers"
            elif cluster_id == 5:
                cluster_name = "Arts & Culture"
            elif cluster_id == 0:
                cluster_name = "Diverse Readers"
            else:
                cluster_name = "General Readers"

            for user_id in user_ids:
                try:
                    user = User.objects.get(id=user_id)
                    UserCluster.objects.update_or_create(
                        user=user,
                        defaults={
                            "cluster_id": cluster_id,
                            "cluster_name": cluster_name,
                            "characteristics": user_patterns[user_id],
                        },
                    )
                except User.DoesNotExist:
                    continue

        return len(clusters)

    @staticmethod
    def analyze_trending_books(period_type="weekly"):
        """
        Analyze and update trending books based on recent activity
        Considers views, borrows, and reservations
        """
        from datetime import timedelta

        # Define period ranges
        period_ranges = {"daily": 1, "weekly": 7, "monthly": 30, "yearly": 365}

        days = period_ranges.get(period_type, 7)
        period_start = timezone.now().date() - timedelta(days=days)
        period_end = timezone.now().date()

        # Analyze activity for each book
        books = Book.objects.all()

        for book in books:
            # Count activities
            views = UserActivity.objects.filter(
                book=book,
                activity_type="view",
                timestamp__date__gte=period_start,
                timestamp__date__lte=period_end,
            ).count()

            borrows = BorrowingTransaction.objects.filter(
                book=book,
                borrowed_date__date__gte=period_start,
                borrowed_date__date__lte=period_end,
            ).count()

            reservations = Reservation.objects.filter(
                book=book,
                reservation_date__date__gte=period_start,
                reservation_date__date__lte=period_end,
            ).count()

            # Calculate popularity score
            # Weighted: borrows (5x), reservations (3x), views (1x)
            popularity_score = (borrows * 5) + (reservations * 3) + views

            if popularity_score > 0:
                TrendingBook.objects.update_or_create(
                    book=book,
                    period_type=period_type,
                    period_start=period_start,
                    defaults={
                        "period_end": period_end,
                        "view_count": views,
                        "borrow_count": borrows,
                        "reservation_count": reservations,
                        "popularity_score": popularity_score,
                    },
                )

        return TrendingBook.objects.filter(
            period_type=period_type, period_start=period_start
        ).count()

    @staticmethod
    def predict_demand(book_id=None):
        """
        Predict future demand for books based on historical trends
        Returns books that might need additional copies
        """
        from datetime import timedelta

        # Analyze past 3 months
        period_start = timezone.now().date() - timedelta(days=90)

        if book_id:
            books = Book.objects.filter(id=book_id)
        else:
            books = Book.objects.all()

        high_demand_books = []

        for book in books:
            # Count recent activity
            recent_borrows = BorrowingTransaction.objects.filter(
                book=book, borrowed_date__date__gte=period_start
            ).count()

            recent_reservations = Reservation.objects.filter(
                book=book, reservation_date__date__gte=period_start
            ).count()

            # Calculate demand ratio
            total_demand = recent_borrows + recent_reservations
            if total_demand > 0 and book.total_copies > 0:
                demand_ratio = total_demand / book.total_copies

                # If demand ratio > 3, book is in high demand
                if demand_ratio > 3:
                    high_demand_books.append(
                        {
                            "book": book,
                            "demand_ratio": round(demand_ratio, 2),
                            "recent_borrows": recent_borrows,
                            "recent_reservations": recent_reservations,
                            "recommended_copies": max(1, int(demand_ratio / 2)),
                        }
                    )

        return sorted(high_demand_books, key=lambda x: x["demand_ratio"], reverse=True)

    @staticmethod
    def generate_usage_insights(days=30):
        """
        Generate insights about library usage patterns
        Returns dictionary with key metrics and insights
        """
        from datetime import timedelta

        period_start = timezone.now().date() - timedelta(days=days)

        # Activity metrics
        total_activities = UserActivity.objects.filter(
            timestamp__date__gte=period_start
        ).count()

        activity_breakdown = (
            UserActivity.objects.filter(timestamp__date__gte=period_start)
            .values("activity_type")
            .annotate(count=Count("id"))
        )

        # Borrowing metrics
        total_borrows = BorrowingTransaction.objects.filter(
            borrowed_date__date__gte=period_start
        ).count()

        overdue_rate = 0
        if total_borrows > 0:
            overdue_count = BorrowingTransaction.objects.filter(
                borrowed_date__date__gte=period_start, status="overdue"
            ).count()
            overdue_rate = round((overdue_count / total_borrows) * 100, 2)

        # Popular categories
        popular_categories = (
            Category.objects.filter(
                books__borrowing_transactions__borrowed_date__date__gte=period_start
            )
            .annotate(borrow_count=Count("books__borrowing_transactions"))
            .order_by("-borrow_count")[:5]
        )

        # Peak usage hours (simplified - would need more complex analysis)
        peak_hours = (
            UserActivity.objects.filter(timestamp__date__gte=period_start)
            .extra(select={"hour": "EXTRACT(hour FROM timestamp)"})
            .values("hour")
            .annotate(count=Count("id"))
            .order_by("-count")[:3]
        )

        insights = {
            "period_days": days,
            "total_activities": total_activities,
            "activity_breakdown": list(activity_breakdown),
            "total_borrows": total_borrows,
            "overdue_rate": overdue_rate,
            "popular_categories": [
                {"name": cat.name, "count": cat.borrow_count}
                for cat in popular_categories
            ],
            "peak_hours": list(peak_hours),
            "insights": [],
        }

        # Generate textual insights
        if overdue_rate > 20:
            insights["insights"].append(
                f"High overdue rate ({overdue_rate}%) - consider reminder notifications"
            )

        if popular_categories:
            top_cat = popular_categories[0]
            insights["insights"].append(
                f"{top_cat.name} is the most popular category with {top_cat.borrow_count} borrows"
            )

        return insights


class LibrarySettingsServices:
    """Services for managing library settings"""

    @staticmethod
    def get_or_create_settings(library):
        """Get or create library settings"""
        from librarymanagement.models import LibrarySettings

        settings, created = LibrarySettings.objects.get_or_create(
            library=library,
            defaults={
                "library_name": library.name,
                "default_loan_period_days": 14,
                "maximum_renewals": 2,
                "maximum_books_per_user": 5,
                "enable_fines": True,
                "daily_fine_amount": Decimal("1.00"),
                "maximum_fine_amount": Decimal("50.00"),
                "grace_period_days": 0,
                "enable_email_notifications": True,
                "enable_sms_notifications": False,
                "notify_due_dates": True,
                "notify_overdue": True,
                "notify_reservation_ready": True,
                "days_before_due_notification": 3,
                "enable_book_recommendations": True,
                "enable_trending_analysis": True,
                "enable_user_analytics": True,
                "enable_digital_resources": True,
                "reservation_expiry_days": 3,
                "auto_extend_on_no_reservation": False,
            },
        )
        return settings

    @staticmethod
    def update_general_settings(library, **kwargs):
        """Update general library settings"""
        settings = LibrarySettingsServices.get_or_create_settings(library)

        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        settings.save()
        return settings

    @staticmethod
    def update_fine_settings(library, **kwargs):
        """Update fine-related settings"""
        settings = LibrarySettingsServices.get_or_create_settings(library)

        fine_fields = [
            "enable_fines",
            "daily_fine_amount",
            "maximum_fine_amount",
            "grace_period_days",
        ]

        for key, value in kwargs.items():
            if key in fine_fields and hasattr(settings, key):
                setattr(settings, key, value)

        settings.save()
        return settings

    @staticmethod
    def update_notification_settings(library, **kwargs):
        """Update notification preferences"""
        settings = LibrarySettingsServices.get_or_create_settings(library)

        notification_fields = [
            "enable_email_notifications",
            "enable_sms_notifications",
            "notify_due_dates",
            "notify_overdue",
            "notify_reservation_ready",
            "days_before_due_notification",
        ]

        for key, value in kwargs.items():
            if key in notification_fields and hasattr(settings, key):
                setattr(settings, key, value)

        settings.save()
        return settings

    @staticmethod
    def update_feature_settings(library, **kwargs):
        """Update feature toggles"""
        settings = LibrarySettingsServices.get_or_create_settings(library)

        feature_fields = [
            "enable_book_recommendations",
            "enable_trending_analysis",
            "enable_user_analytics",
            "enable_digital_resources",
        ]

        for key, value in kwargs.items():
            if key in feature_fields and hasattr(settings, key):
                setattr(settings, key, value)

        settings.save()
        return settings

    @staticmethod
    def export_library_data(library):
        """Export library data as JSON"""
        import json

        data = {
            "library": {
                "name": library.name,
                "description": library.description,
                "location": library.location,
            },
            "books_count": library.books.count(),
            "active_transactions": BorrowingTransaction.objects.filter(
                book__library=library, status="active"
            ).count(),
            "total_users": (
                BorrowingTransaction.objects.filter(book__library=library)
                .values("user")
                .distinct()
                .count()
            ),
        }

        return json.dumps(data, indent=2)


class AdvancedSearchServices:
    """Services for advanced search and filtering"""

    @staticmethod
    def search_books(
        query=None,
        category_ids=None,
        author_ids=None,
        publisher_id=None,
        status=None,
        resource_type=None,
        year_from=None,
        year_to=None,
        language=None,
    ):
        """Advanced book search with multiple criteria"""
        books = Book.objects.all()

        if query:
            from django.db.models import Q

            books = books.filter(
                Q(title__icontains=query)
                | Q(subtitle__icontains=query)
                | Q(isbn__icontains=query)
                | Q(subject__icontains=query)
                | Q(description__icontains=query)
            )

        if category_ids:
            books = books.filter(categories__id__in=category_ids).distinct()

        if author_ids:
            books = books.filter(authors__id__in=author_ids).distinct()

        if publisher_id:
            books = books.filter(publisher_id=publisher_id)

        if status:
            books = books.filter(status=status)

        if resource_type:
            books = books.filter(resource_type=resource_type)

        if year_from:
            books = books.filter(publication_year__gte=year_from)

        if year_to:
            books = books.filter(publication_year__lte=year_to)

        if language:
            books = books.filter(language__iexact=language)

        return books.select_related("library", "publisher").prefetch_related(
            "authors", "categories"
        )

    @staticmethod
    def filter_transactions(
        user_id=None,
        book_id=None,
        status=None,
        date_from=None,
        date_to=None,
        overdue_only=False,
    ):
        """Filter borrowing transactions"""
        transactions = BorrowingTransaction.objects.all()

        if user_id:
            transactions = transactions.filter(user_id=user_id)

        if book_id:
            transactions = transactions.filter(book_id=book_id)

        if status:
            transactions = transactions.filter(status=status)

        if date_from:
            transactions = transactions.filter(borrowed_date__date__gte=date_from)

        if date_to:
            transactions = transactions.filter(borrowed_date__date__lte=date_to)

        if overdue_only:
            transactions = transactions.filter(status="overdue")

        return transactions.select_related("user", "book", "issued_by")

    @staticmethod
    def filter_reservations(
        user_id=None, book_id=None, status=None, date_from=None, date_to=None
    ):
        """Filter reservations"""
        reservations = Reservation.objects.all()

        if user_id:
            reservations = reservations.filter(user_id=user_id)

        if book_id:
            reservations = reservations.filter(book_id=book_id)

        if status:
            reservations = reservations.filter(status=status)

        if date_from:
            reservations = reservations.filter(reservation_date__date__gte=date_from)

        if date_to:
            reservations = reservations.filter(reservation_date__date__lte=date_to)

        return reservations.select_related("user", "book")


class UserActivityServices:
    """Services for tracking and managing user activities"""

    @staticmethod
    def track_book_view(user, book, session_id=None):
        """Track when a user views a book"""
        if not user.is_authenticated:
            return None

        activity = UserActivity.objects.create(
            user=user,
            book=book,
            activity_type="view",
            session_id=session_id or "",
        )
        return activity

    @staticmethod
    def track_search(user, search_query, session_id=None):
        """Track user search queries"""
        if not user.is_authenticated:
            return None

        activity = UserActivity.objects.create(
            user=user,
            activity_type="search",
            search_query=search_query,
            session_id=session_id or "",
        )
        return activity

    @staticmethod
    def get_user_activities(user, activity_type=None, days=30):
        """Get user's activity history"""
        from datetime import timedelta

        period_start = timezone.now() - timedelta(days=days)
        activities = UserActivity.objects.filter(
            user=user, timestamp__gte=period_start
        )

        if activity_type:
            activities = activities.filter(activity_type=activity_type)

        return activities.select_related("book")

    @staticmethod
    def delete_old_activities(days=90):
        """Delete activities older than specified days"""
        from datetime import timedelta

        cutoff_date = timezone.now() - timedelta(days=days)
        deleted_count = UserActivity.objects.filter(
            timestamp__lt=cutoff_date
        ).delete()[0]
        return deleted_count

    @staticmethod
    def export_user_activity(user):
        """Export user's activity data (GDPR compliance)"""
        import json

        activities = UserActivity.objects.filter(user=user).select_related("book")

        data = {
            "user": user.username,
            "total_activities": activities.count(),
            "activities": [
                {
                    "type": activity.activity_type,
                    "book": activity.book.title if activity.book else None,
                    "search_query": activity.search_query,
                    "timestamp": activity.timestamp.isoformat(),
                }
                for activity in activities
            ],
        }

        return json.dumps(data, indent=2)


class UserProfileServices:
    """Services for user profile management"""

    @staticmethod
    def get_borrowing_history(user, limit=None):
        """Get user's complete borrowing history"""
        transactions = BorrowingTransaction.objects.filter(user=user).select_related(
            "book", "issued_by"
        )

        if limit:
            transactions = transactions[:limit]

        return transactions

    @staticmethod
    def get_reservation_history(user, limit=None):
        """Get user's reservation history"""
        reservations = Reservation.objects.filter(user=user).select_related("book")

        if limit:
            reservations = reservations[:limit]

        return reservations

    @staticmethod
    def export_user_data(user):
        """Export user's library data (GDPR compliance)"""
        import json

        transactions = BorrowingTransaction.objects.filter(user=user)
        reservations = Reservation.objects.filter(user=user)
        recommendations = BookRecommendation.objects.filter(user=user)

        data = {
            "user": {
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
            "borrowing_history": [
                {
                    "book": trans.book.title,
                    "borrowed_date": trans.borrowed_date.isoformat(),
                    "due_date": trans.due_date.isoformat(),
                    "return_date": (
                        trans.return_date.isoformat() if trans.return_date else None
                    ),
                    "status": trans.status,
                }
                for trans in transactions
            ],
            "reservations": [
                {
                    "book": res.book.title,
                    "reservation_date": res.reservation_date.isoformat(),
                    "status": res.status,
                }
                for res in reservations
            ],
            "recommendations_count": recommendations.count(),
        }

        return json.dumps(data, indent=2)


class TrendingServices:
    """Services for trending and popular books"""

    @staticmethod
    def get_trending_by_category(category_id, period_type="weekly", limit=10):
        """Get trending books filtered by category"""
        from datetime import timedelta

        period_ranges = {"daily": 1, "weekly": 7, "monthly": 30, "yearly": 365}
        days = period_ranges.get(period_type, 7)
        period_start = timezone.now().date() - timedelta(days=days)

        trending_books = (
            TrendingBook.objects.filter(
                period_type=period_type,
                period_start=period_start,
                book__categories__id=category_id,
            )
            .select_related("book")
            .order_by("-popularity_score")[:limit]
        )

        return trending_books

    @staticmethod
    def update_trending_metrics(period_type="weekly"):
        """Calculate and update trending scores - for scheduled job"""
        return DataMiningServices.analyze_trending_books(period_type)

    @staticmethod
    def export_trending_report(period_type="weekly"):
        """Export trending data as JSON"""
        import json
        from datetime import timedelta

        period_ranges = {"daily": 1, "weekly": 7, "monthly": 30, "yearly": 365}
        days = period_ranges.get(period_type, 7)
        period_start = timezone.now().date() - timedelta(days=days)

        trending_books = TrendingBook.objects.filter(
            period_type=period_type, period_start=period_start
        ).select_related("book")[:20]

        data = {
            "period_type": period_type,
            "period_start": str(period_start),
            "trending_books": [
                {
                    "title": tb.book.title,
                    "popularity_score": str(tb.popularity_score),
                    "view_count": tb.view_count,
                    "borrow_count": tb.borrow_count,
                    "reservation_count": tb.reservation_count,
                }
                for tb in trending_books
            ],
        }

        return json.dumps(data, indent=2)
