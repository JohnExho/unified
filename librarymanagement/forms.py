from django import forms
from django.utils import timezone
from .models import (
    Library,
    Category,
    Author,
    Publisher,
    Book,
    BorrowingTransaction,
    Reservation,
    LibraryReport,
    Notification,
    LibrarySettings,
)
import json


class LibraryForm(forms.ModelForm):
    """Form for creating and editing libraries"""

    class Meta:
        model = Library
        fields = [
            "name",
            "description",
            "location",
            "contact_email",
            "contact_phone",
            "operating_hours",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Library Name"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Library Description",
                }
            ),
            "location": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Physical Location"}
            ),
            "contact_email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "contact@library.com"}
            ),
            "contact_phone": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "+1234567890"}
            ),
            "operating_hours": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Mon-Fri: 8AM - 8PM",
                }
            ),
        }


class CategoryForm(forms.ModelForm):
    """Form for creating and editing categories"""

    class Meta:
        model = Category
        fields = ["name", "description", "parent_category"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Category Name"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Category Description",
                }
            ),
            "parent_category": forms.Select(attrs={"class": "form-control"}),
        }

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if name:
            name = name.strip()
            # Check for duplicates, excluding current instance if editing
            qs = Category.objects.filter(name__iexact=name)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("A category with this name already exists.")
        return name

    def clean(self):
        cleaned_data = super().clean()
        parent = cleaned_data.get("parent_category")

        # Prevent circular references
        if parent and self.instance and self.instance.pk:
            if parent == self.instance:
                raise forms.ValidationError("A category cannot be its own parent.")

            # Check if parent is a descendant of this category
            current = parent
            while current.parent_category:
                if current.parent_category == self.instance:
                    raise forms.ValidationError(
                        "Cannot create circular category hierarchy."
                    )
                current = current.parent_category

        return cleaned_data


class AuthorForm(forms.ModelForm):
    """Form for creating and editing authors"""

    class Meta:
        model = Author
        fields = [
            "first_name",
            "last_name",
            "middle_name",
            "bio",
            "birth_date",
            "nationality",
        ]
        widgets = {
            "first_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "First Name"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Last Name"}
            ),
            "middle_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Middle Name (Optional)"}
            ),
            "bio": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Author Biography",
                }
            ),
            "birth_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "nationality": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Nationality"}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        first_name = cleaned_data.get("first_name")
        last_name = cleaned_data.get("last_name")

        if first_name:
            cleaned_data["first_name"] = first_name.strip()
        if last_name:
            cleaned_data["last_name"] = last_name.strip()

        return cleaned_data


class PublisherForm(forms.ModelForm):
    """Form for creating and editing publishers"""

    class Meta:
        model = Publisher
        fields = ["name", "address", "website", "email"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Publisher Name"}
            ),
            "address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Publisher Address",
                }
            ),
            "website": forms.URLInput(
                attrs={"class": "form-control", "placeholder": "https://publisher.com"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "contact@publisher.com"}
            ),
        }

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if name:
            name = name.strip()
            # Check for duplicates, excluding current instance if editing
            qs = Publisher.objects.filter(name__iexact=name)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    "A publisher with this name already exists."
                )
        return name


