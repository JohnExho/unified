from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import SystemMembership
from .models import (
    AcademicTerm,
    Department,
    Evaluation,
    UserDepartmentAssignment,
    EvaluationCategory,
    EvaluationCriterion,
    EvaluationCycle,
    EvaluationForm,
)


class StudentEvaluationSelectionTests(TestCase):
    def setUp(self):
        self.student = get_user_model().objects.create_user(
            username="student1",
            email="student1@example.com",
            password="password123",
        )
        self.teacher = get_user_model().objects.create_user(
            username="teacher1",
            email="teacher1@example.com",
            password="password123",
        )

        self.department = Department.objects.create(name="Education", code="EDU")
        UserDepartmentAssignment.objects.create(user=self.student, department=self.department)
        UserDepartmentAssignment.objects.create(user=self.teacher, department=self.department)

        SystemMembership.objects.create(user=self.student, system_name="performanceevaluation", system_role="user")
        SystemMembership.objects.create(user=self.teacher, system_name="performanceevaluation", system_role="instructor")

        self.term = AcademicTerm.objects.create(
            name="AY 2026-2027",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 12, 31),
            is_active=True,
        )
        self.cycle = EvaluationCycle.objects.create(
            term=self.term,
            name="Midterm",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 8, 31),
            is_closed=False,
        )
        self.form = EvaluationForm.objects.create(
            cycle=self.cycle,
            evaluator_type="student",
            is_active=True,
        )
        self.category = EvaluationCategory.objects.create(
            cycle=self.cycle,
            name="Teaching Skills",
            weight="20.00",
        )
        self.criterion = EvaluationCriterion.objects.create(
            category=self.category,
            name="Preparedness",
            description="Preparedness",
            weight="10.00",
        )
        self.teacher_subject = self.teacher

    def test_student_can_select_teacher_and_subject_for_evaluation(self):
        self.client.login(username="student1", password="password123")

        response = self.client.get(
            reverse("performanceevaluation:user_evaluation_form", args=[self.form.id]),
            {"teacher": self.teacher.id, "subject": "English 101"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "English 101")

        post_response = self.client.post(
            reverse("performanceevaluation:user_evaluation_form", args=[self.form.id]),
            {
                "teacher": self.teacher.id,
                "subject": "English 101",
                "criterion_{}".format(self.criterion.id): "5",
                "overall_comment": "Great teaching",
            },
        )

        self.assertRedirects(post_response, reverse("performanceevaluation:user_evaluations"))
        evaluation = Evaluation.objects.get(evaluatee=self.teacher, evaluator=self.student)
        self.assertEqual(evaluation.subject_name, "English 101")
