from django.utils import timezone
from .utils import percent_change


def get_information_dashboard_data():
    today = timezone.now().date()
    stats = [
        {
            "label": "Active Projects",
            "value": 24,
            "delta": percent_change(24, 21),
            "trend": "up",
        },
        {
            "label": "Partner Orgs",
            "value": 18,
            "delta": percent_change(18, 15),
            "trend": "up",
        },
        {
            "label": "Beneficiaries",
            "value": 1260,
            "delta": percent_change(1260, 1210),
            "trend": "up",
        },
        {
            "label": "Activities This Month",
            "value": 12,
            "delta": percent_change(12, 14),
            "trend": "down",
        },
    ]

    projects = [
        {
            "name": "Community Literacy Boost",
            "category": "Education",
            "status": "Ongoing",
            "start": "Jan 08, 2026",
            "end": "Apr 21, 2026",
            "progress": 72,
        },
        {
            "name": "Agri-Tech Starter Kit",
            "category": "Livelihood",
            "status": "Ongoing",
            "start": "Feb 01, 2026",
            "end": "Jun 30, 2026",
            "progress": 38,
        },
        {
            "name": "Safe Water Initiative",
            "category": "Health",
            "status": "Proposed",
            "start": "Mar 12, 2026",
            "end": "Aug 18, 2026",
            "progress": 15,
        },
    ]

    recent_activities = [
        {
            "title": "Barangay mapping workshop",
            "location": "Brgy. San Miguel",
            "date": today.strftime("%b %d, %Y"),
            "participants": 64,
            "status": "Completed",
        },
        {
            "title": "Partner alignment meeting",
            "location": "Linkages Office",
            "date": today.strftime("%b %d, %Y"),
            "participants": 14,
            "status": "Completed",
        },
        {
            "title": "Baseline survey kick-off",
            "location": "Brgy. Poblacion",
            "date": today.strftime("%b %d, %Y"),
            "participants": 32,
            "status": "Scheduled",
        },
    ]

    sector_coverage = [
        {"name": "Education", "key": "education", "value": 32},
        {"name": "Health", "key": "health", "value": 24},
        {"name": "Livelihood", "key": "livelihood", "value": 18},
        {"name": "Environment", "key": "environment", "value": 14},
        {"name": "Governance", "key": "governance", "value": 12},
    ]

    return {
        "stats": stats,
        "projects": projects,
        "recent_activities": recent_activities,
        "sector_coverage": sector_coverage,
    }


def get_projects_data():
    return {
        "filters": ["Education", "Health", "Livelihood", "Environment", "Governance"],
        "projects": [
            {
                "name": "Community Literacy Boost",
                "category": "Education",
                "lead": "Prof. C. Reyes",
                "status": "Ongoing",
                "beneficiaries": 420,
                "timeline": "Jan - Apr 2026",
            },
            {
                "name": "Agri-Tech Starter Kit",
                "category": "Livelihood",
                "lead": "Dr. L. Santos",
                "status": "Ongoing",
                "beneficiaries": 210,
                "timeline": "Feb - Jun 2026",
            },
            {
                "name": "Safe Water Initiative",
                "category": "Health",
                "lead": "Dr. M. Dela Cruz",
                "status": "Proposed",
                "beneficiaries": 130,
                "timeline": "Mar - Aug 2026",
            },
            {
                "name": "Eco-Youth Engagement",
                "category": "Environment",
                "lead": "Ms. P. Valdez",
                "status": "Completed",
                "beneficiaries": 180,
                "timeline": "Sep - Dec 2025",
            },
        ],
    }


def get_beneficiaries_data():
    return {
        "segments": [
            {"label": "Women-led households", "value": 34},
            {"label": "Senior citizens", "value": 18},
            {"label": "Youth", "value": 26},
            {"label": "PWD", "value": 7},
            {"label": "Farmer groups", "value": 15},
        ],
        "communities": [
            {"name": "Brgy. San Miguel", "households": 220, "priority": "High"},
            {"name": "Brgy. Poblacion", "households": 180, "priority": "Medium"},
            {"name": "Brgy. Mabini", "households": 160, "priority": "Medium"},
            {"name": "Brgy. Bagong Silang", "households": 140, "priority": "Low"},
        ],
    }


