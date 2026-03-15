"""
Train and run basic Random Forest demand classification for Library Management.
Usage:
  python manage.py train_library_random_forest
  python manage.py train_library_random_forest --days 120 --show-top 10
"""

from django.core.management.base import BaseCommand
from librarymanagement.services import DataMiningServices


class Command(BaseCommand):
    help = "Train basic Random Forest model and show high-demand book predictions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="Historical window (in days) for training features",
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

        self.stdout.write(self.style.WARNING("Training Random Forest model..."))
        result = DataMiningServices.train_random_forest_demand_model(period_days=days)

        if not result.get("trained"):
            self.stdout.write(
                self.style.ERROR(
                    f"Model not trained: {result.get('reason', 'Unknown reason')}"
                )
            )
            self.stdout.write("Falling back to heuristic demand prediction for now.")

        predictions = DataMiningServices.predict_demand()

        if not predictions:
            self.stdout.write(self.style.WARNING("No high-demand books detected."))
            return

        self.stdout.write(
            self.style.SUCCESS(f"Found {len(predictions)} high-demand books.")
        )

        for row in predictions[:show_top]:
            confidence = row.get("confidence")
            confidence_text = (
                f"{round(float(confidence) * 100, 1)}%"
                if confidence is not None
                else "N/A"
            )
            self.stdout.write(
                f"- {row['book'].title} | confidence={confidence_text} | "
                f"demand_ratio={row['demand_ratio']} | "
                f"recommend+={row['recommended_copies']}"
            )
