from decimal import Decimal

from decimal import Decimal

from django.test import TestCase

from communityextensionservices.models import Member
from .forms import ProjectForm
from .models import (
    AssociationFund,
    AssociationFundTransaction,
    BeneficiaryGroup,
    MemberContributionEntry,
    MemberContributionRecord,
    Partner,
    Project,
)
from .services import FinancialReportingService


class ProjectEnhancementTests(TestCase):
    def setUp(self):
        self.beneficiary_group = BeneficiaryGroup.objects.create(
            name="Youth Livelihood",
            segment="Youth",
            households=120,
            priority="High",
        )
        self.active_member = Member.objects.create(
            first_name="Jane",
            last_name="Doe",
            status="active",
        )
        self.second_member = Member.objects.create(
            first_name="John",
            last_name="Smith",
            status="active",
        )

    def test_project_form_uses_selected_beneficiaries_and_all_members(self):
        form = ProjectForm(
            data={
                "name": "Community Garden",
                "category": "Environment",
                "lead": "Maria",
                "status": "Ongoing",
                "start_date": "2026-01-01",
                "end_date": "2026-12-31",
                "beneficiary_groups": [self.beneficiary_group.id],
                "member_selection_mode": "all_members",
                "selected_members": [self.active_member.id],
                "progress": 20,
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        project = form.save()

        self.assertEqual(project.beneficiaries_count, 120)
        self.assertEqual(project.selected_members.count(), 2)
        self.assertEqual(project.member_selection_mode, "all_members")


class PartnerContributionTests(TestCase):
    def test_partner_contribution_updates_association_fund(self):
        AssociationFund.objects.create(
            name="Association Fund",
            current_balance=Decimal("1000.00"),
            total_income=Decimal("1000.00"),
        )

        Partner.objects.create(
            name="Acme Corp",
            partner_type="Private",
            status="Active",
            engagement="High",
            contribution="Cash sponsorship",
            contribution_amount=Decimal("250.00"),
        )

        fund = AssociationFund.objects.get()
        self.assertEqual(fund.current_balance, Decimal("1250.00"))
        self.assertEqual(fund.total_income, Decimal("1250.00"))
        self.assertTrue(
            AssociationFundTransaction.objects.filter(
                source_type="partner_contribution"
            ).exists()
        )


class MemberContributionLedgerTests(TestCase):
    def test_member_contribution_entries_contribute_to_financial_summary(self):
        AssociationFund.objects.create(
            name="Association Fund",
            current_balance=Decimal("0.00"),
            total_income=Decimal("0.00"),
        )

        member = MemberContributionRecord.objects.create(
            member_name="Maria Santos",
            employee_id="EMP-1001",
        )

        MemberContributionEntry.objects.create(
            member=member,
            amount=Decimal("150.00"),
            remarks="January contribution",
        )
        MemberContributionEntry.objects.create(
            member=member,
            amount=Decimal("75.00"),
            remarks="February contribution",
        )

        summary = FinancialReportingService.get_association_financial_summary()

        self.assertEqual(summary["total_contributions"], Decimal("225.00"))
        self.assertEqual(summary["total_income"], Decimal("225.00"))
