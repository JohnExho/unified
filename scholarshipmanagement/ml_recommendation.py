"""
ML-based scholarship recommendation engine.
Uses a simple scoring/ranking approach with sklearn for ranking by match.
"""
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent / "ml_models"


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
