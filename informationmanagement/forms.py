from django import forms
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
)


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "name",
            "category",
            "lead",
            "status",
            "start_date",
            "end_date",
            "beneficiaries_count",
            "progress",
            "predicted_success",
            "predicted_reach",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


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
        fields = ["title", "period", "status", "owner"]


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
