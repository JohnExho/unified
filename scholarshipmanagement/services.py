"""
Business logic services for Scholarship Management.
"""
from django.utils import timezone
from .models import (
    StudentProfile, Scholarship, Application, Evaluation,
    Document, Notification, ScholarshipOffer, RejectionAnalysis, AuditLog,
)


# ----------------------
# Stage 1 Completion
# ----------------------
def get_stage_1_checklist(profile: StudentProfile) -> dict:
    """Return Stage 1 completion checklist for a student profile."""
    has_gov_id = Document.objects.filter(
        user=profile.user,
        document_type='government_id',
        verification_status__in=['pending', 'verified']
    ).exists()
    has_transcript = Document.objects.filter(
        user=profile.user,
        document_type='transcript',
        verification_status__in=['pending', 'verified']
    ).exists()

    items = {
        'full_name': bool(profile.full_name),
        'address': bool(profile.address),
        'contact_number': bool(profile.contact_number),
        'school_university': bool(profile.school_university),
        'course_strand': bool(profile.course_strand),
        'gpa': profile.gpa is not None,
        'annual_family_income': profile.annual_family_income is not None,
        'province': bool(profile.province),
        'government_id': has_gov_id,
        'transcript': has_transcript,
    }
    total = len(items)
    completed = sum(1 for v in items.values() if v)
    return {
        'items': items,
        'completed': completed,
        'total': total,
        'percent': round((completed / total) * 100) if total else 0,
        'is_complete': completed == total,
    }


def refresh_stage_1(profile: StudentProfile):
    """Re-evaluate Stage 1 and update the profile."""
    checklist = get_stage_1_checklist(profile)
    doc_ok = checklist['items'].get('government_id') and checklist['items'].get('transcript')
    profile.all_required_documents_uploaded = bool(doc_ok)
    profile.check_and_update_stage_1()

    if profile.is_stage_1_complete:
        # Notify student that Stage 2 is unlocked
        Notification.objects.get_or_create(
            recipient=profile.user,
            notification_type='stage_unlocked',
            title='Stage 2 Unlocked!',
            defaults={
                'message': 'Your profile is complete. You can now browse and apply for scholarships.',
            }
        )


# ----------------------
# Eligibility Engine
# ----------------------
def check_eligibility(profile: StudentProfile, scholarship: Scholarship) -> dict:
    """
    Run the rule-based eligibility engine against scholarship.eligibility_rules.

    Rules JSON format example:
    {
        "min_gpa": 3.0,
        "max_annual_income": 250000,
        "required_course": ["BSCS", "BSIT"],
        "required_province": ["Cebu", "Manila"]
    }
    Returns dict: {eligible: bool, failed_rules: [str], passed_rules: [str]}
    """
    rules = scholarship.eligibility_rules or {}
    failed = []
    passed = []

    if 'min_gpa' in rules:
        threshold = float(rules['min_gpa'])
        if profile.gpa is None or profile.gpa < threshold:
            failed.append(f"GPA below minimum required ({threshold}). Yours: {profile.gpa}")
        else:
            passed.append(f"GPA meets requirement (≥ {threshold})")

    if 'max_annual_income' in rules:
        cap = float(rules['max_annual_income'])
        if profile.annual_family_income is None or float(profile.annual_family_income) > cap:
            failed.append(f"Annual family income exceeds cap (₱{cap:,.0f})")
        else:
            passed.append(f"Income within limit (≤ ₱{cap:,.0f})")

    if 'required_course' in rules:
        allowed = [c.upper() for c in rules['required_course']]
        if not profile.course_strand or profile.course_strand.upper() not in allowed:
            failed.append(f"Course '{profile.course_strand}' not in eligible courses: {', '.join(rules['required_course'])}")
        else:
            passed.append(f"Course '{profile.course_strand}' is eligible")

    if 'required_province' in rules:
        allowed = [p.lower() for p in rules['required_province']]
        if not profile.province or profile.province.lower() not in allowed:
            failed.append(f"Province '{profile.province}' not in eligible provinces")
        else:
            passed.append(f"Province '{profile.province}' is eligible")

    if 'required_documents' in rules:
        required_docs = rules['required_documents']
        for doc_type in required_docs:
            has_doc = Document.objects.filter(
                user=profile.user,
                document_type=doc_type,
                verification_status__in=['pending', 'verified']
            ).exists()
            if not has_doc:
                failed.append(f"Missing required document: {doc_type.replace('_', ' ').title()}")
            else:
                passed.append(f"Document '{doc_type.replace('_', ' ').title()}' present")

    return {
        'eligible': len(failed) == 0,
        'failed_rules': failed,
        'passed_rules': passed,
    }


