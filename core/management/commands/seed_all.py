from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run all 6 seeders in one go."

    SEEDERS = [
        "seed_ces",
        "seed_informationmanagement",
        "seed_inventorymanagement",
        "seed_librarymanagement",
        "seed_performanceevaluation",
        "seed_projectmanagement",
    ]

    def handle(self, *args, **options):
        for seeder in self.SEEDERS:
            self.stdout.write(f"Running {seeder}...")
            try:
                call_command(seeder, stdout=self.stdout, stderr=self.stderr)
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  {seeder} failed: {e}"))
                continue
            self.stdout.write(self.style.SUCCESS(f"  {seeder} done."))

        self.stdout.write(self.style.SUCCESS("All seeders finished."))
