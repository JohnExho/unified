from django.core.management.base import BaseCommand
from librarymanagement.services import TransactionServices


class Command(BaseCommand):
    help = "Check and update overdue transactions"

    def handle(self, *args, **options):
        self.stdout.write("Checking for overdue transactions...")

        updated_count = TransactionServices.check_and_update_overdue_transactions()

        self.stdout.write(
            self.style.SUCCESS(f"Successfully updated {updated_count} overdue transactions")
        )
