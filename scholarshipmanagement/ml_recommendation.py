"""
ML-based retention prediction and scholarship recommendation for single-school system.

Primary model: predict_retention(profile) → classifies existing scholars into
  Retain / At-Risk / Failed (for renewal assessment).

Secondary (optional): generate_recommendations(profile, scholarships) → ranks
  scholarships by match score (used only for student browsing).

This is a simplified single-institution system (not multi-tenant).
"""
from pathlib import Path

import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

MODEL_DIR = Path(__file__).resolve().parent / "ml_models"


def predict_retention(profile, scholarship_type='general'):
    """Classify a student into Retain / At-Risk / Failed using thesis-aligned inputs for renewal classification."""
    gpa = float(getattr(profile, 'gpa', 0) or 0.0)
    if gpa <= 2.75:
        return {'label': 'At-Risk', 'confidence': 100.0}

    features = np.array([
        [
            gpa,
            float(getattr(profile, 'failed_subjects', 0) or 0),
            float(getattr(profile, 'units_enrolled', 0) or 0),
            float(getattr(profile, 'attendance_rate', 0) or 0),
            1.0 if scholarship_type == 'merit_based' else 0.0,
            1.0 if getattr(profile, 'socioeconomic_status', '') == 'low' else 0.0,
        ]
    ])

    X_train = np.array([
        [3.8, 0, 24, 92, 1, 0],
        [3.5, 1, 21, 86, 1, 0],
        [2.8, 2, 18, 74, 1, 1],
        [2.3, 3, 16, 63, 0, 1],
        [1.8, 4, 12, 48, 0, 1],
        [1.4, 5, 9, 35, 0, 1],
    ])
    y_train = np.array(['Retain', 'Retain', 'At-Risk', 'At-Risk', 'Failed', 'Failed'])

    tree_model = DecisionTreeClassifier(max_depth=3, random_state=7)
    tree_model.fit(X_train, y_train)

    logistic_model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, random_state=7))
    logistic_model.fit(X_train, y_train)

    tree_prob = tree_model.predict_proba(features)[0]
    logistic_prob = logistic_model.predict_proba(features)[0]
    classes = tree_model.classes_
    combined = np.zeros(len(classes))
    for idx, label in enumerate(classes):
        combined[idx] = (tree_prob[idx] + logistic_prob[idx]) / 2.0

    label = classes[np.argmax(combined)]
    confidence = round(float(np.max(combined)) * 100, 1)

    return {'label': label, 'confidence': confidence}


def build_overall_prediction_summary(profiles, scholarships):
    """Build an aggregate prediction summary across multiple profiles and scholarships."""
    profiles = list(profiles or [])
    scholarships = list(scholarships or [])

    valid_profiles = [profile for profile in profiles if profile.is_ml_ready]
    valid_scholarships = [scholarship for scholarship in scholarships if scholarship.is_accepting_applications]

    if not valid_profiles or not valid_scholarships:
        return {
            'total_profiles': len(profiles),
            'ml_ready_profiles': len(valid_profiles),
            'total_scholarships': len(scholarships),
            'average_match_score': 0.0,
            'average_eligibility_probability': 0.0,
            'average_success_probability': 0.0,
            'top_scholarship': None,
            'overall_predictions': [],
        }

    scholarship_totals = {}
    score_samples = []

    for profile in valid_profiles:
        for scholarship in valid_scholarships:
            score_data = compute_match_score(profile, scholarship)
            if score_data['eligibility_probability'] <= 0:
                continue

            score_samples.append(score_data)
            entry = scholarship_totals.setdefault(scholarship.id, {
                'scholarship': scholarship,
                'match_total': 0.0,
                'eligibility_total': 0.0,
                'success_total': 0.0,
                'count': 0,
            })
            entry['match_total'] += score_data['match_score']
            entry['eligibility_total'] += score_data['eligibility_probability'] * 100
            entry['success_total'] += score_data['success_probability'] * 100
            entry['count'] += 1

    overall_predictions = []
    for entry in scholarship_totals.values():
        count = entry['count'] or 1
        overall_predictions.append({
            'scholarship': entry['scholarship'],
            'avg_match_score': round(entry['match_total'] / count, 1),
            'avg_eligibility_probability': round(entry['eligibility_total'] / count, 1),
            'avg_success_probability': round(entry['success_total'] / count, 1),
            'prediction_label': 'High demand' if (entry['match_total'] / count) >= 70 else 'Steady interest',
            'match_count': count,
        })

    overall_predictions.sort(key=lambda item: (-item['avg_match_score'], -item['avg_success_probability']))

    top_scholarship = overall_predictions[0]['scholarship'] if overall_predictions else None

    return {
        'total_profiles': len(profiles),
        'ml_ready_profiles': len(valid_profiles),
        'total_scholarships': len(scholarships),
        'average_match_score': round(sum(item['match_score'] for item in score_samples) / len(score_samples), 1) if score_samples else 0.0,
        'average_eligibility_probability': round(sum(item['eligibility_probability'] for item in score_samples) / len(score_samples) * 100, 1) if score_samples else 0.0,
        'average_success_probability': round(sum(item['success_probability'] for item in score_samples) / len(score_samples) * 100, 1) if score_samples else 0.0,
        'top_scholarship': top_scholarship,
        'overall_predictions': overall_predictions[:5],
    }


