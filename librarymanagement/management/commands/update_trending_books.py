from django.core.management.base import BaseCommand
from librarymanagement.services import DataMiningServices


class Command(BaseCommand):
    help = "Update trending books metrics"

    def add_arguments(self, parser):
        parser.add_argument(
            '--period',
            type=str,
            default='weekly',
            choices=['daily', 'weekly', 'monthly', 'yearly'],
            help='Period type for trending analysis',
        )

    def handle(self, *args, **options):
        period_type = options['period']
        self.stdout.write(f"Updating trending books for {period_type} period...")

        count = DataMiningServices.analyze_trending_books(period_type)

        self.stdout.write(
            self.style.SUCCESS(f"Successfully updated {count} trending book records")
        )
