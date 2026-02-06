from django.core.management.base import BaseCommand
from librarymanagement.services import UserActivityServices


class Command(BaseCommand):
    help = "Clean up old user activity logs"

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Delete activities older than this many days',
        )

    def handle(self, *args, **options):
        days = options['days']
        self.stdout.write(f"Deleting activities older than {days} days...")

        deleted_count = UserActivityServices.delete_old_activities(days)

        self.stdout.write(
            self.style.SUCCESS(f"Successfully deleted {deleted_count} old activity records")
        )
