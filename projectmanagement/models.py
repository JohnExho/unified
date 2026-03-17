import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError

# ----------------------
# Teams
# ----------------------
class Team(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='teams')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

# ----------------------
# Projects
# ----------------------
class Project(models.Model):
    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('active', 'Active'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    RESEARCH_METHOD_CHOICES = [
        ('action_research', 'Action Research'),
        ('text_mining', 'Text Mining'),
        ('case_study', 'Case Study'),
        ('experimental', 'Experimental'),
        ('mixed_methods', 'Mixed Methods'),
        ('other', 'Other'),
    ]
    PUBLICATION_SCOPE_CHOICES = [
        ('local', 'Local'),
        ('international', 'International'),
    ]
    PUBLICATION_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('for_publication', 'For Publication'),
        ('published', 'Published'),
    ]
    SOURCE_TYPE_CHOICES = [
        ('student', 'Student'),
        ('faculty', 'Faculty'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='active')
    start_date = models.DateField()
    end_date = models.DateField()
    research_method = models.CharField(max_length=40, choices=RESEARCH_METHOD_CHOICES, default='action_research')
    publication_scope = models.CharField(max_length=20, choices=PUBLICATION_SCOPE_CHOICES, default='local')
    publication_status = models.CharField(max_length=30, choices=PUBLICATION_STATUS_CHOICES, default='draft')
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPE_CHOICES, default='student')
    repository_source = models.URLField(blank=True, null=True)
    auto_detected_topic = models.CharField(max_length=120, blank=True)
    text_mining_summary = models.TextField(blank=True)
    meta_tags = models.JSONField(default=list, blank=True)
    team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_projects')

    class Meta:
        permissions = [
            ("access_project_management_system", "Can access Research Management system"),
        ]

    def clean(self):
        # Validate that start_date is before end_date
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValidationError({
                    'start_date': f"Research start date ({self.start_date}) cannot be after end date ({self.end_date})."
                })

    def save(self, *args, **kwargs):
        # Ensure clean() runs on save
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

# ----------------------
# Tasks
# ----------------------
class Task(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    STATUS_CHOICES = [
        ('todo', 'To Do'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    
    # Support multiple assignees
    assigned_to = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        related_name='tasks', 
        blank=True
    )
    # Optional: assign to entire team
    assigned_team = models.ForeignKey(
        Team, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='tasks'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='todo')
    priority = models.PositiveSmallIntegerField(
        default=3,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(10),
        ],
    )
    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.project.name})"

    def clean(self):
        # Only validate if both dates are set
        if self.due_date and self.project.start_date:
            if self.due_date < self.project.start_date:
                raise ValidationError({
                    'due_date': f"Task due date ({self.due_date}) cannot be before research start date ({self.project.start_date})."
                })
        
        if self.due_date and self.project.end_date:
            if self.due_date > self.project.end_date:
                raise ValidationError({
                    'due_date': f"Task due date ({self.due_date}) cannot exceed research end date ({self.project.end_date})."
                })

    def save(self, *args, **kwargs):
        # Ensure clean() runs on save
        self.full_clean()
        super().save(*args, **kwargs)

# ----------------------
# Calendar Events
# ----------------------
class CalendarEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    related_task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True)
    related_project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.title

# ----------------------
# Notifications
# ----------------------
class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    related_task = models.ForeignKey(Task, on_delete=models.CASCADE, null=True, blank=True)
    related_project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"Notification to {self.recipient.username}"

# ----------------------
# Reports (JSON for ML later)
# ----------------------
class Report(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='reports')
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    data = models.JSONField()
    summary = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Report for {self.project.name} at {self.created_at}"


class MLInsight(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('training', 'Training'),
        ('ready', 'Ready'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    target = models.CharField(max_length=120)
    algorithm = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    score = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name