class BookForm(forms.ModelForm):
    """Form for creating and editing books"""

    categories_tagify = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Book
        fields = [
            "library",
            "accession_number",
            "title",
            "subtitle",
            "isbn",
            "authors",
            "publisher",
            "publication_year",
            "edition",
            "categories",
            "subject",
            "language",
            "pages",
            "resource_type",
            "status",
            "total_copies",
            "available_copies",
            "description",
            "cover_image",
            "digital_file",
            "shelf_location",
        ]
        widgets = {
            "library": forms.Select(attrs={"class": "form-control"}),
            "accession_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Unique Accession Number",
                }
            ),
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Book Title"}
            ),
            "subtitle": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Subtitle (Optional)"}
            ),
            "isbn": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "13-digit ISBN"}
            ),
            "authors": forms.SelectMultiple(attrs={"class": "form-control"}),
            "publisher": forms.Select(attrs={"class": "form-control"}),
            "publication_year": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Year"}
            ),
            "edition": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Edition"}
            ),
            "categories": forms.SelectMultiple(attrs={"class": "form-control"}),
            "subject": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Subject"}
            ),
            "language": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Language"}
            ),
            "pages": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "Number of Pages"}
            ),
            "resource_type": forms.Select(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "total_copies": forms.NumberInput(
                attrs={"class": "form-control", "min": "1"}
            ),
            "available_copies": forms.NumberInput(
                attrs={"class": "form-control", "min": "0"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Book Description",
                }
            ),
            "shelf_location": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Shelf Location"}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        # Handle tagify categories
        tagify_raw = self.data.get("categories") or self.data.get("categories_tagify")
        category_names = []
        if tagify_raw:
            try:
                tagify_data = json.loads(tagify_raw)
                if isinstance(tagify_data, list):
                    category_names = [
                        item["value"] for item in tagify_data if "value" in item
                    ]
            except Exception:
                # fallback: comma-separated
                category_names = [x.strip() for x in tagify_raw.split(",") if x.strip()]
        cleaned_data["categories"] = category_names

        # Validate copies
        total_copies = cleaned_data.get("total_copies")
        available_copies = cleaned_data.get("available_copies")

        if total_copies is not None and available_copies is not None:
            if available_copies > total_copies:
                raise forms.ValidationError(
                    "Available copies cannot exceed total copies."
                )

        # Validate ISBN
        isbn = cleaned_data.get("isbn")
        if isbn:
            # Remove hyphens and spaces
            isbn = isbn.replace("-", "").replace(" ", "")
            if len(isbn) not in [10, 13]:
                raise forms.ValidationError("ISBN must be 10 or 13 digits.")
            cleaned_data["isbn"] = isbn

        return cleaned_data


class BorrowingTransactionForm(forms.ModelForm):
    """Form for creating and editing borrowing transactions"""

    class Meta:
        model = BorrowingTransaction
        fields = [
            "user",
            "book",
            "due_date",
            "status",
            "renewal_count",
            "fine_amount",
            "notes",
        ]
        widgets = {
            "user": forms.Select(attrs={"class": "form-control"}),
            "book": forms.Select(attrs={"class": "form-control"}),
            "due_date": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "status": forms.Select(attrs={"class": "form-control"}),
            "renewal_count": forms.NumberInput(
                attrs={"class": "form-control", "min": "0"}
            ),
            "fine_amount": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Additional Notes",
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        book = cleaned_data.get("book")
        user = cleaned_data.get("user")

        # Check if book is available (only for new transactions)
        if not self.instance.pk and book:
            if not book.is_available:
                raise forms.ValidationError(
                    f"Book '{book.title}' is not available for borrowing."
                )

        # Check if user has overdue books
        if not self.instance.pk and user:
            overdue_count = BorrowingTransaction.objects.filter(
                user=user, status="overdue"
            ).count()
            if overdue_count > 0:
                raise forms.ValidationError(
                    f"User has {overdue_count} overdue book(s). Please return them first."
                )

        return cleaned_data


class ReturnBookForm(forms.Form):
    """Form for returning books"""

    transaction_id = forms.UUIDField(widget=forms.HiddenInput())
    return_date = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={"class": "form-control", "type": "datetime-local"}
        ),
        initial=timezone.now,
    )
    condition_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Book condition notes",
            }
        ),
        help_text="Note any damage or issues with the returned book",
    )
    apply_fine = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        help_text="Check if fine should be applied for overdue",
    )


class RenewBookForm(forms.Form):
    """Form for renewing borrowed books"""

    transaction_id = forms.UUIDField(widget=forms.HiddenInput())
    extend_days = forms.IntegerField(
        min_value=1,
        max_value=30,
        initial=14,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        help_text="Number of days to extend the due date",
    )


