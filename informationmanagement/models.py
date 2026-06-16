from django.db import models
from django.conf import settings
from django.utils import timezone


class Information(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        permissions = [
            (
                "access_information_management_system",
                "Can access Information Management system",
            ),
        ]

    def __str__(self):
        return self.name


class Project(models.Model):
    CATEGORY_CHOICES = [
        ("Education", "Education"),
        ("Health", "Health"),
        ("Livelihood", "Livelihood"),
        ("Environment", "Environment"),
        ("Governance", "Governance"),
    ]
    STATUS_CHOICES = [
        ("Proposed", "Proposed"),
        ("Ongoing", "Ongoing"),
        ("Completed", "Completed"),
    ]

    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    lead = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    beneficiaries_count = models.PositiveIntegerField(default=0)
    progress = models.PositiveIntegerField(default=0)
    predicted_success = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    predicted_reach = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return self.name


class BeneficiaryGroup(models.Model):
    PRIORITY_CHOICES = [
        ("High", "High"),
        ("Medium", "Medium"),
        ("Low", "Low"),
    ]

    name = models.CharField(max_length=200)
    segment = models.CharField(max_length=120)
    households = models.PositiveIntegerField(default=0)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Partner(models.Model):
    TYPE_CHOICES = [
        ("Government", "Government"),
        ("NGO", "NGO"),
        ("Private", "Private"),
        ("Academe", "Academe"),
    ]
    STATUS_CHOICES = [
        ("Active", "Active"),
        ("Prospecting", "Prospecting"),
        ("Dormant", "Dormant"),
    ]
    ENGAGEMENT_CHOICES = [
        ("High", "High"),
        ("Medium", "Medium"),
        ("Low", "Low"),
    ]

    name = models.CharField(max_length=200)
    partner_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    engagement = models.CharField(max_length=20, choices=ENGAGEMENT_CHOICES)
    contribution = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=120, blank=True)

    def __str__(self):
        return self.name


class Activity(models.Model):
    STATUS_CHOICES = [
        ("Scheduled", "Scheduled"),
        ("Completed", "Completed"),
        ("In Progress", "In Progress"),
        ("Cancelled", "Cancelled"),
    ]

    title = models.CharField(max_length=200)
    date = models.DateField()
    location = models.CharField(max_length=200)
    owner = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    participants = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title


class Report(models.Model):
    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("In Review", "In Review"),
        ("Generated", "Generated"),
    ]

    title = models.CharField(max_length=200)
    period = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    owner = models.CharField(max_length=120)

    def __str__(self):
        return f"{self.title} ({self.period})"


class ReportTemplate(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class MLModel(models.Model):
    STATUS_CHOICES = [
        ("Prototype", "Prototype"),
        ("Training", "Training"),
        ("Ready", "Ready"),
    ]

    name = models.CharField(max_length=200)
    model_type = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    metric = models.CharField(max_length=80)

    def __str__(self):
        return self.name


class MLPipeline(models.Model):
    STATUS_CHOICES = [
        ("Planned", "Planned"),
        ("Design", "Design"),
        ("Operational", "Operational"),
    ]

    name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)

    def __str__(self):
        return self.name


class MLExperiment(models.Model):
    STATUS_CHOICES = [
        ("Running", "Running"),
        ("Completed", "Completed"),
        ("Queued", "Queued"),
    ]

    name = models.CharField(max_length=200)
    owner = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


# ============================================================================
# Feature 1: Contribution Allocation Management Models
# ============================================================================


class ContributionFund(models.Model):
    """Represents a fund or project that receives allocated contributions"""
    
    STATUS_CHOICES = [
        ("active", "Active"),
        ("completed", "Completed"),
        ("on_hold", "On Hold"),
    ]

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="contribution_funds", null=True, blank=True
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    budget_required = models.DecimalField(max_digits=15, decimal_places=2)
    start_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def get_total_allocated(self):
        """Calculate total allocated amount to this fund"""
        from django.db.models import Sum
        total = FundAllocation.objects.filter(fund=self).aggregate(
            total=Sum("amount")
        )["total"]
        return total or 0

    def get_total_used(self):
        """Calculate total used amount from expenses"""
        from django.db.models import Sum
        total = FundExpense.objects.filter(fund=self).aggregate(
            total=Sum("amount")
        )["total"]
        return total or 0

    def get_remaining_balance(self):
        """Calculate remaining balance"""
        return self.get_total_allocated() - self.get_total_used()


class FundAllocation(models.Model):
    """Track allocation of contributions to funds"""
    
    fund = models.ForeignKey(
        ContributionFund, on_delete=models.CASCADE, related_name="allocations"
    )
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    allocated_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)
    allocated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-allocated_date"]

    def __str__(self):
        return f"{self.fund} - ${self.amount}"


class FundExpense(models.Model):
    """Track expenses from allocated fund resources"""
    
    CATEGORY_CHOICES = [
        ("equipment", "Equipment"),
        ("services", "Services"),
        ("personnel", "Personnel"),
        ("materials", "Materials"),
        ("travel", "Travel"),
        ("other", "Other"),
    ]

    fund = models.ForeignKey(
        ContributionFund, on_delete=models.CASCADE, related_name="expenses"
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    expense_date = models.DateField()
    reference_no = models.CharField(max_length=80, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-expense_date"]

    def __str__(self):
        return f"{self.fund} - {self.description}"


# ============================================================================
# Feature 3: Member Contribution Monitoring Models
# ============================================================================


class MemberContributionRecord(models.Model):
    """Track member contributions with status and payment information"""
    
    PAYMENT_STATUS_CHOICES = [
        ("on_time", "On Time"),
        ("overdue", "Overdue"),
        ("delinquent", "Delinquent"),
    ]

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="member_contributions", null=True, blank=True
    )
    member_name = models.CharField(max_length=200)
    employee_id = models.CharField(max_length=100, unique=True)
    department = models.ForeignKey(
        "MasterDataDepartment", on_delete=models.SET_NULL, null=True, blank=True, related_name="member_records"
    )
    total_contributions = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    due_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    late_payment_penalties = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default="on_time"
    )
    last_payment_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        unique_together = ("member_name", "employee_id")

    def __str__(self):
        return f"{self.member_name} ({self.employee_id})"


class MasterDataDepartment(models.Model):
    """Configurable master data for departments"""
    
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
