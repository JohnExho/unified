from django.db import models


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
