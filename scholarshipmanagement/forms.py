import re

from django import forms
from django.contrib.auth import get_user_model
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
    """Simplified evaluation form for renewal decisions based on retention prediction."""
    class Meta:
        model = Evaluation
        fields = [
            'recommendation', 'reviewer_comments',
        ]
        widgets = {
            'recommendation': forms.Select(attrs={'class': 'form-select'}),
            'reviewer_comments': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4, 'placeholder': 'Optional: reason for decision or override justification'}),
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


class StudentIntakeForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-input'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-input'}))
    password = forms.CharField(min_length=8, widget=forms.PasswordInput(attrs={'class': 'form-input'}))

    full_name = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'class': 'form-input'}))
    contact_number = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+639171234567'}))
    address = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-textarea', 'rows': 2}))
    school_university = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'class': 'form-input'}))
    course_strand = forms.CharField(max_length=255, widget=forms.TextInput(attrs={'class': 'form-input'}))
    province = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-input'}))

    gpa = forms.FloatField(min_value=0.0, max_value=4.0, widget=forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}))
    annual_family_income = forms.DecimalField(min_value=0, max_digits=12, decimal_places=2, widget=forms.NumberInput(attrs={'class': 'form-input', 'step': '1000'}))

    failed_subjects = forms.IntegerField(min_value=0, initial=0, widget=forms.NumberInput(attrs={'class': 'form-input'}))
    units_enrolled = forms.IntegerField(min_value=0, initial=21, widget=forms.NumberInput(attrs={'class': 'form-input'}))
    attendance_rate = forms.FloatField(min_value=0.0, max_value=100.0, initial=85.0, widget=forms.NumberInput(attrs={'class': 'form-input', 'step': '0.1'}))
    socioeconomic_status = forms.ChoiceField(
        choices=[('low', 'Low'), ('middle', 'Middle'), ('high', 'High')],
        initial='middle',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def clean_username(self):
        User = get_user_model()
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Username already exists.')
        return username

    def clean_email(self):
        User = get_user_model()
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email already exists.')
        return email

    def clean_full_name(self):
        return re.sub(r'<[^>]+>', '', self.cleaned_data.get('full_name', '')).strip()

    def clean_address(self):
        return re.sub(r'<[^>]+>', '', self.cleaned_data.get('address', '')).strip()

    def clean_course_strand(self):
        return re.sub(r'<[^>]+>', '', self.cleaned_data.get('course_strand', '')).strip()

    def clean_province(self):
        return re.sub(r'<[^>]+>', '', self.cleaned_data.get('province', '')).strip()

    def clean_contact_number(self):
        value = self.cleaned_data.get('contact_number', '').strip()
        phone_validator(value)
        return value
