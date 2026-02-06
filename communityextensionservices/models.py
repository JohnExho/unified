import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class Service(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        permissions = [
            (
                "access_community_extension_services_system",
                "Can access Community Extension Services system",
            ),
        ]

    def __str__(self):
        return self.name


class Member(models.Model):
    CLASSIFICATION_CHOICES = [
        ("faculty", "Faculty"),
        ("non_teaching", "Non-Teaching Staff"),
        ("retired", "Retired"),
        ("associate", "Associate"),
    ]
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("suspended", "Suspended"),
    ]

    membership_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    classification = models.CharField(
        max_length=20, choices=CLASSIFICATION_CHOICES, default="faculty"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    joined_date = models.DateField(default=timezone.now)
    exit_date = models.DateField(null=True, blank=True)
    department = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)

    # ML placeholders
    engagement_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    churn_risk_score = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    predicted_status = models.CharField(max_length=30, blank=True)
    cluster_label = models.CharField(max_length=30, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.last_name}, {self.first_name}"


class MembershipHistory(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=Member.STATUS_CHOICES)
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.member} → {self.status}"


class DuesPayment(models.Model):
    STATUS_CHOICES = [
        ("paid", "Paid"),
        ("pending", "Pending"),
        ("overdue", "Overdue"),
    ]
    METHOD_CHOICES = [
        ("cash", "Cash"),
        ("check", "Check"),
        ("payroll", "Payroll Deduction"),
        ("other", "Other"),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default="cash")
    reference_no = models.CharField(max_length=60, blank=True)
    remarks = models.TextField(blank=True)

    # ML placeholder
    late_payment_risk = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    class Meta:
        ordering = ["-due_date"]

    def __str__(self):
        return f"{self.member} - {self.amount}"


class Contribution(models.Model):
    CATEGORY_CHOICES = [
        ("in_kind", "In-kind"),
        ("cash", "Cash"),
        ("volunteer", "Volunteer Hours"),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    title = models.CharField(max_length=120)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="cash")
    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    date = models.DateField(default=timezone.now)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.member} - {self.title}"


class Activity(models.Model):
    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    title = models.CharField(max_length=160)
    category = models.CharField(max_length=100, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    location = models.CharField(max_length=160, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="scheduled"
    )
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return self.title


class Attendance(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    role = models.CharField(max_length=80, blank=True)
    attended = models.BooleanField(default=False)
    remarks = models.TextField(blank=True)

    class Meta:
        unique_together = ("member", "activity")

    def __str__(self):
        return f"{self.member} - {self.activity}"


class DocumentRecord(models.Model):
    CATEGORY_CHOICES = [
        ("policy", "Policy"),
        ("minutes", "Minutes"),
        ("report", "Report"),
        ("form", "Form"),
    ]

    title = models.CharField(max_length=160)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    storage_url = models.URLField(blank=True)
    summary = models.TextField(blank=True)
    is_sensitive = models.BooleanField(default=False)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class MLInsight(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("training", "Training"),
        ("ready", "Ready"),
    ]

    name = models.CharField(max_length=120)
    target = models.CharField(max_length=120)
    algorithm = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    score = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    generated_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self):
        return self.name
