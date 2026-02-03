from django.core.management.base import BaseCommand
from librarymanagement.services import ReservationServices


class Command(BaseCommand):
    help = "Check and expire old reservations"

    def handle(self, *args, **options):
        self.stdout.write("Checking for expired reservations...")

        expired_count = ReservationServices.check_and_expire_reservations()

        self.stdout.write(
            self.style.SUCCESS(f"Successfully expired {expired_count} reservations")
        )