class ReservationForm(forms.ModelForm):
    """Form for creating and editing reservations"""

    class Meta:
        model = Reservation
        fields = [
            "user",
            "book",
            "expiry_date",
            "status",
            "notes",
        ]
        widgets = {
            "user": forms.Select(attrs={"class": "form-control"}),
            "book": forms.Select(attrs={"class": "form-control"}),
            "expiry_date": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"}
            ),
            "status": forms.Select(attrs={"class": "form-control"}),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Reservation Notes",
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        book = cleaned_data.get("book")
        user = cleaned_data.get("user")

        # Check if user already has an active reservation for this book
        if not self.instance.pk and book and user:
            existing = Reservation.objects.filter(
                user=user, book=book, status__in=["pending", "ready"]
            ).exists()

            if existing:
                raise forms.ValidationError(
                    "You already have an active reservation for this book."
                )

        return cleaned_data


class LibraryReportForm(forms.ModelForm):
    """Form for generating library reports"""

    class Meta:
        model = LibraryReport
        fields = [
            "report_type",
            "title",
            "period_start",
            "period_end",
            "summary",
        ]
        widgets = {
            "report_type": forms.Select(attrs={"class": "form-control"}),
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Report Title"}
            ),
            "period_start": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "period_end": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "summary": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Report Summary",
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        period_start = cleaned_data.get("period_start")
        period_end = cleaned_data.get("period_end")

        if period_start and period_end:
            if period_end < period_start:
                raise forms.ValidationError("End date cannot be before start date.")

        return cleaned_data


class NotificationForm(forms.ModelForm):
    """Form for creating and editing notifications"""

    class Meta:
        model = Notification
        fields = [
            "user",
            "notification_type",
            "title",
            "message",
            "related_transaction",
            "related_reservation",
        ]
        widgets = {
            "user": forms.Select(attrs={"class": "form-control"}),
            "notification_type": forms.Select(attrs={"class": "form-control"}),
            "title": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Notification Title"}
            ),
            "message": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Notification Message",
                }
            ),
            "related_transaction": forms.Select(attrs={"class": "form-control"}),
            "related_reservation": forms.Select(attrs={"class": "form-control"}),
        }


class BookSearchForm(forms.Form):
    """Form for searching books"""

    query = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Search by title, author, ISBN, or keyword...",
            }
        ),
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
        empty_label="All Categories",
    )
    resource_type = forms.ChoiceField(
        choices=[("", "All Types")] + list(Book.RESOURCE_TYPE_CHOICES),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    status = forms.ChoiceField(
        choices=[("", "All Status")] + list(Book.STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    language = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Language"}
        ),
    )


class BulkBookImportForm(forms.Form):
    """Form for bulk importing books from CSV/Excel"""

    file = forms.FileField(
        widget=forms.FileInput(
            attrs={"class": "form-control", "accept": ".csv,.xlsx,.xls"}
        ),
        help_text="Upload CSV or Excel file with book data",
    )
    library = forms.ModelChoiceField(
        queryset=Library.objects.all(),
        widget=forms.Select(attrs={"class": "form-control"}),
        help_text="Select the library these books belong to",
    )
    update_existing = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        help_text="Update existing books with matching ISBN or accession number",
    )


