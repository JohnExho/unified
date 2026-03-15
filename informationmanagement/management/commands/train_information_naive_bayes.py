"""
Train and run basic Naive Bayes classification for IMS projects.
Usage:
  python manage.py train_information_naive_bayes
  python manage.py train_information_naive_bayes --days 3650 --show-top 10
"""

from django.core.management.base import BaseCommand
from informationmanagement.services import InformationClassificationService


class Command(BaseCommand):
    help = "Train IMS Naive Bayes classifier and show top project classifications"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=3650,
            help="Lookback window (in days) for training data",
        )
        parser.add_argument(
            "--show-top",
            type=int,
            default=10,
            help="How many top predictions to print",
        )

    def handle(self, *args, **options):
        days = options["days"]
        show_top = options["show_top"]

        self.stdout.write(self.style.WARNING("Training Naive Bayes model..."))
        result = InformationClassificationService.train_naive_bayes_classifier(
            lookback_days=days
        )

        if not result.get("trained"):
            self.stdout.write(
                self.style.ERROR(
                    f"Model not trained: {result.get('reason', 'Unknown reason')}"
                )
            )
            return

        predictions = InformationClassificationService.predict_project_success()

        accuracy = result.get("accuracy")
        if accuracy is not None:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Training complete. samples={result.get('samples')} accuracy={accuracy}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Training complete. samples={result.get('samples')}"
                )
            )

        if not predictions:
            self.stdout.write(
                self.style.WARNING("No high-confidence predictions found.")
            )
            return

        for row in predictions[:show_top]:
            self.stdout.write(
                f"- {row['project'].name} | confidence={round(row['confidence'] * 100, 1)}% | "
                f"predicted_reach={row['predicted_reach']}"
            )
