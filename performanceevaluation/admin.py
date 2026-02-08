from django.contrib import admin
from .models import (
    AcademicTerm,
    EvaluationCycle,
    EvaluationCategory,
    EvaluationCriterion,
    Rubric,
    EvaluationForm,
    Evaluation,
    EvaluationScore,
    EvaluationComment,
    ComputedResult,
    Recommendation,
    Department,
    UserDepartmentAssignment
)

@admin.register(AcademicTerm)
class AcademicTermAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)

@admin.register(EvaluationCycle)
class EvaluationCycleAdmin(admin.ModelAdmin):
    list_display = ('name', 'term', 'start_date', 'end_date', 'is_closed')
    list_filter = ('term', 'is_closed')
    search_fields = ('name',)

@admin.register(EvaluationCategory)
class EvaluationCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'weight')
    search_fields = ('name',)

@admin.register(EvaluationCriterion)
class EvaluationCriterionAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'weight')
    list_filter = ('category',)
    search_fields = ('name',)


@admin.register(Rubric)
class RubricAdmin(admin.ModelAdmin):
    list_display = ('criterion', 'level')
    list_filter = ('criterion',)
    search_fields = ('criterion__name',)


@admin.register(EvaluationForm)
class EvaluationFormAdmin(admin.ModelAdmin):
    list_display = ('evaluator_type', 'cycle', 'is_active')
    list_filter = ('evaluator_type', 'cycle', 'is_active')

class EvaluationScoreInline(admin.TabularInline):
    model = EvaluationScore
    extra = 0

class EvaluationCommentInline(admin.StackedInline):
    model = EvaluationComment
    extra = 0

@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('evaluatee', 'evaluator', 'form', 'is_submitted', 'submitted_at')
    list_filter = ('is_submitted', 'form__cycle', 'form__evaluator_type')
    search_fields = ('evaluatee__username', 'evaluator__username')
    date_hierarchy = 'submitted_at'
    inlines = [EvaluationScoreInline, EvaluationCommentInline]

    readonly_fields = ('submitted_at',)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.is_submitted:
            return self.readonly_fields + ('is_submitted',)
        return self.readonly_fields

@admin.register(ComputedResult)
class ComputedResultAdmin(admin.ModelAdmin):
    list_display = ('evaluatee', 'cycle', 'total_score', 'performance_level', 'is_locked')
    list_filter = ('cycle', 'performance_level', 'is_locked')
    search_fields = ('evaluatee__username',)
    readonly_fields = ('computed_at',)

@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ('recommendation_type', 'result', 'created_at')
    list_filter = ('recommendation_type',)
    search_fields = ('description',)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    search_fields = ('name', 'code')

@admin.register(UserDepartmentAssignment)
class UserDepartmentAssignmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'department')
    search_fields = ('user__username', 'department__name')