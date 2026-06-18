import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


# ----------------------
# Student Profile (Stage 1)
# ----------------------
class StudentProfile(models.Model):
    STAGE_STATUS_CHOICES = [
        ('incomplete', 'Incomplete'),
        ('complete', 'Complete'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='scholarship_profile'
    )

    # Stage tracking
    stage_1_status = models.CharField(max_length=20, choices=STAGE_STATUS_CHOICES, default='incomplete')
    stage_1_completed_at = models.DateTimeField(null=True, blank=True)

    # Biodata
    full_name = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True)
    contact_number = models.CharField(max_length=20, blank=True)
    family_background = models.TextField(blank=True)

    # Academic Data
    school_university = models.CharField(max_length=255, blank=True)
    course_strand = models.CharField(max_length=255, blank=True)
    gpa = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(4.0)]
    )
    academic_awards = models.TextField(blank=True)

    # Financial Data
    annual_family_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    financial_need_score = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )

    # Location
    province = models.CharField(max_length=100, blank=True)
    location_coords = models.CharField(max_length=100, blank=True)

    # Validation flags
    all_required_fields_filled = models.BooleanField(default=False)
    all_required_documents_uploaded = models.BooleanField(default=False)
    validation_checks_passed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [
            ("access_scholarship_management_system", "Can access Scholarship Management system"),
            ("view_student_dashboard", "Can view student dashboard"),
            ("manage_scholarship_applications", "Can manage scholarship applications"),
        ]

    @property
    def is_stage_1_complete(self):
        return self.stage_1_status == 'complete'

    def check_and_update_stage_1(self):
        """Validate Stage 1 completion criteria and update status."""
        required_fields_ok = all([
            self.full_name,
            self.address,
            self.contact_number,
            self.school_university,
            self.course_strand,
            self.gpa is not None,
            self.annual_family_income is not None,
            self.province,
        ])
        docs_ok = self.all_required_documents_uploaded
        self.all_required_fields_filled = required_fields_ok
        self.validation_checks_passed = required_fields_ok and docs_ok

        if required_fields_ok and docs_ok and self.stage_1_status == 'incomplete':
            self.stage_1_status = 'complete'
            self.stage_1_completed_at = timezone.now()
        elif not (required_fields_ok and docs_ok):
            self.stage_1_status = 'incomplete'
            self.stage_1_completed_at = None

        self.save(update_fields=[
            'all_required_fields_filled',
            'all_required_documents_uploaded',
            'validation_checks_passed',
            'stage_1_status',
            'stage_1_completed_at',
        ])

    def __str__(self):
        return f"Profile: {self.full_name or self.user.username}"


# ----------------------
# Documents
# ----------------------
class Document(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ('government_id', 'Government-Issued ID'),
        ('transcript', 'Transcript / Report Card'),
        ('income_proof', 'Income Proof'),
        ('recommendation_letter', 'Recommendation Letter'),
        ('other', 'Other'),
    ]
    VERIFICATION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='scholarship_documents'
    )
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPE_CHOICES)
    file = models.FileField(upload_to='scholarship_documents/%Y/%m/%d/')
    original_filename = models.CharField(max_length=255, blank=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VERIFICATION_STATUS_CHOICES,
        default='pending'
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='verified_documents'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    version = models.PositiveIntegerField(default=1)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.get_document_type_display()} - {self.user.username} (v{self.version})"


# ----------------------
# Scholarships
# ----------------------
class Scholarship(models.Model):
    CATEGORY_CHOICES = [
        ('merit_based', 'Merit-Based'),
        ('need_based', 'Need-Based'),
        ('talent_based', 'Talent-Based'),
    ]
    TYPE_CHOICES = [
        ('government', 'Government'),
        ('private', 'Private'),
        ('corporate', 'Corporate'),
        ('organization', 'Organization'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('closed', 'Closed'),
        ('archived', 'Archived'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    scholarship_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    award_amount = models.DecimalField(max_digits=12, decimal_places=2)
    number_of_slots = models.PositiveIntegerField()
    renewable = models.BooleanField(default=False)

    # JSON rule engine for eligibility
    eligibility_rules = models.JSONField(default=dict, blank=True)
    required_documents = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of required document types: ['government_id', 'transcript', 'income_proof']"
    )

    # Dates
    application_start_date = models.DateTimeField()
    application_end_date = models.DateTimeField()
    decision_announcement_date = models.DateField(null=True, blank=True)

    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='managed_scholarships'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_scholarships'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_accepting_applications(self):
        now = timezone.now()
        return (
            self.status == 'published'
            and self.application_start_date <= now <= self.application_end_date
        )

    @property
    def accepted_count(self):
        return self.applications.filter(status='accepted').count()

    @property
    def slots_remaining(self):
        return max(0, self.number_of_slots - self.accepted_count)

    def __str__(self):
        return self.name


# ----------------------
# Applications
# ----------------------
class Application(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('waitlisted', 'Waitlisted'),
        ('offer_accepted', 'Offer Accepted'),
        ('offer_declined', 'Offer Declined'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='scholarship_applications'
    )
    scholarship = models.ForeignKey(
        Scholarship,
        on_delete=models.CASCADE,
        related_name='applications'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    motivation_essay = models.TextField(blank=True)
    achievements = models.TextField(blank=True)
    additional_info = models.JSONField(default=dict, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'scholarship')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.student.username} → {self.scholarship.name} [{self.status}]"


# ----------------------
# Evaluations
# ----------------------
class Evaluation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]
    RECOMMENDATION_CHOICES = [
        ('accept', 'Accept'),
        ('reject', 'Reject'),
        ('waitlist', 'Waitlist'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name='evaluation'
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='evaluations_conducted'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Weighted rubric scores (0–100 each)
    academic_score = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text='Academic performance (0-100)'
    )
    financial_need_score = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text='Financial need assessment (0-100)'
    )
    interview_score = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text='Interview score (0-100)'
    )
    extracurricular_score = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text='Extracurricular activities (0-100)'
    )
    total_score = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )

    recommendation = models.CharField(
        max_length=20,
        choices=RECOMMENDATION_CHOICES,
        null=True, blank=True
    )
    reviewer_comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def compute_total_score(self):
        """Compute weighted total: Academic 40%, Financial 30%, Interview 20%, Extracurricular 10%."""
        weights = {
            'academic': 0.40,
            'financial': 0.30,
            'interview': 0.20,
            'extracurricular': 0.10,
        }
        scores = {
            'academic': self.academic_score,
            'financial': self.financial_need_score,
            'interview': self.interview_score,
            'extracurricular': self.extracurricular_score,
        }
        total_weight = sum(w for k, w in weights.items() if scores[k] is not None)
        if total_weight == 0:
            return None
        weighted_sum = sum(
            scores[k] * w for k, w in weights.items() if scores[k] is not None
        )
        return round(weighted_sum / total_weight, 2)

    def save(self, *args, **kwargs):
        self.total_score = self.compute_total_score()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Evaluation for {self.application}"


