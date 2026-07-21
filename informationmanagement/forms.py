from django import forms
from communityextensionservices.models import Member
from .models import (
    Project,
    BeneficiaryGroup,
    Partner,
    Activity,
    Report,
    ReportTemplate,
    MLModel,
    MLPipeline,
    MLExperiment,
    ContributionFund,
    FundAllocation,
    FundExpense,
    MemberContributionRecord,
    MemberContributionEntry,
    MasterDataDepartment,
)


class ProjectForm(forms.ModelForm):
    beneficiary_groups = forms.ModelMultipleChoiceField(
        queryset=BeneficiaryGroup.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select"}),
    )
    selected_members = forms.ModelMultipleChoiceField(
        queryset=Member.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "form-select"}),
    )

    class Meta:
        model = Project
        fields = [
            "name",
            "category",
            "lead",
            "status",
            "start_date",
            "end_date",
            "progress",
            "predicted_success",
            "predicted_reach",
            "member_selection_mode",
            "beneficiary_groups",
            "selected_members",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

    def save(self, commit=True):
        project = super().save(commit=False)
        beneficiary_groups = self.cleaned_data.get("beneficiary_groups") or []
        project.beneficiaries_count = sum(group.households for group in beneficiary_groups)

        if commit:
            project.save()
            self.save_m2m()
            if project.member_selection_mode == "all_members":
                project.selected_members.set(Member.objects.filter(status="active"))
            else:
                project.selected_members.set(self.cleaned_data.get("selected_members") or [])
            project.beneficiary_groups.set(beneficiary_groups)
            project.save(update_fields=["beneficiaries_count"])
        return project


class BeneficiaryGroupForm(forms.ModelForm):
    class Meta:
        model = BeneficiaryGroup
        fields = ["name", "segment", "households", "priority", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}


class PartnerForm(forms.ModelForm):
    class Meta:
        model = Partner
        fields = [
            "name",
            "partner_type",
            "status",
            "engagement",
            "contribution",
            "contact_person",
        ]


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ["title", "date", "location", "owner", "status", "participants"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ["title", "period", "status", "owner", "template"]
        widgets = {
            "template": forms.Select(attrs={"class": "form-select"}),
        }


class ReportTemplateForm(forms.ModelForm):
    class Meta:
        model = ReportTemplate
        fields = ["name"]


class MLModelForm(forms.ModelForm):
    class Meta:
        model = MLModel
        fields = ["name", "model_type", "status", "metric"]


class MLPipelineForm(forms.ModelForm):
    class Meta:
        model = MLPipeline
        fields = ["name", "status"]


class MLExperimentForm(forms.ModelForm):
    class Meta:
        model = MLExperiment
        fields = ["name", "owner", "status"]


# ============================================================================
# Feature 1: Contribution Allocation Management Forms
# ============================================================================


class ContributionFundForm(forms.ModelForm):
    """Form for creating and editing contribution funds"""

    class Meta:
        model = ContributionFund
        fields = [
            "project",
            "name",
            "description",
            "budget_required",
            "start_date",
            "status",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 4}),
            "budget_required": forms.NumberInput(attrs={"step": 0.01}),
        }


class FundAllocationForm(forms.ModelForm):
    """Form for allocating funds"""

    class Meta:
        model = FundAllocation
        fields = [
            "fund",
            "amount",
            "notes",
        ]
        widgets = {
            "amount": forms.NumberInput(attrs={"step": 0.01}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class FundExpenseForm(forms.ModelForm):
    """Form for recording fund expenses"""

    class Meta:
        model = FundExpense
        fields = [
            "category",
            "description",
            "amount",
            "expense_date",
            "reference_no",
        ]
        widgets = {
            "expense_date": forms.DateInput(attrs={"type": "date"}),
            "amount": forms.NumberInput(attrs={"step": 0.01}),
        }


# ============================================================================
# Feature 3: Master Data and Member Monitoring Forms
# ============================================================================


class MasterDataDepartmentForm(forms.ModelForm):
    """Form for managing departments master data"""

    class Meta:
        model = MasterDataDepartment
        fields = [
            "name",
            "description",
            "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class MemberContributionRecordForm(forms.ModelForm):
    """Form for managing member contribution records"""

    class Meta:
        model = MemberContributionRecord
        fields = [
            "project",
            "member_name",
            "employee_id",
            "department",
            "due_amount",
            "late_payment_penalties",
            "payment_status",
        ]
        widgets = {
            "due_amount": forms.NumberInput(attrs={"step": 0.01}),
            "late_payment_penalties": forms.NumberInput(attrs={"step": 0.01}),
        }


class MemberContributionEntryForm(forms.ModelForm):
    """Form for recording an individual contribution entry for a member."""

    class Meta:
        model = MemberContributionEntry
        fields = ["member", "contribution_date", "amount", "remarks"]
        widgets = {
            "member": forms.HiddenInput(),
            "contribution_date": forms.DateInput(attrs={"type": "date"}),
            "amount": forms.NumberInput(attrs={"step": 0.01}),
            "remarks": forms.Textarea(attrs={"rows": 3}),
        }


class MemberContributionFilterForm(forms.Form):
    """Form for filtering member contributions"""

    FILTER_CHOICES = [
        ("all", "All Members"),
        ("on_time", "On Time"),
        ("overdue", "Overdue"),
        ("delinquent", "Delinquent"),
    ]

    status_filter = forms.ChoiceField(
        choices=FILTER_CHOICES, required=False, initial="all"
    )
    member_name = forms.CharField(
        max_length=200, required=False, widget=forms.TextInput(
            attrs={"placeholder": "Search by name..."}
        )
    )
    employee_id = forms.CharField(
        max_length=100, required=False, widget=forms.TextInput(
            attrs={"placeholder": "Search by employee ID..."}
        )
    )
    department = forms.ModelChoiceField(
        queryset=MasterDataDepartment.objects.filter(is_active=True),
        required=False,
        empty_label="All Departments"
    )
    date_from = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    date_to = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
