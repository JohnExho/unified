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
            defaults={"system_role": "superadmin" if evaluatee.is_superuser else "user"},
        )
        SystemMembership.objects.update_or_create(
            user=evaluator,
            system_name="performanceevaluation",
            defaults={"system_role": "superadmin" if evaluator.is_superuser else "user"},
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

        # --- Kolehiyo ng Subic Faculty Peer Evaluation Instrument ---
        # Rating scale: 5=Excellent, 4=Very Good, 3=Good, 2=Fair, 1=Poor
        rubric_labels = {
            5: "Excellent",
            4: "Very Good",
            3: "Good",
            2: "Fair",
            1: "Poor",
        }

        categories_data = [
            {
                "name": "A. Classroom Management",
                "weight": 25,
                "criteria": [
                    "Regularly monitors class attendance",
                    "Starts and ends the class on time",
                    "Maintains proper discipline in the classroom",
                    "Commands students' respect without force",
                    "Handles cases of individual and group discipline appropriately",
                    "Returns examination papers properly checked",
                    "Gives fair treatment and grade to submitted examinations",
                    "Exercises self-control in various classroom situation and interaction with students",
                    "Plans in advanced the ways for dealing with potential problems and misbehavior",
                    "Establishes rules for respect of different points of view and decision",
                ],
            },
            {
                "name": "B. Mastery of Subject Matter",
                "weight": 25,
                "criteria": [
                    "Demonstrates in-depth knowledge of the subject matter",
                    "Comes to class completely prepared",
                    "Explains the lesson very well and very clear, making it understandable and realistic",
                    "Gives specific and concrete example to create meaningful experiences",
                    "Integrates values in subject matter and in teaching",
                    "Links concepts to real life situations or to local and national issues",
                    "Develops scientific attitudes such as objectivity, open mindedness, judgement, and originality",
                    "Keep abreast of new ideas and understanding in the field",
                    "Employs method and techniques that will show evidences of mastery of the subject matter",
                    "Guides daily learning and discussing problems and needs",
                ],
            },
            {
                "name": "C. Teaching Strategies",
                "weight": 25,
                "criteria": [
                    "Uses variety of techniques and strategies to encourage students' participation",
                    "Uses appropriate instructional materials to make teaching meaningful",
                    "Make the lesson interesting and pertinent",
                    "Uses methods suited to the needs and capabilities of students",
                    "Utilizes and presents proper teaching devices, equipment and materials",
                    "Give praise incentives and recognition for outstanding achievement of student",
                    "Develops the value of listening and skillful way of students' participation",
                    "Uses strategies to prepare and motivate students for the day activity",
                    "Uses varied evaluation measures",
                    "Exerts effort to provide student with first hand experiences like field trips, research work and doing community works",
                ],
            },
            {
                "name": "D. Communication Skills",
                "weight": 25,
                "criteria": [
                    "Speaks with a well-modulated voice",
                    "Uses correct grammar and observe proper pronunciation",
                    "Communicates ideas effectively",
                    "Has good command of the language instruction",
                    "Promotes a better medium of exchange of ideas and encourages respect for other members' point of view",
                    "Speaks and writes appropriate and acceptable",
                    "Emphasizes listening and reading improving or enhancing communication ability",
                    "Expresses himself in appropriate and acceptable word and sentences at all times",
                    "Realizes the meaning, value and relevance of communication in daily activities or routine",
                    "Keeps abreast with recent trends and issues in language development",
                ],
            },
        ]

        all_criteria = []
        for cat_data in categories_data:
            category = EvaluationCategory.objects.create(
                cycle=cycle,
                name=cat_data["name"],
                weight=cat_data["weight"],
            )
            criterion_weight = round(cat_data["weight"] / len(cat_data["criteria"]), 2)
            for item in cat_data["criteria"]:
                criterion = EvaluationCriterion.objects.create(
                    category=category,
                    name=item,
                    description="",
                    weight=criterion_weight,
                )
                for level, label in rubric_labels.items():
                    Rubric.objects.create(
                        criterion=criterion,
                        level=level,
                        description=label,
                    )
                all_criteria.append(criterion)

        form = EvaluationForm.objects.create(cycle=cycle, evaluator_type="peer", is_active=True)
        EvaluationForm.objects.create(cycle=cycle, evaluator_type="self", is_active=True)
        EvaluationForm.objects.create(cycle=cycle, evaluator_type="supervisor", is_active=True)

        evaluation = Evaluation.objects.create(
            form=form,
            evaluatee=evaluatee,
            evaluator=evaluator,
            submitted_at=timezone.now(),
            is_submitted=True,
        )

        sample_scores = [5, 4, 4, 5, 4, 3, 5, 4, 4, 5,
                         4, 5, 4, 4, 5, 4, 3, 4, 5, 4,
                         4, 5, 4, 4, 4, 5, 4, 4, 3, 5,
                         5, 4, 5, 4, 4, 4, 5, 4, 4, 4]
        for criterion, score in zip(all_criteria, sample_scores):
            EvaluationScore.objects.create(evaluation=evaluation, criterion=criterion, score=score)

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
