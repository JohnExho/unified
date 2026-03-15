"""
Train and run basic K-Means clustering for CES members.
Usage:
  python manage.py train_ces_kmeans
  python manage.py train_ces_kmeans --k 4 --show-top 10
"""

from django.core.management.base import BaseCommand
from communityextensionservices.services import CESClusteringService


class Command(BaseCommand):
    help = "Train CES K-Means model and display clustered members"

    def add_arguments(self, parser):
        parser.add_argument(
            "--k",
            type=int,
            default=3,
            help="Number of clusters",
        )
        parser.add_argument(
            "--show-top",
            type=int,
            default=10,
            help="How many member rows to print",
        )

    def handle(self, *args, **options):
        k = options["k"]
        show_top = options["show_top"]

        if k < 2:
            k = 2
        if k > 8:
            k = 8

        self.stdout.write(self.style.WARNING("Training CES K-Means model..."))
        result = CESClusteringService.train_kmeans_model(k=k)

        if not result.get("trained"):
            self.stdout.write(
                self.style.ERROR(
                    f"Model not trained: {result.get('reason', 'Unknown reason')}"
                )
            )
            return

        assignments = CESClusteringService.run_member_clustering()
        silhouette = result.get("silhouette")

        if silhouette is not None:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Training complete. samples={result.get('samples')} silhouette={silhouette}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Training complete. samples={result.get('samples')}"
                )
            )

        if not assignments:
            self.stdout.write(self.style.WARNING("No member clusters generated."))
            return

        for row in assignments[:show_top]:
            self.stdout.write(
                f"- {row['member'].last_name}, {row['member'].first_name} | "
                f"{row['cluster_label']} | engagement={row['engagement_score']} | "
                f"churn_risk={row['churn_risk_score']}"
            )
