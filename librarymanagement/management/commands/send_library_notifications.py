"""
Management command to send automated library notifications
Run this command daily via cron or task scheduler
Usage: python manage.py send_library_notifications
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from librarymanagement.models import BorrowingTransaction, Reservation, Notification
from librarymanagement.services import NotificationServices


class Command(BaseCommand):
    help = "Send automated library notifications for due dates, overdue items, and reservations"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run without actually sending notifications",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "Running in DRY RUN mode - no notifications will be sent"
                )
            )

        # Send due soon notifications (books due in 2 days)
        due_soon_count = self.send_due_soon_notifications(dry_run)

        # Send overdue notifications
        overdue_count = self.send_overdue_notifications(dry_run)

        # Send reservation ready notifications
        reservation_count = self.send_reservation_notifications(dry_run)

        # Send reservation expiring notifications
        expiring_count = self.send_reservation_expiring_notifications(dry_run)

        # Update overdue status
        updated_count = self.update_overdue_status(dry_run)

        # Summary
        self.stdout.write(self.style.SUCCESS("\n=== Notification Summary ==="))
        self.stdout.write(f"Due soon notifications: {due_soon_count}")
        self.stdout.write(f"Overdue notifications: {overdue_count}")
        self.stdout.write(f"Reservation ready notifications: {reservation_count}")
        self.stdout.write(f"Reservation expiring notifications: {expiring_count}")
        self.stdout.write(f"Transactions marked overdue: {updated_count}")

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN - No actual changes made"))
        else:
            self.stdout.write(self.style.SUCCESS("\nNotifications sent successfully!"))

    def send_due_soon_notifications(self, dry_run=False):
        """Send notifications for books due in 2 days"""
        two_days_from_now = timezone.now() + timedelta(days=2)

        # Get active transactions due in 2 days
        due_soon = BorrowingTransaction.objects.filter(
            status="active", due_date__date=two_days_from_now.date()
        ).select_related("user", "book")

        count = 0
        for transaction in due_soon:
            # Check if notification already sent
            existing = Notification.objects.filter(
                user=transaction.user,
                related_transaction=transaction,
                notification_type="due_soon",
                created_at__date=timezone.now().date(),
            ).exists()

            if not existing:
                if not dry_run:
                    NotificationServices.create_due_soon_notification(transaction)
                count += 1
                self.stdout.write(
                    f"Due soon: {transaction.user.username} - {transaction.book.title}"
                )

        return count

    def send_overdue_notifications(self, dry_run=False):
        """Send notifications for overdue books"""
        overdue_transactions = BorrowingTransaction.objects.filter(
            status="overdue"
        ).select_related("user", "book")

        count = 0
        for transaction in overdue_transactions:
            # Send daily reminder
            if not dry_run:
                NotificationServices.create_overdue_notification(transaction)
            count += 1
            self.stdout.write(
                self.style.WARNING(
                    f"Overdue: {transaction.user.username} - {transaction.book.title} ({transaction.days_overdue} days)"
                )
            )

        return count

    def send_reservation_notifications(self, dry_run=False):
        """Send notifications for ready reservations that haven't been notified"""
        ready_reservations = Reservation.objects.filter(
            status="ready", notified=False
        ).select_related("user", "book")

        count = 0
        for reservation in ready_reservations:
            if not dry_run:
                NotificationServices.create_reservation_ready_notification(reservation)
                reservation.notified = True
                reservation.notified_at = timezone.now()
                reservation.save()
            count += 1
            self.stdout.write(
                f"Reservation ready: {reservation.user.username} - {reservation.book.title}"
            )

        return count

    def send_reservation_expiring_notifications(self, dry_run=False):
        """Send notifications for reservations expiring soon"""
        tomorrow = timezone.now() + timedelta(days=1)

        expiring_soon = Reservation.objects.filter(
            status="ready", expiry_date__date=tomorrow.date()
        ).select_related("user", "book")

        count = 0
        for reservation in expiring_soon:
            # Check if notification already sent
            existing = Notification.objects.filter(
                user=reservation.user,
                related_reservation=reservation,
                notification_type="reservation_expiring",
                created_at__date=timezone.now().date(),
            ).exists()

            if not existing:
                if not dry_run:
                    NotificationServices.create_reservation_expiring_notification(
                        reservation
                    )
                count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"Reservation expiring: {reservation.user.username} - {reservation.book.title}"
                    )
                )

        return count

    def update_overdue_status(self, dry_run=False):
        """Update transaction status to overdue if past due date"""
        now = timezone.now()

        # Find active transactions that are past due
        past_due = BorrowingTransaction.objects.filter(
            status="active", due_date__lt=now
        )

        count = past_due.count()

        if not dry_run:
            for transaction in past_due:
                transaction.status = "overdue"
                # Calculate days overdue
                delta = now - transaction.due_date
                transaction.days_overdue = delta.days
                transaction.save()

                self.stdout.write(
                    self.style.WARNING(
                        f"Marked overdue: {transaction.user.username} - {transaction.book.title}"
                    )
                )

        return count