def compute_match_score(profile, scholarship) -> dict:
    """
    Rule-enhanced match scoring between a student profile and a scholarship.
    Returns: {match_score, eligibility_probability, success_probability, reason_tags, explanation}
    """
    rules = scholarship.eligibility_rules or {}
    tags = []
    score_components = []

    # GPA score component
    gpa_score = 0.0
    if profile.gpa is not None:
        if 'min_gpa' in rules:
            min_gpa = float(rules['min_gpa'])
            if profile.gpa >= min_gpa:
                gpa_score = min(100.0, ((profile.gpa - min_gpa) / (4.0 - min_gpa + 0.01)) * 100)
                tags.append('strong_academic')
            else:
                gpa_score = 0.0
        else:
            gpa_score = min(100.0, (profile.gpa / 4.0) * 100)
            if profile.gpa >= 3.5:
                tags.append('honor_student')
    score_components.append(('gpa', gpa_score, 0.40))

    # Financial need component
    financial_score = 0.0
    if profile.annual_family_income is not None:
        income = float(profile.annual_family_income)
        if 'max_annual_income' in rules:
            cap = float(rules['max_annual_income'])
            if income <= cap:
                financial_score = min(100.0, ((cap - income) / cap) * 100)
                tags.append('financially_qualified')
        else:
            # Lower income = higher need score
            financial_score = min(100.0, max(0, (1 - income / 500000) * 100))
    if profile.financial_need_score is not None:
        financial_score = max(financial_score, profile.financial_need_score)
        tags.append('high_financial_need')
    score_components.append(('financial', financial_score, 0.30))

    # Course/location match
    match_score = 30.0  # baseline
    if 'required_course' in rules:
        allowed = [c.upper() for c in rules['required_course']]
        if profile.course_strand and profile.course_strand.upper() in allowed:
            match_score = 80.0
            tags.append('course_match')
    if 'required_province' in rules:
        allowed_prov = [p.lower() for p in rules['required_province']]
        if profile.province and profile.province.lower() in allowed_prov:
            match_score = min(100.0, match_score + 20.0)
            tags.append('location_match')
    score_components.append(('match', match_score, 0.30))

    # Weighted total
    total = sum(v * w for (_, v, w) in score_components)
    total = round(min(100.0, max(0.0, total)), 2)

    # Eligibility probability: 1.0 if all hard rules pass, else proportional
    failed_hard = 0
    if 'min_gpa' in rules and (profile.gpa is None or profile.gpa < float(rules['min_gpa'])):
        failed_hard += 1
    if 'max_annual_income' in rules and (
        profile.annual_family_income is None or
        float(profile.annual_family_income) > float(rules['max_annual_income'])
    ):
        failed_hard += 1
    hard_rule_count = sum(1 for k in rules if k in ('min_gpa', 'max_annual_income', 'required_course', 'required_province'))
    eligibility_prob = round(max(0.0, 1.0 - (failed_hard / max(1, hard_rule_count))), 2)

    # Success probability based on total score
    success_prob = round(total / 100.0, 2)

    # Scholarship category tag
    category_map = {
        'merit_based': 'merit_scholarship',
        'need_based': 'need_based_scholarship',
        'talent_based': 'talent_scholarship',
    }
    tags.append(category_map.get(scholarship.category, 'general_scholarship'))

    explanation_parts = []
    if gpa_score >= 70:
        explanation_parts.append("strong academic record")
    if financial_score >= 70:
        explanation_parts.append("meets financial need criteria")
    if match_score >= 70:
        explanation_parts.append("course/location match")
    explanation = f"Recommended based on: {', '.join(explanation_parts)}." if explanation_parts else "Partial match with eligibility criteria."

    return {
        'match_score': total,
        'eligibility_probability': eligibility_prob,
        'success_probability': success_prob,
        'reason_tags': tags,
        'explanation': explanation,
    }


def generate_recommendations(profile, scholarships):
    """
    Generate ranked recommendations for a student profile from a list of scholarships.
    Returns sorted list of {scholarship, score_data} dicts.
    """
    results = []
    for s in scholarships:
        if not s.is_accepting_applications:
            continue
        score_data = compute_match_score(profile, s)
        if score_data['eligibility_probability'] > 0:
            results.append({'scholarship': s, **score_data})

    results.sort(key=lambda x: (-x['match_score'], -x['success_probability']))
    for rank, r in enumerate(results, start=1):
        r['rank'] = rank
    return results