# ----------------------
# Application Workflow
# ----------------------
def submit_application(application: Application, user) -> bool:
    """Move application from draft to submitted."""
    if application.status != 'draft':
        return False
    application.status = 'submitted'
    application.submitted_at = timezone.now()
    application.save(update_fields=['status', 'submitted_at'])

    Notification.objects.create(
        recipient=application.student,
        notification_type='application_status',
        title='Application Submitted',
        message=f'Your application for "{application.scholarship.name}" has been submitted.',
        related_application=application,
        related_scholarship=application.scholarship,
    )
    _log_audit(user, 'create', 'Application', application.id, f"Submitted application for {application.scholarship.name}")
    return True


def release_decision(application: Application, decision: str, admin_user) -> bool:
    """Admin finalises decision: accepted / rejected / waitlisted."""
    valid = {'accepted', 'rejected', 'waitlisted'}
    if decision not in valid:
        return False

    application.status = decision
    application.save(update_fields=['status'])

    if decision == 'accepted':
        # Create scholarship offer
        ScholarshipOffer.objects.get_or_create(
            application=application,
            defaults={'offer_amount': application.scholarship.award_amount}
        )
        notif_title = 'Scholarship Offer Received!'
        notif_message = f'Congratulations! You have been accepted for "{application.scholarship.name}".'
    elif decision == 'rejected':
        notif_title = 'Application Result'
        notif_message = f'Your application for "{application.scholarship.name}" was not selected.'
        # Create rejection analysis record
        _create_rejection_analysis(application)
    else:
        notif_title = 'Application Waitlisted'
        notif_message = f'You have been placed on the waitlist for "{application.scholarship.name}".'

    Notification.objects.create(
        recipient=application.student,
        notification_type='decision_released',
        title=notif_title,
        message=notif_message,
        related_application=application,
        related_scholarship=application.scholarship,
    )
    _log_audit(admin_user, 'decide', 'Application', application.id, f"Decision: {decision}")
    return True


def respond_to_offer(offer: ScholarshipOffer, response: str, student) -> bool:
    """Student accepts or declines an offer."""
    if response == 'accept':
        offer.status = 'accepted'
        offer.application.status = 'offer_accepted'
        Notification.objects.create(
            recipient=student,
            notification_type='application_status',
            title='Offer Accepted',
            message=f'You have accepted the scholarship offer for "{offer.application.scholarship.name}".',
            related_application=offer.application,
            related_scholarship=offer.application.scholarship,
        )
    elif response == 'decline':
        offer.status = 'declined'
        offer.application.status = 'offer_declined'
        Notification.objects.create(
            recipient=student,
            notification_type='application_status',
            title='Offer Declined',
            message=f'You have declined the scholarship offer for "{offer.application.scholarship.name}".',
            related_application=offer.application,
            related_scholarship=offer.application.scholarship,
        )
    else:
        return False
    offer.responded_at = timezone.now()
    offer.save(update_fields=['status', 'responded_at'])
    offer.application.save(update_fields=['status'])
    return True


# ----------------------
# Helpers
# ----------------------
def _create_rejection_analysis(application: Application):
    """Generate a basic rejection analysis record."""
    try:
        profile = application.student.scholarship_profile
    except StudentProfile.DoesNotExist:
        return

    result = check_eligibility(profile, application.scholarship)
    failed = result['failed_rules']

    category = 'other'
    for rule_msg in failed:
        if 'gpa' in rule_msg.lower():
            category = 'academic'
            break
        elif 'income' in rule_msg.lower():
            category = 'financial'
            break
        elif 'document' in rule_msg.lower():
            category = 'document'
            break

    suggestions = []
    for rule_msg in failed:
        if 'gpa' in rule_msg.lower():
            suggestions.append('Improve your academic GPA by focusing on core subjects.')
        elif 'income' in rule_msg.lower():
            suggestions.append('Look for scholarships with higher income thresholds.')
        elif 'document' in rule_msg.lower():
            suggestions.append('Complete your required document submissions in your profile.')

    RejectionAnalysis.objects.update_or_create(
        application=application,
        defaults={
            'qualification_status': result['eligible'],
            'rejected_category': category,
            'failed_criteria': failed,
            'recommendations': result['passed_rules'],
            'analysis_summary': f"Application reviewed. Failed {len(failed)} eligibility criteria.",
            'improvement_suggestions': suggestions,
        }
    )


def _log_audit(user, action: str, model: str, target_id, description: str, ip=None, ua=None):
    AuditLog.objects.create(
        user=user,
        action=action,
        target_model=model,
        target_id=target_id,
        description=description,
        ip_address=ip,
        user_agent=ua or '',
    )
