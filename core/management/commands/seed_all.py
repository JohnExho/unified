from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Run all 7 seeders in one go."

    SYSTEM_CHOICES = [
        ('core', 'Core'),
        ('researchmanagement', 'Research Management'),
        ('librarymanagement', 'Library Management'),
        ('inventorymanagement', 'Inventory Management'),
        ('communityextensionservices', 'Community Extension Services'),
        ('informationmanagement', 'Information Management'),
        ('performanceevaluation', 'Performance Evaluation'),
        ('scholarshipmanagement', 'Scholarship Management'),
    ]

    SEEDERS = [
        "seed_ces",
        "seed_informationmanagement",
        "seed_inventorymanagement",
        "seed_librarymanagement",
        "seed_performanceevaluation",
        "seed_projectmanagement",
        "seed_scholarshipmanagement",
    ]

    def _get_seed_user(self):
        User = get_user_model()

        user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@example.com",
                "is_staff": True,
                "is_superuser": True,
            }
        )

        if created:
            user.set_password("password")
            user.save()
            self.stdout.write(
                self.style.SUCCESS("Superuser 'admin' created.")
            )
        else:
            self.stdout.write(
                "Superuser 'admin' already exists, skipping."
            )

        return user

    def _create_multiple_users(self):
        User = get_user_model()

        users_data = [
            {
                "username": "ResearchManager",
                "email": "researchmanager@example.com",
                "password": "RMCIRCA2026",
                "system": "researchmanagement",
            },
            {
                "username": "LibraryAdmin",
                "email": "libraryadmin@example.com",
                "password": "LA2390067",
                "system": "librarymanagement",
            },
            {
                "username": "InventoryCustodian",
                "email": "inventorycustodian@example.com",
                "password": "IV7M2K9A",
                "system": "inventorymanagement",
            },
            {
                "username": "FlowSupervisor",
                "email": "flowsupervisor@example.com",
                "password": "IN46PQ8R",
                "system": "informationmanagement",
            },
            {
                "username": "MetricsEvaluationLead",
                "email": "metricsevaluationlead@example.com",
                "password": "PE9X41LT",
                "system": "performanceevaluation",
            },
            {
                "username": "ExtensionSupportOfficer",
                "email": "extensionsupportofficer@example.com",
                "password": "CX52RD0E",
                "system": "communityextensionservices",
            },
            {
                "username": "ScholarshipOfficer",
                "email": "scholarshipofficer@example.com",
                "password": "SM8KZ3WQ",
                "system": "scholarshipmanagement",
            },
        ]

        users = []

        for data in users_data:
            user, created = User.objects.get_or_create(
                username=data["username"],
                defaults={
                    "email": data["email"]
                }
            )

            if created:
                user.set_password(data["password"])
                user.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"User '{user.username}' created."
                    )
                )
            else:
                self.stdout.write(
                    f"User '{user.username}' already exists, skipping."
                )

            users.append({
                "user": user,
                "system": data["system"]
            })

        return users

    def _assign_multiple_system_roles(self, users):
        from core.models import SystemMembership

        for item in users:
            membership, created = SystemMembership.objects.get_or_create(
                user=item["user"],
                system_name=item["system"],
                defaults={
                    "system_role": "superadmin"
                }
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Assigned {item['system']} to {item['user'].username}"
                    )
                )

    def _assign_all_system_roles(self, user):
        from core.models import SystemMembership

        for code, label in self.SYSTEM_CHOICES:
            membership, created = SystemMembership.objects.get_or_create(
                user=user,
                system_name=code,
                defaults={
                    "system_role": "superadmin"
                }
            )

            if created:
                self.stdout.write(
                    f"Assigned role: {label}"
                )

    def handle(self, *args, **options):
        # Create admin user
        self.stdout.write("Creating seed superuser...")
        admin_user = self._get_seed_user()

        # Give admin access to all systems
        self.stdout.write("Assigning admin system roles...")
        self._assign_all_system_roles(admin_user)

        # Create system-specific users
        self.stdout.write("Creating additional users...")
        users = self._create_multiple_users()

        # Give each user only one matching system
        self.stdout.write("Assigning user system roles...")
        self._assign_multiple_system_roles(users)

        # Run seeders
        for seeder in self.SEEDERS:
            self.stdout.write(f"Running {seeder}...")

            try:
                call_command(
                    seeder,
                    stdout=self.stdout,
                    stderr=self.stderr
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"{seeder} done."
                    )
                )

            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(
                        f"{seeder} failed: {e}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                "All seeders finished."
            )
        )