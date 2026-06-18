from django.contrib import admin
from .models import (
    StudentProfile, Scholarship, Application, Evaluation,
    Document, Notification, ScholarshipOffer, RenewalApplication,
    RecommendationModel, RejectionAnalysis, AuditLog
)


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'school_university', 'gpa', 'stage_1_status', 'updated_at')
    list_filter = ('stage_1_status',)
    search_fields = ('user__username', 'full_name', 'school_university')


@admin.register(Scholarship)
class ScholarshipAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'scholarship_type', 'status', 'number_of_slots', 'award_amount', 'application_end_date')
    list_filter = ('category', 'scholarship_type', 'status', 'renewable')
    search_fields = ('name', 'description')


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('student', 'scholarship', 'status', 'submitted_at', 'created_at')
    list_filter = ('status',)
    search_fields = ('student__username', 'scholarship__name')


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('application', 'reviewer', 'status', 'total_score', 'recommendation', 'updated_at')
    list_filter = ('status', 'recommendation')
    search_fields = ('application__student__username', 'reviewer__username')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('user', 'document_type', 'verification_status', 'version', 'uploaded_at')
    list_filter = ('document_type', 'verification_status')
    search_fields = ('user__username',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'notification_type', 'title', 'read', 'created_at')
    list_filter = ('notification_type', 'read')
    search_fields = ('recipient__username', 'title')


@admin.register(ScholarshipOffer)
class ScholarshipOfferAdmin(admin.ModelAdmin):
    list_display = ('application', 'status', 'offer_amount', 'responded_at', 'created_at')
    list_filter = ('status',)
    search_fields = ('application__student__username',)


@admin.register(RenewalApplication)
class RenewalApplicationAdmin(admin.ModelAdmin):
    list_display = ('offer', 'renewal_year', 'status', 'submitted_at')
    list_filter = ('status',)


@admin.register(RecommendationModel)
class RecommendationModelAdmin(admin.ModelAdmin):
    list_display = ('student', 'scholarship', 'match_score', 'eligibility_probability', 'rank', 'created_at')
    list_filter = ()
    search_fields = ('student__full_name', 'scholarship__name')


@admin.register(RejectionAnalysis)
class RejectionAnalysisAdmin(admin.ModelAdmin):
    list_display = ('application', 'qualification_status', 'rejected_category', 'created_at')
    list_filter = ('qualification_status', 'rejected_category')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'target_model', 'target_id', 'created_at')
    list_filter = ('action', 'target_model')
    search_fields = ('user__username', 'description')