class LibrarySettingsForm(forms.ModelForm):
    """Form for library settings"""

    class Meta:
        model = LibrarySettings
        fields = [
            "library_name",
            "default_loan_period_days",
            "maximum_renewals",
            "maximum_books_per_user",
            "enable_fines",
            "daily_fine_amount",
            "maximum_fine_amount",
            "grace_period_days",
            "enable_email_notifications",
            "enable_sms_notifications",
            "notify_due_dates",
            "notify_overdue",
            "notify_reservation_ready",
            "days_before_due_notification",
            "enable_book_recommendations",
            "enable_trending_analysis",
            "enable_user_analytics",
            "enable_digital_resources",
            "reservation_expiry_days",
            "auto_extend_on_no_reservation",
        ]
        widgets = {
            "library_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Library Name"}
            ),
            "default_loan_period_days": forms.NumberInput(
                attrs={"class": "form-control", "min": "1"}
            ),
            "maximum_renewals": forms.NumberInput(
                attrs={"class": "form-control", "min": "0"}
            ),
            "maximum_books_per_user": forms.NumberInput(
                attrs={"class": "form-control", "min": "1"}
            ),
            "enable_fines": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "daily_fine_amount": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "maximum_fine_amount": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "grace_period_days": forms.NumberInput(
                attrs={"class": "form-control", "min": "0"}
            ),
            "enable_email_notifications": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "enable_sms_notifications": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "notify_due_dates": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "notify_overdue": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "notify_reservation_ready": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "days_before_due_notification": forms.NumberInput(
                attrs={"class": "form-control", "min": "1"}
            ),
            "enable_book_recommendations": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "enable_trending_analysis": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "enable_user_analytics": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "enable_digital_resources": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "reservation_expiry_days": forms.NumberInput(
                attrs={"class": "form-control", "min": "1"}
            ),
            "auto_extend_on_no_reservation": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }


class AdvancedSearchForm(forms.Form):
    """Form for advanced book search"""

    query = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Search by title, ISBN, or keyword...",
            }
        ),
    )
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-control"}),
    )
    authors = forms.ModelMultipleChoiceField(
        queryset=Author.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-control"}),
    )
    publisher = forms.ModelChoiceField(
        queryset=Publisher.objects.all(),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
        empty_label="All Publishers",
    )
    status = forms.ChoiceField(
        choices=[("", "All Status")] + list(Book.STATUS_CHOICES),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    resource_type = forms.ChoiceField(
        choices=[("", "All Types")] + list(Book.RESOURCE_TYPE_CHOICES),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    year_from = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "Year from"}
        ),
    )
    year_to = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "Year to"}
        ),
    )
    language = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Language"}
        ),
    )


class FinePaymentForm(forms.Form):
    """Form for recording fine payment"""

    transaction_id = forms.UUIDField(widget=forms.HiddenInput())
    amount_paid = forms.DecimalField(
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "step": "0.01", "min": "0"}
        ),
        help_text="Amount paid by user",
    )
    payment_method = forms.ChoiceField(
        choices=[
            ("cash", "Cash"),
            ("card", "Card"),
            ("gcash", "GCash"),
            ("bank_transfer", "Bank Transfer"),
            ("other", "Other"),
        ],
        widget=forms.Select(attrs={"class": "form-control"}),
    )


class WaiveFineForm(forms.Form):
    """Form for waiving fines"""

    transaction_id = forms.UUIDField(widget=forms.HiddenInput())
    waive_amount = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "step": "0.01", "min": "0"}
        ),
        help_text="Amount to waive (leave blank to waive all)",
    )
    reason = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Reason for waiving fine",
            }
        ),
        help_text="Reason for waiving the fine",
    )


class ExtendDueDateForm(forms.Form):
    """Form for extending due dates"""

    transaction_id = forms.UUIDField(widget=forms.HiddenInput())
    additional_days = forms.IntegerField(
        min_value=1,
        max_value=30,
        initial=7,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
        help_text="Number of days to extend",
    )


class BulkReturnForm(forms.Form):
    """Form for bulk returning books"""

    transaction_ids = forms.CharField(
        widget=forms.HiddenInput(),
        help_text="Comma-separated transaction IDs",
    )
    return_date = forms.DateTimeField(
        widget=forms.DateTimeInput(
            attrs={"class": "form-control", "type": "datetime-local"}
        ),
        initial=timezone.now,
    )
