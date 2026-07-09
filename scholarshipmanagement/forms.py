import re

from django import forms
from django.core.validators import RegexValidator
from .models import (
    StudentProfile, Scholarship, Application, Evaluation,
    Document, RenewalApplication,
)

phone_validator = RegexValidator(
    regex=r'^\+?\d{10,15}$',
    message='Enter a valid phone number with 10-15 digits.',
)


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = [
            'full_name', 'address', 'contact_number', 'family_background',
            'school_university', 'course_strand', 'gpa', 'academic_awards',
            'annual_family_income', 'province',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Full Name'}),
            'address': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2, 'placeholder': 'Complete Address'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+63...'}),
            'family_background': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'school_university': forms.TextInput(attrs={'class': 'form-input'}),
            'course_strand': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. BSCS, BSIT, ABM'}),
            'gpa': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0', 'max': '4.0', 'placeholder': '0.00 - 4.00'}),
            'academic_awards': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}),
            'annual_family_income': forms.NumberInput(attrs={'class': 'form-input', 'step': '1000', 'placeholder': 'Annual family income in PHP'}),
            'province': forms.TextInput(attrs={'class': 'form-input'}),
        }

    def clean_full_name(self):
        value = self.cleaned_data.get('full_name', '')
        return re.sub(r'<[^>]+>', '', value).strip()

    def clean_address(self):
        value = self.cleaned_data.get('address', '')
        return re.sub(r'<[^>]+>', '', value).strip()

    def clean_contact_number(self):
        value = self.cleaned_data.get('contact_number', '')
        phone_validator(value)
        return value

    def clean_course_strand(self):
        value = self.cleaned_data.get('course_strand', '')
        return re.sub(r'<[^>]+>', '', value).strip()

    def clean_province(self):
        value = self.cleaned_data.get('province', '')
        return re.sub(r'<[^>]+>', '', value).strip()


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['document_type', 'file']
        widgets = {
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'file': forms.FileInput(attrs={'class': 'form-input'}),
        }


class ScholarshipForm(forms.ModelForm):
    class Meta:
        model = Scholarship
        fields = [
            'name', 'description', 'category', 'scholarship_type', 'status',
            'award_amount', 'number_of_slots', 'renewable',
            'eligibility_rules', 'required_documents',
            'application_start_date', 'application_end_date', 'decision_announcement_date',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'scholarship_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'award_amount': forms.NumberInput(attrs={'class': 'form-input', 'step': '100'}),
            'number_of_slots': forms.NumberInput(attrs={'class': 'form-input', 'min': '1'}),
            'renewable': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'application_start_date': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'application_end_date': forms.DateTimeInput(attrs={'class': 'form-input', 'type': 'datetime-local'}),
            'decision_announcement_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
        }


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['motivation_essay', 'achievements']
        widgets = {
            'motivation_essay': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 5, 'placeholder': 'Tell us why you deserve this scholarship...'}),
            'achievements': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4, 'placeholder': 'List relevant academic and extracurricular achievements...'}),
        }

    def clean_motivation_essay(self):
        value = self.cleaned_data.get('motivation_essay', '')
        return re.sub(r'<[^>]+>', '', value).strip()

    def clean_achievements(self):
        value = self.cleaned_data.get('achievements', '')
        return re.sub(r'<[^>]+>', '', value).strip()


class EvaluationForm(forms.ModelForm):
    class Meta:
        model = Evaluation
        fields = [
            'academic_score', 'financial_need_score', 'interview_score',
            'extracurricular_score', 'recommendation', 'reviewer_comments',
        ]
        widgets = {
            'academic_score': forms.NumberInput(attrs={'class': 'form-input score-input', 'min': 0, 'max': 100, 'step': '0.1'}),
            'financial_need_score': forms.NumberInput(attrs={'class': 'form-input score-input', 'min': 0, 'max': 100, 'step': '0.1'}),
            'interview_score': forms.NumberInput(attrs={'class': 'form-input score-input', 'min': 0, 'max': 100, 'step': '0.1'}),
            'extracurricular_score': forms.NumberInput(attrs={'class': 'form-input score-input', 'min': 0, 'max': 100, 'step': '0.1'}),
            'recommendation': forms.Select(attrs={'class': 'form-select'}),
            'reviewer_comments': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4}),
        }


class RenewalApplicationForm(forms.ModelForm):
    class Meta:
        model = RenewalApplication
        fields = ['renewal_year', 'updated_grades', 'progress_report', 'behavioral_evaluation']
        widgets = {
            'renewal_year': forms.NumberInput(attrs={'class': 'form-input', 'min': 1}),
            'updated_grades': forms.FileInput(attrs={'class': 'form-input'}),
            'progress_report': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4}),
            'behavioral_evaluation': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
        }
