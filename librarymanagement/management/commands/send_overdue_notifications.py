from django.core.management.base import BaseCommand
from librarymanagement.services import NotificationServices


class Command(BaseCommand):
    help = "Send overdue notifications to users"

    def handle(self, *args, **options):
        self.stdout.write("Sending overdue notifications...")

        count = NotificationServices.send_overdue_notifications()

        self.stdout.write(
            self.style.SUCCESS(f"Successfully sent {count} overdue notifications")
        )