# ----------------------
# Scholarship Offer
# ----------------------
class ScholarshipOffer(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending Student Response'),
        ('accepted', 'Accepted by Student'),
        ('declined', 'Declined by Student'),
        ('revoked', 'Revoked'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name='offer'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    offer_amount = models.DecimalField(max_digits=12, decimal_places=2)
    offer_letter = models.FileField(upload_to='scholarship_offers/%Y/%m/%d/', null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    response_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Offer: {self.application.student.username} | {self.status}"


# ----------------------
# Renewal Application
# ----------------------
class RenewalApplication(models.Model):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('conditional', 'Conditional'),
        ('terminated', 'Terminated'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    offer = models.ForeignKey(
        ScholarshipOffer,
        on_delete=models.CASCADE,
        related_name='renewals'
    )
    renewal_year = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    updated_grades = models.FileField(upload_to='renewal_documents/%Y/%m/%d/', null=True, blank=True)
    progress_report = models.TextField(blank=True)
    behavioral_evaluation = models.TextField(blank=True)
    reviewer_notes = models.TextField(blank=True)
    renewal_decision_date = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Renewal Year {self.renewal_year}: {self.offer}"


# ----------------------
# Notifications
# ----------------------
class Notification(models.Model):
    TYPE_CHOICES = [
        ('stage_unlocked', 'Stage Unlocked'),
        ('application_status', 'Application Status Update'),
        ('decision_released', 'Decision Released'),
        ('deadline_reminder', 'Deadline Reminder'),
        ('document_verified', 'Document Verified'),
        ('offer_received', 'Scholarship Offer'),
        ('system_update', 'System Update'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='scholarship_notifications'
    )
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    related_scholarship = models.ForeignKey(
        Scholarship,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='notifications'
    )
    related_application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='notifications'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.notification_type}] → {self.recipient.username}"


# ----------------------
# ML: Recommendation
# ----------------------
class RecommendationModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='recommendations'
    )
    scholarship = models.ForeignKey(
        Scholarship,
        on_delete=models.CASCADE,
        related_name='student_recommendations'
    )
    match_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )
    eligibility_probability = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    success_probability = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    reason_tags = models.JSONField(default=list)
    explanation = models.TextField(blank=True)
    rank = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'scholarship')
        ordering = ['-match_score']

    def __str__(self):
        return f"Rec: {self.student} → {self.scholarship} ({self.match_score:.1f}%)"


# ----------------------
# ML: Rejection Analysis
# ----------------------
class RejectionAnalysis(models.Model):
    CATEGORY_CHOICES = [
        ('academic', 'Academic'),
        ('financial', 'Financial'),
        ('document', 'Document'),
        ('quota', 'Quota'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.OneToOneField(
        Application,
        on_delete=models.CASCADE,
        related_name='rejection_analysis'
    )
    qualification_status = models.BooleanField(default=False)
    rejected_category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    failed_criteria = models.JSONField(default=list)
    recommendations = models.JSONField(default=list)
    analysis_summary = models.TextField(blank=True)
    improvement_suggestions = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rejection Analysis: {self.application}"


# ----------------------
# Audit Log
# ----------------------
class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('review', 'Review'),
        ('decide', 'Decision'),
        ('contact', 'Contact'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    target_model = models.CharField(max_length=50)
    target_id = models.UUIDField()
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} | {self.action} | {self.target_model} | {self.created_at}"
