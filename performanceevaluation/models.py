from django.conf import settings
from django.db import models

class AcademicTerm(models.Model):
    name = models.CharField(max_length=100)  # e.g. AY 2025–2026
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class EvaluationCycle(models.Model):
    term = models.ForeignKey(AcademicTerm, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)  # e.g. Midyear, End-of-Term
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.term} - {self.name}"


class EvaluationCategory(models.Model):
    cycle = models.ForeignKey(EvaluationCycle, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    weight = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return self.name

class EvaluationCriterion(models.Model):
    category = models.ForeignKey(EvaluationCategory, on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return self.name

class Rubric(models.Model):
    criterion = models.ForeignKey(EvaluationCriterion, on_delete=models.CASCADE)
    level = models.PositiveSmallIntegerField()  # e.g. 1–5
    description = models.TextField()

    class Meta:
        unique_together = ('criterion', 'level')

    def __str__(self):
        return f"{self.criterion} - Level {self.level}"

class EvaluationForm(models.Model):
    cycle = models.ForeignKey(EvaluationCycle, on_delete=models.CASCADE)
    evaluator_type = models.CharField(
        max_length=30,
        choices=[
            ('self', 'Self'),
            ('peer', 'Peer'),
            ('student', 'Student'),
            ('supervisor', 'Supervisor'),
        ]
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.evaluator_type} - {self.cycle}"


class Evaluation(models.Model):
    form = models.ForeignKey(EvaluationForm, on_delete=models.CASCADE)
    evaluatee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='evaluations_received'
    )
    evaluator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='evaluations_given'
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    is_submitted = models.BooleanField(default=False)

    def __str__(self):
        return f"Evaluation for {self.evaluatee}"


class EvaluationScore(models.Model):
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE)
    criterion = models.ForeignKey(EvaluationCriterion, on_delete=models.CASCADE)
    score = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = ('evaluation', 'criterion')

class EvaluationComment(models.Model):
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE)
    comment = models.TextField()

    def __str__(self):
        return f"Comment for {self.evaluation}"


class ComputedResult(models.Model):
    evaluatee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    cycle = models.ForeignKey(EvaluationCycle, on_delete=models.CASCADE)
    total_score = models.DecimalField(max_digits=6, decimal_places=2)
    performance_level = models.CharField(max_length=50)
    computed_at = models.DateTimeField(auto_now_add=True)
    is_locked = models.BooleanField(default=False)

    class Meta:
        unique_together = ('evaluatee', 'cycle')


class Recommendation(models.Model):
    result = models.ForeignKey(ComputedResult, on_delete=models.CASCADE)
    recommendation_type = models.CharField(
        max_length=50,
        choices=[
            ('training', 'Training'),
            ('recognition', 'Recognition'),
            ('promotion', 'Promotion'),
            ('improvement', 'Improvement Plan'),
        ]
    )
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.recommendation_type


class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class Department(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class UserDepartmentAssignment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'department')