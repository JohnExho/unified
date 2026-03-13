"""
Pure-Python Linear SVM (Support Vector Machine) — One-vs-Rest multiclass.
No external dependencies (no NumPy, no scikit-learn).

Algorithm
---------
- Binary linear SVM with hinge loss + L2 regularisation, trained via SGD.
- OvR (One-vs-Rest) wrapper for multiclass classification.
- Feature vectors are z-score normalised per fit().

Usage
-----
    from .svm_classifier import OvRLinearSVM

    model = OvRLinearSVM(C=1.0, lr=0.01, epochs=200)
    model.fit(X_train, y_train)          # X: list[list[float]], y: list[str]
    labels = model.predict(X_test)       # list[str]
    weights = model.feature_weights()    # dict {class: [float, ...]}
"""


# ---------------------------------------------------------------------------
# Feature normalisation helpers
# ---------------------------------------------------------------------------

def _fit_scaler(X):
    """Return per-feature (mu, std) from a list-of-lists matrix."""
    n_feats = len(X[0])
    stats = []
    for j in range(n_feats):
        col = [row[j] for row in X]
        mu = sum(col) / len(col)
        var = sum((v - mu) ** 2 for v in col) / max(len(col) - 1, 1)
        std = var ** 0.5 if var > 1e-9 else 1.0
        stats.append((mu, std))
    return stats


def _apply_scaler(X, stats):
    return [[(row[j] - stats[j][0]) / stats[j][1] for j in range(len(row))] for row in X]


# ---------------------------------------------------------------------------
# Binary Linear SVM
# ---------------------------------------------------------------------------

class _LinearSVM:
    """
    Binary linear SVM (labels +1 / -1).
    Trained with Pegasos-style SGD (hinge loss + L2).

    Parameters
    ----------
    C       : regularisation strength (higher = less regularisation)
    lr      : initial learning rate
    epochs  : passes over the dataset
    """

    def __init__(self, C=1.0, lr=0.01, epochs=200):
        self.C      = C
        self.lr     = lr
        self.epochs = epochs
        self.w      = []
        self.b      = 0.0

    def fit(self, Xn, y_bin):
        """Train on normalised Xn with binary labels ±1."""
        n, d  = len(Xn), len(Xn[0])
        self.w = [0.0] * d
        self.b = 0.0

        for ep in range(self.epochs):
            lr_t = self.lr / (1.0 + ep * 0.01)   # mild decay
            for i in range(n):
                xi   = Xn[i]
                yi   = y_bin[i]
                dot  = sum(self.w[j] * xi[j] for j in range(d)) + self.b
                margin = yi * dot
                if margin < 1.0:
                    # Subgradient of hinge + L2
                    for j in range(d):
                        self.w[j] = (1.0 - lr_t) * self.w[j] + lr_t * self.C * yi * xi[j]
                    self.b += lr_t * self.C * yi
                else:
                    for j in range(d):
                        self.w[j] *= (1.0 - lr_t)

    def decision(self, Xn):
        """Raw margin score for each sample."""
        return [sum(self.w[j] * x[j] for j in range(len(x))) + self.b for x in Xn]


# ---------------------------------------------------------------------------
# One-vs-Rest multiclass SVM
# ---------------------------------------------------------------------------

class OvRLinearSVM:
    """
    One-vs-Rest multiclass linear SVM.

    Parameters
    ----------
    C       : regularisation strength
    lr      : learning rate
    epochs  : SGD epochs per binary classifier
    """

    def __init__(self, C=1.0, lr=0.01, epochs=200):
        self.C        = C
        self.lr       = lr
        self.epochs   = epochs
        self.classes_ = []
        self._clfs    = {}
        self._scaler  = None

    # ------------------------------------------------------------------
    def fit(self, X, y):
        """
        X : list[list[float]] — feature matrix
        y : list[str]         — class labels
        """
        self._scaler  = _fit_scaler(X)
        Xn            = _apply_scaler(X, self._scaler)
        self.classes_ = sorted(set(y))

        for cls in self.classes_:
            y_bin = [1 if yi == cls else -1 for yi in y]
            clf   = _LinearSVM(C=self.C, lr=self.lr, epochs=self.epochs)
            clf.fit(Xn, y_bin)
            self._clfs[cls] = clf
        return self

    # ------------------------------------------------------------------
    def _scores(self, X):
        """Return per-class margin scores for all samples."""
        Xn = _apply_scaler(X, self._scaler)
        return {cls: clf.decision(Xn) for cls, clf in self._clfs.items()}

    # ------------------------------------------------------------------
    def predict(self, X):
        """Return predicted class label for each sample."""
        scores = self._scores(X)
        n = len(X)
        return [max(self.classes_, key=lambda c: scores[c][i]) for i in range(n)]

    # ------------------------------------------------------------------
    def confidence(self, X):
        """
        Per-sample confidence: winning margin as a percentage of the
        sum of absolute margins across all classes (softmax-free proxy).
        Returns list of (predicted_class, confidence_pct).
        """
        scores = self._scores(X)
        n      = len(X)
        out    = []
        for i in range(n):
            class_scores = {c: scores[c][i] for c in self.classes_}
            pred  = max(class_scores, key=class_scores.get)
            total = sum(abs(v) for v in class_scores.values()) or 1.0
            pct   = round(max(0.0, class_scores[pred]) / total * 100, 1)
            out.append((pred, pct))
        return out

    # ------------------------------------------------------------------
    def feature_weights(self, feature_names=None):
        """
        Return per-feature importance as the mean absolute weight
        across all binary classifiers (normalised to 100).

        Returns list of dicts: [{name, importance}, ...]
        """
        if not self._clfs:
            return []

        d   = len(next(iter(self._clfs.values())).w)
        agg = [0.0] * d
        for clf in self._clfs.values():
            for j in range(d):
                agg[j] += abs(clf.w[j])

        total = sum(agg) or 1.0
        names = feature_names or [f"Feature {j+1}" for j in range(d)]
        return [
            {'name': names[j], 'importance': round(agg[j] / total * 100, 1)}
            for j in range(d)
        ]

    # ------------------------------------------------------------------
    def accuracy(self, X, y):
        preds = self.predict(X)
        return round(sum(p == t for p, t in zip(preds, y)) / max(len(y), 1) * 100, 1)
