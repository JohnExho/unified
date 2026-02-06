from django import forms
from .models import Member, DuesPayment, Activity, DocumentRecord


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = [
            "first_name",
            "last_name",
            "email",
            "phone",
            "classification",
            "status",
            "joined_date",
            "department",
            "notes",
            "engagement_score",
            "churn_risk_score",
            "predicted_status",
            "cluster_label",
        ]
        widgets = {
            "joined_date": forms.DateInput(attrs={"type": "date"}),
        }


class DuesPaymentForm(forms.ModelForm):
    class Meta:
        model = DuesPayment
        fields = [
            "member",
            "amount",
            "due_date",
            "paid_date",
            "status",
            "method",
            "reference_no",
            "remarks",
            "late_payment_risk",
        ]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "paid_date": forms.DateInput(attrs={"type": "date"}),
        }


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = [
            "title",
            "category",
            "start_date",
            "end_date",
            "location",
            "status",
            "description",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }


class DocumentRecordForm(forms.ModelForm):
    class Meta:
        model = DocumentRecord
        fields = [
            "title",
            "category",
            "storage_url",
            "summary",
            "is_sensitive",
        ]
