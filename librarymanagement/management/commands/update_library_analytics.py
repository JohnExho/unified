"""
Management command to update library analytics and data mining
Run this command periodically to update recommendations, trending books, and user clusters
Usage: python manage.py update_library_analytics
"""

from django.core.management.base import BaseCommand
from librarymanagement.services import DataMiningServices, RecommendationServices


class Command(BaseCommand):
    help = (
        "Update library analytics: trending books, user clusters, and recommendations"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--recommendations",
            action="store_true",
            help="Update user recommendations",
        )
        parser.add_argument(
            "--trending",
            action="store_true",
            help="Update trending books",
        )
        parser.add_argument(
            "--clusters",
            action="store_true",
            help="Analyze and update user clusters",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Run all analytics updates",
        )

    def handle(self, *args, **options):
        run_all = options["all"]

        if run_all or options["trending"]:
            self.stdout.write(self.style.WARNING("Updating trending books..."))
            self.update_trending_books()

        if run_all or options["clusters"]:
            self.stdout.write(
                self.style.WARNING("Analyzing user patterns and clusters...")
            )
            self.update_user_clusters()

        if run_all or options["recommendations"]:
            self.stdout.write(self.style.WARNING("Generating user recommendations..."))
            self.update_recommendations()

        if not (
            run_all
            or options["trending"]
            or options["clusters"]
            or options["recommendations"]
        ):
            self.stdout.write(
                self.style.ERROR(
                    "Please specify what to update: --all, --trending, --clusters, or --recommendations"
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS("\nAnalytics update completed successfully!")
        )

    def update_trending_books(self):
        """Update trending books for all periods"""
        periods = ["daily", "weekly", "monthly", "yearly"]

        for period in periods:
            count = DataMiningServices.analyze_trending_books(period_type=period)
            self.stdout.write(f"  - {period.capitalize()}: {count} trending books")

    def update_user_clusters(self):
        """Analyze user patterns and create clusters"""
        cluster_count = DataMiningServices.analyze_user_patterns()
        self.stdout.write(f"  - Created/updated {cluster_count} user clusters")

        # Show demand predictions
        high_demand = DataMiningServices.predict_demand()
        if high_demand:
            self.stdout.write(f"  - Found {len(high_demand)} high-demand books")
            for item in high_demand[:5]:  # Show top 5
                self.stdout.write(
                    f'    * {item["book"].title}: {item["demand_ratio"]}x demand ratio '
                    f'(recommend {item["recommended_copies"]} additional copies)'
                )

    def update_recommendations(self):
        """Generate recommendations for all users"""
        count = RecommendationServices.update_all_recommendations()
        self.stdout.write(f"  - Updated recommendations for {count} users")
