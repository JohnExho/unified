from django.core.management.base import BaseCommand
from librarymanagement.services import NotificationServices


class Command(BaseCommand):
    help = "Send due soon notifications to users"

    def handle(self, *args, **options):
        self.stdout.write("Sending due soon notifications...")

        count = NotificationServices.send_due_soon_notifications()

        self.stdout.write(
            self.style.SUCCESS(f"Successfully sent {count} due soon notifications")
        )
