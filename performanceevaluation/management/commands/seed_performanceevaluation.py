from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from core.models import SystemMembership

from performanceevaluation.models import (
    AcademicTerm,
    ComputedResult,
    Department,
    Evaluation,
    EvaluationCategory,
    EvaluationComment,
    EvaluationCriterion,
    EvaluationCycle,
    EvaluationForm,
    EvaluationScore,
    MLInsight,
    Recommendation,
    Rubric,
    UserDepartmentAssignment,
)


class Command(BaseCommand):
    help = "Seed Performance Evaluation with sample structure, scores, and recommendations."

    def _get_seed_users(self):
        user_model = get_user_model()
        users = list(user_model.objects.order_by("date_joined")[:2])
        if len(users) >= 2:
            return users[0], users[1]

        first = users[0] if users else user_model.objects.create_user(
            username="seed_user",
            email="seed_user@example.com",
            password="seed-password-123",
        )
        second = user_model.objects.filter(username="seed_reviewer").first()
        if not second:
            second = user_model.objects.create_user(
                username="seed_reviewer",
                email="seed_reviewer@example.com",
                password="seed-password-123",
            )
        return first, second

    @transaction.atomic
    def handle(self, *args, **options):
        evaluatee, evaluator = self._get_seed_users()
        today = timezone.localdate()

        Recommendation.objects.all().delete()
        ComputedResult.objects.all().delete()
        EvaluationComment.objects.all().delete()
        EvaluationScore.objects.all().delete()
        Evaluation.objects.all().delete()
        EvaluationForm.objects.all().delete()
        Rubric.objects.all().delete()
        EvaluationCriterion.objects.all().delete()
        EvaluationCategory.objects.all().delete()
        EvaluationCycle.objects.all().delete()
        AcademicTerm.objects.all().delete()
        UserDepartmentAssignment.objects.all().delete()
        Department.objects.all().delete()
        MLInsight.objects.all().delete()

        department = Department.objects.create(name="Computer Studies", code="CS", is_active=True)
        UserDepartmentAssignment.objects.create(user=evaluatee, department=department)
        UserDepartmentAssignment.objects.create(user=evaluator, department=department)

        SystemMembership.objects.update_or_create(
            user=evaluatee,
            system_name="performanceevaluation",
            defaults={"system_role": "admin" if evaluatee.is_superuser else "user"},
        )
        SystemMembership.objects.update_or_create(
            user=evaluator,
            system_name="performanceevaluation",
            defaults={"system_role": "user"},
        )

        term = AcademicTerm.objects.create(
            name="AY 2025-2026",
            start_date=today - timedelta(days=120),
            end_date=today + timedelta(days=120),
            is_active=True,
        )
        cycle = EvaluationCycle.objects.create(
            term=term,
            name="Midyear Evaluation",
            start_date=today - timedelta(days=15),
            end_date=today + timedelta(days=20),
            is_closed=False,
        )

        category_teaching = EvaluationCategory.objects.create(cycle=cycle, name="Teaching Effectiveness", weight=50)
        category_service = EvaluationCategory.objects.create(cycle=cycle, name="Service and Extension", weight=50)

        criterion_1 = EvaluationCriterion.objects.create(
            category=category_teaching,
            name="Instructional Delivery",
            description="Clarity and engagement during classes.",
            weight=30,
        )
        criterion_2 = EvaluationCriterion.objects.create(
            category=category_teaching,
            name="Assessment Quality",
            description="Validity and timeliness of assessment tools.",
            weight=20,
        )
        criterion_3 = EvaluationCriterion.objects.create(
            category=category_service,
            name="Community Involvement",
            description="Participation in extension activities.",
            weight=25,
        )
        criterion_4 = EvaluationCriterion.objects.create(
            category=category_service,
            name="Professional Development",
            description="Seminars, trainings, and certifications.",
            weight=25,
        )

        for criterion in [criterion_1, criterion_2, criterion_3, criterion_4]:
            for level in range(1, 6):
                Rubric.objects.create(
                    criterion=criterion,
                    level=level,
                    description=f"Level {level} benchmark for {criterion.name}.",
                )

        form = EvaluationForm.objects.create(cycle=cycle, evaluator_type="supervisor", is_active=True)
        EvaluationForm.objects.create(cycle=cycle, evaluator_type="self", is_active=True)

        evaluation = Evaluation.objects.create(
            form=form,
            evaluatee=evaluatee,
            evaluator=evaluator,
            submitted_at=timezone.now(),
            is_submitted=True,
        )

        EvaluationScore.objects.create(evaluation=evaluation, criterion=criterion_1, score=4)
        EvaluationScore.objects.create(evaluation=evaluation, criterion=criterion_2, score=5)
        EvaluationScore.objects.create(evaluation=evaluation, criterion=criterion_3, score=4)
        EvaluationScore.objects.create(evaluation=evaluation, criterion=criterion_4, score=5)

        EvaluationComment.objects.create(
            evaluation=evaluation,
            comment="Strong instructional performance with active community engagement.",
        )

        result = ComputedResult.objects.create(
            evaluatee=evaluatee,
            cycle=cycle,
            total_score=4.50,
            performance_level="Very Satisfactory",
            is_locked=False,
        )
        Recommendation.objects.create(
            result=result,
            recommendation_type="recognition",
            description="Nominate for college teaching excellence recognition.",
        )

        MLInsight.objects.create(
            name="Performance Risk Classifier",
            target="performance_level",
            algorithm="SVM",
            status="ready",
            score=0.903,
            notes="Seeded classification insight for Performance Evaluation ML Lab.",
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded Performance Evaluation with evaluation structures, scores, and recommendations."
            )
        )
