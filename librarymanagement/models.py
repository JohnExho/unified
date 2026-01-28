from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid
from django.utils import timezone
import datetime

def manila_now():
    return timezone.now().astimezone(timezone.get_fixed_timezone(8*60))
# Create your models here.


class Library(models.Model):
    """Main library entity"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=300, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Libraries"
        permissions = [
            (
                "access_library_management_system",
                "Can access Library Management system",
            ),
        ]

    def __str__(self):
        return self.name


class Category(models.Model):
    """Book categories for classification"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    parent_category = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="subcategories",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Author(models.Model):
    """Author information"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    birth_date = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        if self.middle_name:
            return f"{self.first_name} {self.middle_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"


class Publisher(models.Model):
    """Publisher information"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    address = models.TextField(blank=True)
    website = models.URLField(blank=True)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Book(models.Model):
    """Main book resource entity"""

    RESOURCE_TYPE_CHOICES = [
        ("physical", "Physical Book"),
        ("digital", "Digital Resource"),
        ("audio", "Audio Book"),
        ("video", "Video Resource"),
    ]

    STATUS_CHOICES = [
        ("available", "Available"),
        ("borrowed", "Borrowed"),
        ("reserved", "Reserved"),
        ("maintenance", "Under Maintenance"),
        ("lost", "Lost"),
        ("damaged", "Damaged"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    library = models.ForeignKey(Library, on_delete=models.CASCADE, related_name="books")
    accession_number = models.CharField(
        max_length=50, unique=True, help_text="Unique identifier for the book copy"
    )

    # Book details
    title = models.CharField(max_length=300)
    subtitle = models.CharField(max_length=300, blank=True)
    isbn = models.CharField(max_length=13, blank=True, help_text="13-digit ISBN")
    authors = models.ManyToManyField(Author, related_name="books")
    publisher = models.ForeignKey(
        Publisher, on_delete=models.SET_NULL, null=True, blank=True
    )
    publication_year = models.IntegerField(null=True, blank=True)
    edition = models.CharField(max_length=50, blank=True)

    # Classification
    categories = models.ManyToManyField(Category, related_name="books")
    subject = models.CharField(max_length=200, blank=True)
    language = models.CharField(max_length=50, default="English")

    # Physical details
    pages = models.IntegerField(null=True, blank=True)
    resource_type = models.CharField(
        max_length=20, choices=RESOURCE_TYPE_CHOICES, default="physical"
    )

    # Status and availability
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="available"
    )
    total_copies = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    available_copies = models.IntegerField(default=1, validators=[MinValueValidator(0)])

    # Additional information
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to="library/covers/", null=True, blank=True)
    digital_file = models.FileField(upload_to="library/digital/", null=True, blank=True)
    shelf_location = models.CharField(
        max_length=100, blank=True, help_text="Physical location in library"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="books_created",
    )

    class Meta:
        ordering = ["title"]
        indexes = [
            models.Index(fields=["isbn"]),
            models.Index(fields=["accession_number"]),
            models.Index(fields=["title"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.accession_number})"

    @property
    def is_available(self):
        return self.status == "available" and self.available_copies > 0


class BorrowingTransaction(models.Model):
    """Tracks book borrowing and returning"""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("returned", "Returned"),
        ("overdue", "Overdue"),
        ("lost", "Lost"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="borrowing_transactions",
    )
    book = models.ForeignKey(
        Book, on_delete=models.CASCADE, related_name="borrowing_transactions"
    )

    # Transaction dates
    borrowed_date = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField()
    return_date = models.DateTimeField(null=True, blank=True)

    # Status and management
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    renewal_count = models.IntegerField(default=0)

    fine_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    days_overdue = models.IntegerField(default=0)

    # Additional notes
    notes = models.TextField(blank=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="transactions_issued",
    )

    class Meta:
        ordering = ["-borrowed_date"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["book", "status"]),
            models.Index(fields=["due_date"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.book.title} ({self.status})"

    @property
    def is_overdue(self):
        if self.status == "returned":
            return False
        return timezone.now() > self.due_date


class Reservation(models.Model):
    """Book reservation system"""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("ready", "Ready for Pickup"),
        ("fulfilled", "Fulfilled"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reservations"
    )
    book = models.ForeignKey(
        Book, on_delete=models.CASCADE, related_name="reservations"
    )

    # Reservation details
    reservation_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Fulfillment
    fulfilled_date = models.DateTimeField(null=True, blank=True)
    notified = models.BooleanField(default=False)
    notified_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-reservation_date"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["book", "status"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.book.title} ({self.status})"


class UserActivity(models.Model):
    """Tracks user activities for data mining and recommendations"""

    ACTIVITY_TYPES = [
        ("view", "Viewed"),
        ("search", "Searched"),
        ("borrow", "Borrowed"),
        ("reserve", "Reserved"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="library_activities",
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="user_activities",
    )

    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    search_query = models.CharField(max_length=300, blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)
    session_id = models.CharField(max_length=100, blank=True)

    # Metadata for analysis
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name_plural = "User Activities"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user", "activity_type"]),
            models.Index(fields=["book", "activity_type"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.activity_type} - {self.timestamp}"


class BookRecommendation(models.Model):
    """Stores personalized book recommendations"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="book_recommendations",
    )
    book = models.ForeignKey(
        Book, on_delete=models.CASCADE, related_name="recommendations"
    )

    score = models.DecimalField(
        max_digits=5, decimal_places=2, help_text="Recommendation confidence score"
    )
    reason = models.CharField(
        max_length=200, blank=True, help_text="Why this book was recommended"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    viewed = models.BooleanField(default=False)
    actioned = models.BooleanField(default=False)  # User borrowed or reserved

    class Meta:
        ordering = ["-score", "-created_at"]
        unique_together = ("user", "book")
        indexes = [
            models.Index(fields=["user", "viewed"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.book.title} (Score: {self.score})"


class TrendingBook(models.Model):
    """Tracks trending and popular books"""

    TREND_PERIOD = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    book = models.ForeignKey(
        Book, on_delete=models.CASCADE, related_name="trending_records"
    )

    period_type = models.CharField(max_length=20, choices=TREND_PERIOD)
    period_start = models.DateField()
    period_end = models.DateField()

    view_count = models.IntegerField(default=0)
    borrow_count = models.IntegerField(default=0)
    reservation_count = models.IntegerField(default=0)
    popularity_score = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-popularity_score", "-period_start"]
        unique_together = ("book", "period_type", "period_start")
        indexes = [
            models.Index(fields=["period_type", "period_start"]),
            models.Index(fields=["popularity_score"]),
        ]

    def __str__(self):
        return f"{self.book.title} - {self.period_type} ({self.period_start})"


class UserCluster(models.Model):
    """Stores user clustering data for data mining"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_clusters"
    )

    cluster_id = models.IntegerField()
    cluster_name = models.CharField(max_length=100, blank=True)
    characteristics = models.JSONField(
        default=dict, help_text="Cluster characteristics and patterns"
    )

    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["cluster_id"]
        indexes = [
            models.Index(fields=["cluster_id"]),
        ]

    def __str__(self):
        return f"{self.user.username} - Cluster {self.cluster_id}"


class LibraryReport(models.Model):
    """Stores generated reports for decision support"""

    REPORT_TYPES = [
        ("usage", "Usage Report"),
        ("circulation", "Circulation Report"),
        ("trending", "Trending Analysis"),
        ("user_behavior", "User Behavior Analysis"),
        ("inventory", "Inventory Report"),
        ("acquisition", "Acquisition Recommendation"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report_type = models.CharField(max_length=30, choices=REPORT_TYPES)
    title = models.CharField(max_length=200)

    period_start = models.DateField()
    period_end = models.DateField()

    data = models.JSONField(help_text="Report data and statistics")
    summary = models.TextField(blank=True)

    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    generated_at = models.DateTimeField(auto_now_add=True)

    file = models.FileField(upload_to="library/reports/", null=True, blank=True)

    class Meta:
        ordering = ["-generated_at"]
        indexes = [
            models.Index(fields=["report_type", "period_start"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.period_start} to {self.period_end})"


class Notification(models.Model):
    """Library notifications for users"""

    NOTIFICATION_TYPES = [
        ("due_soon", "Due Soon"),
        ("overdue", "Overdue"),
        ("reservation_ready", "Reservation Ready"),
        ("reservation_expiring", "Reservation Expiring"),
        ("announcement", "Announcement"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="library_notifications",
    )

    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()

    related_transaction = models.ForeignKey(
        BorrowingTransaction, on_delete=models.SET_NULL, null=True, blank=True
    )
    related_reservation = models.ForeignKey(
        Reservation, on_delete=models.SET_NULL, null=True, blank=True
    )

    is_read = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.notification_type}"