def get_partners_data():
    return {
        "partners": [
            {
                "name": "Local Health Unit",
                "type": "Government",
                "status": "Active",
                "engagement": "High",
                "contribution": "Medical missions",
            },
            {
                "name": "AgriCoop Federation",
                "type": "NGO",
                "status": "Active",
                "engagement": "Medium",
                "contribution": "Inputs and training",
            },
            {
                "name": "Green Future Foundation",
                "type": "Private",
                "status": "Prospecting",
                "engagement": "Low",
                "contribution": "CSR funding",
            },
        ],
        "pipeline": [
            {"stage": "Prospecting", "count": 6},
            {"stage": "Negotiation", "count": 3},
            {"stage": "Active", "count": 18},
            {"stage": "Dormant", "count": 4},
        ],
    }


def get_activities_data():
    return {
        "upcoming": [
            {
                "title": "Data collection training",
                "date": "Feb 12, 2026",
                "location": "CES Hub",
                "owner": "Extension Unit",
                "status": "Scheduled",
            },
            {
                "title": "Partner alignment meeting",
                "date": "Feb 15, 2026",
                "location": "Board Room",
                "owner": "Linkages Unit",
                "status": "Scheduled",
            },
        ],
        "recent": [
            {
                "title": "Baseline survey kickoff",
                "date": "Feb 02, 2026",
                "location": "Brgy. Poblacion",
                "owner": "Research Unit",
                "status": "Completed",
            },
            {
                "title": "Impact narrative workshop",
                "date": "Jan 28, 2026",
                "location": "CES Hub",
                "owner": "QA Team",
                "status": "Completed",
            },
        ],
    }


def get_analytics_data():
    return {
        "kpis": [
            {"label": "Program Reach", "value": "1,260", "trend": "+4.1%"},
            {"label": "Partner Engagement", "value": "76%", "trend": "+2.2%"},
            {"label": "Completion Rate", "value": "68%", "trend": "+5.8%"},
            {"label": "Satisfaction", "value": "4.6/5", "trend": "+0.3"},
        ],
        "insights": [
            "Education projects have the highest retention rate in the last two quarters.",
            "Health initiatives show rising demand in coastal barangays.",
            "Livelihood programs benefit most when paired with partner micro-finance support.",
        ],
        "trend": [
            {"label": "Q1", "value": 62},
            {"label": "Q2", "value": 68},
            {"label": "Q3", "value": 71},
            {"label": "Q4", "value": 75},
        ],
    }


def get_reports_data():
    return {
        "reports": [
            {
                "title": "Accomplishment Report",
                "period": "Q4 2025",
                "status": "Generated",
                "owner": "QA Team",
            },
            {
                "title": "Impact Evaluation",
                "period": "CY 2025",
                "status": "In Review",
                "owner": "Research Unit",
            },
            {
                "title": "Partner Contribution",
                "period": "Jan 2026",
                "status": "Draft",
                "owner": "Linkages Unit",
            },
        ],
        "templates": [
            "Extension Activity Report",
            "Partner Commitment Tracker",
            "Beneficiary Outcome Matrix",
            "Accreditation Evidence Bundle",
        ],
    }


def get_ml_lab_data():
    return {
        "models": [
            {
                "name": "Program Reach Predictor",
                "type": "Regression",
                "status": "Prototype",
                "metric": "MAE 0.18",
            },
            {
                "name": "Beneficiary Segmentation",
                "type": "Clustering",
                "status": "Ready",
                "metric": "Silhouette 0.62",
            },
            {
                "name": "Partner Engagement Classifier",
                "type": "Classification",
                "status": "Training",
                "metric": "F1 0.74",
            },
        ],
        "pipelines": [
            {"name": "Data Cleaning", "status": "Operational"},
            {"name": "Feature Store", "status": "Design"},
            {"name": "Model Registry", "status": "Backlog"},
            {"name": "Monitoring", "status": "Planned"},
        ],
        "experiments": [
            {
                "name": "Impact Score v2",
                "owner": "ML Team",
                "status": "Running",
                "updated": "2 hours ago",
            },
            {
                "name": "Engagement uplift test",
                "owner": "Data Science",
                "status": "Completed",
                "updated": "Yesterday",
            },
        ],
    }
