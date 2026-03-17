from django.core.management.base import BaseCommand
from django.utils import timezone
from informationmanagement.models import (
    Project,
    BeneficiaryGroup,
    Partner,
    Activity,
    Report,
    ReportTemplate,
    MLModel,
    MLPipeline,
    MLExperiment,
)


class Command(BaseCommand):
    help = "Seed Information Management with sample data (23 items total)."

    def handle(self, *args, **options):
        Project.objects.all().delete()
        BeneficiaryGroup.objects.all().delete()
        Partner.objects.all().delete()
        Activity.objects.all().delete()
        Report.objects.all().delete()
        ReportTemplate.objects.all().delete()
        MLModel.objects.all().delete()
        MLPipeline.objects.all().delete()
        MLExperiment.objects.all().delete()

        projects = [
            Project(
                name="Community Literacy Boost",
                category="Education",
                lead="Prof. C. Reyes",
                status="Ongoing",
                start_date=timezone.now().date(),
                end_date=timezone.now().date(),
                beneficiaries_count=420,
                progress=72,
                predicted_success=82.5,
                predicted_reach=460,
            ),
            Project(
                name="Agri-Tech Starter Kit",
                category="Livelihood",
                lead="Dr. L. Santos",
                status="Ongoing",
                start_date=timezone.now().date(),
                end_date=timezone.now().date(),
                beneficiaries_count=210,
                progress=38,
                predicted_success=76.2,
                predicted_reach=250,
            ),
            Project(
                name="Safe Water Initiative",
                category="Health",
                lead="Dr. M. Dela Cruz",
                status="Proposed",
                start_date=timezone.now().date(),
                end_date=timezone.now().date(),
                beneficiaries_count=130,
                progress=15,
                predicted_success=64.4,
                predicted_reach=170,
            ),
            Project(
                name="Eco-Youth Engagement",
                category="Environment",
                lead="Ms. P. Valdez",
                status="Completed",
                start_date=timezone.now().date(),
                end_date=timezone.now().date(),
                beneficiaries_count=180,
                progress=100,
                predicted_success=91.3,
                predicted_reach=200,
            ),
            Project(
                name="Digital Literacy Caravan",
                category="Education",
                lead="Mr. A. Gomez",
                status="Ongoing",
                start_date=timezone.now().date(),
                end_date=timezone.now().date(),
                beneficiaries_count=95,
                progress=55,
                predicted_success=70.8,
                predicted_reach=120,
            ),
            Project(
                name="Barangay Health Navigator",
                category="Health",
                lead="Nurse J. Ramos",
                status="Ongoing",
                start_date=timezone.now().date(),
                end_date=timezone.now().date(),
                beneficiaries_count=165,
                progress=74,
                predicted_success=79.4,
                predicted_reach=190,
            ),
            Project(
                name="Community Composting Network",
                category="Environment",
                lead="Engr. T. Navarro",
                status="Completed",
                start_date=timezone.now().date(),
                end_date=timezone.now().date(),
                beneficiaries_count=140,
                progress=100,
                predicted_success=88.1,
                predicted_reach=158,
            ),
            Project(
                name="Microenterprise Mentoring",
                category="Livelihood",
                lead="Ms. D. Flores",
                status="Proposed",
                start_date=timezone.now().date(),
                end_date=timezone.now().date(),
                beneficiaries_count=120,
                progress=22,
                predicted_success=61.9,
                predicted_reach=145,
            ),
        ]
        Project.objects.bulk_create(projects)

        beneficiary_groups = [
            BeneficiaryGroup(
                name="Brgy. San Miguel",
                segment="Women-led households",
                households=220,
                priority="High",
            ),
            BeneficiaryGroup(
                name="Brgy. Poblacion",
                segment="Youth",
                households=180,
                priority="Medium",
            ),
            BeneficiaryGroup(
                name="Brgy. Mabini",
                segment="Senior citizens",
                households=160,
                priority="Medium",
            ),
            BeneficiaryGroup(
                name="Brgy. Bagong Silang",
                segment="Farmer groups",
                households=140,
                priority="Low",
            ),
        ]
        BeneficiaryGroup.objects.bulk_create(beneficiary_groups)

        partners = [
            Partner(
                name="Local Health Unit",
                partner_type="Government",
                status="Active",
                engagement="High",
                contribution="Medical missions",
                contact_person="Dr. Perez",
            ),
            Partner(
                name="AgriCoop Federation",
                partner_type="NGO",
                status="Active",
                engagement="Medium",
                contribution="Inputs and training",
                contact_person="Ms. Vega",
            ),
            Partner(
                name="Green Future Foundation",
                partner_type="Private",
                status="Prospecting",
                engagement="Low",
                contribution="CSR funding",
                contact_person="Mr. Tan",
            ),
        ]
        Partner.objects.bulk_create(partners)

        activities = [
            Activity(
                title="Data collection training",
                date=timezone.now().date(),
                location="CES Hub",
                owner="Extension Unit",
                status="Scheduled",
                participants=24,
            ),
            Activity(
                title="Partner alignment meeting",
                date=timezone.now().date(),
                location="Board Room",
                owner="Linkages Unit",
                status="Scheduled",
                participants=14,
            ),
            Activity(
                title="Baseline survey kickoff",
                date=timezone.now().date(),
                location="Brgy. Poblacion",
                owner="Research Unit",
                status="Completed",
                participants=32,
            ),
        ]
        Activity.objects.bulk_create(activities)

        reports = [
            Report(
                title="Accomplishment Report",
                period="Q4 2025",
                status="Generated",
                owner="QA Team",
            ),
        ]
        Report.objects.bulk_create(reports)

        templates = [
            ReportTemplate(name="Extension Activity Report"),
        ]
        ReportTemplate.objects.bulk_create(templates)

        models = [
            MLModel(
                name="Program Reach Predictor",
                model_type="Regression",
                status="Prototype",
                metric="MAE 0.18",
            ),
        ]
        MLModel.objects.bulk_create(models)

        pipelines = [
            MLPipeline(name="Feature Store", status="Design"),
        ]
        MLPipeline.objects.bulk_create(pipelines)

        experiments = [
            MLExperiment(name="Impact Score v2", owner="ML Team", status="Running"),
        ]
        MLExperiment.objects.bulk_create(experiments)

        self.stdout.write(
            self.style.SUCCESS("Seeded Information Management with 23 items.")
        )
