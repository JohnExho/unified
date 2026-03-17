from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


MODEL_DIR = Path(__file__).resolve().parent / "ml_models"
METHOD_MODEL_PATH = MODEL_DIR / "research_method_classifier.joblib"
STATUS_MODEL_PATH = MODEL_DIR / "publication_status_classifier.joblib"
SCOPE_MODEL_PATH = MODEL_DIR / "publication_scope_classifier.joblib"


# Seed labels to bootstrap models even when the database has little/no history.
TRAINING_SAMPLES = [
    {
        "title": "Action research for classroom intervention",
        "description": "Iterative cycle with plan act observe reflect in local schools.",
        "research_method": "action_research",
        "publication_status": "for_publication",
        "publication_scope": "local",
    },
    {
        "title": "Text mining of institutional repository abstracts",
        "description": "NLP keyword extraction and topic modeling for publication indexing.",
        "research_method": "text_mining",
        "publication_status": "draft",
        "publication_scope": "international",
    },
    {
        "title": "Experimental evaluation of blended learning outcomes",
        "description": "Controlled experiment and statistical testing for journal submission.",
        "research_method": "experimental",
        "publication_status": "for_publication",
        "publication_scope": "international",
    },
    {
        "title": "Case study on local library digitization",
        "description": "Single-site investigation focused on local implementation results.",
        "research_method": "case_study",
        "publication_status": "draft",
        "publication_scope": "local",
    },
    {
        "title": "Mixed methods study for education policy",
        "description": "Survey plus interviews prepared for publication and dissemination.",
        "research_method": "mixed_methods",
        "publication_status": "for_publication",
        "publication_scope": "international",
    },
    {
        "title": "Published action research on community engagement",
        "description": "Already accepted and published in a local journal.",
        "research_method": "action_research",
        "publication_status": "published",
        "publication_scope": "local",
    },
    {
        "title": "Published NLP document classifier for scholarly works",
        "description": "International conference paper on automatic tagging.",
        "research_method": "text_mining",
        "publication_status": "published",
        "publication_scope": "international",
    },
    {
        "title": "Repository profiling study",
        "description": "Profiling and metadata cleanup prior to publication release.",
        "research_method": "other",
        "publication_status": "draft",
        "publication_scope": "local",
    },
]


def _record_text(title, description):
    return f"{title or ''} {description or ''}".strip().lower()


def _build_pipeline():
    return Pipeline(
        [
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
            ("clf", LogisticRegression(max_iter=1000, random_state=42)),
        ]
    )


def _train_model(label_key):
    texts = [_record_text(s["title"], s["description"]) for s in TRAINING_SAMPLES]
    labels = [s[label_key] for s in TRAINING_SAMPLES]
    model = _build_pipeline()
    model.fit(texts, labels)
    return model


def _load_or_train(model_path, label_key):
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if model_path.exists():
        return joblib.load(model_path)

    model = _train_model(label_key)
    joblib.dump(model, model_path)
    return model


def predict_research_fields(title, description):
    text = _record_text(title, description)
    if not text:
        return {
            "research_method": "action_research",
            "publication_status": "draft",
            "publication_scope": "local",
        }

    try:
        method_model = _load_or_train(METHOD_MODEL_PATH, "research_method")
        status_model = _load_or_train(STATUS_MODEL_PATH, "publication_status")
        scope_model = _load_or_train(SCOPE_MODEL_PATH, "publication_scope")

        method_pred = str(method_model.predict([text])[0]).strip()
        status_pred = str(status_model.predict([text])[0]).strip()
        scope_pred = str(scope_model.predict([text])[0]).strip()

        return {
            "research_method": method_pred,
            "publication_status": status_pred,
            "publication_scope": scope_pred,
        }
    except Exception:
        # Safe fallback if model files or sklearn pipeline fail at runtime.
        return {
            "research_method": "text_mining" if "nlp" in text or "text mining" in text else "action_research",
            "publication_status": "for_publication" if "publication" in text or "journal" in text else "draft",
            "publication_scope": "international" if "international" in text or "conference" in text else "local",
        }
