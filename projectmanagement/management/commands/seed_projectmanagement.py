from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from projectmanagement.models import (
    CalendarEvent,
    MLInsight,
    Notification,
    Project,
    Report,
    Task,
    Team,
)


class Command(BaseCommand):
    help = "Seed Research Management with sample teams, research, tasks, and insights."

    def _get_seed_user(self):
        user_model = get_user_model()
        user = user_model.objects.order_by("date_joined").first()
        if user:
            return user

        return user_model.objects.create_user(
            username="seed_user",
            email="seed_user@example.com",
            password="seed-password-123",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        user = self._get_seed_user()
        today = timezone.localdate()

        Notification.objects.all().delete()
        CalendarEvent.objects.all().delete()
        Report.objects.all().delete()
        Task.objects.all().delete()
        Project.objects.all().delete()
        Team.objects.all().delete()
        MLInsight.objects.all().delete()

        methods = ["text_mining", "action_research", "case_study"]
        scopes = ["international", "local", "local"]
        statuses = ["for_publication", "draft", "published"]
        sources = ["faculty", "student", "faculty"]

        team_a = Team.objects.create(name="Research Analytics Team")
        team_b = Team.objects.create(name="Publication and Ethics Team")
        team_a.members.add(user)
        team_b.members.add(user)

        projects = []
        for i, title in enumerate(
            [
                "AI-assisted Student Retention Analysis",
                "Community Reading Comprehension Study",
                "Faculty Publication Productivity Mapping",
            ]
        ):
            start_date = today - timedelta(days=10 * (i + 1))
            end_date = today + timedelta(days=30 * (i + 1))
            project = Project.objects.create(
                name=title,
                description="Seeded research record for dashboard and reports.",
                status="active" if i < 2 else "completed",
                start_date=start_date,
                end_date=end_date,
                research_method=methods[i],
                publication_scope=scopes[i],
                publication_status=statuses[i],
                source_type=sources[i],
                repository_source="https://repository.example.edu/research/seed",
                auto_detected_topic="Educational Analytics",
                text_mining_summary="Seeded NLP summary generated for testing.",
                meta_tags=["research", "seed", "analytics"],
                team=team_a if i % 2 == 0 else team_b,
                created_by=user,
            )
            projects.append(project)

        for project in projects:
            for index, task_title in enumerate(["Data Collection", "Analysis", "Write-up"], start=1):
                task = Task.objects.create(
                    project=project,
                    title=f"{task_title} - {project.name[:24]}",
                    description="Seeded task for workflow testing.",
                    status="completed" if index == 1 else "in_progress",
                    priority=min(10, 2 + index),
                    due_date=min(project.end_date, today + timedelta(days=index * 7)),
                    assigned_team=project.team,
                )
                task.assigned_to.add(user)

        CalendarEvent.objects.create(
            title="Seeded Research Review Meeting",
            description="Auto-generated event from seed command.",
            start_time=timezone.now() + timedelta(days=2),
            end_time=timezone.now() + timedelta(days=2, hours=1),
            related_project=projects[0],
        )

        Report.objects.create(
            project=projects[0],
            generated_by=user,
            data={"completion_rate": 66, "seeded": True},
            summary="Seeded report entry for Research Management.",
        )

        Notification.objects.create(
            recipient=user,
            message="Seed data loaded for Research Management.",
            related_project=projects[0],
        )

        MLInsight.objects.create(
            name="Research Classification v1",
            target="publication_status",
            algorithm="LogisticRegression",
            status="ready",
            score=0.912,
            notes="Seeded ML insight for admin ML Lab.",
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded Research Management with 2 teams, 3 research items, 9 tasks, and support records."
            )
        )
