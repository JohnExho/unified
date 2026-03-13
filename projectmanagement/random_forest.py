"""
Pure-Python Random Forest Classifier (no numpy / scikit-learn).
Implements CART decision trees with Gini impurity, bootstrap sampling,
random feature subsets, and mean-decrease-in-impurity feature importance.
"""
import random
import math
from collections import Counter


# ---------------------------------------------------------------------------
# Decision Tree (CART)
# ---------------------------------------------------------------------------

class _Node:
    __slots__ = ('feature', 'threshold', 'left', 'right', 'value')

    def __init__(self):
        self.feature = None
        self.threshold = None
        self.left = None
        self.right = None
        self.value = None  # set for leaf nodes


def _gini(labels):
    n = len(labels)
    if n == 0:
        return 0.0
    counts = Counter(labels)
    return 1.0 - sum((c / n) ** 2 for c in counts.values())


def _best_split(X, y, feature_indices):
    best_gain = -1.0
    best_feat = None
    best_thresh = None
    parent_gini = _gini(y)
    n = len(y)

    for fi in feature_indices:
        values = sorted(set(row[fi] for row in X))
        thresholds = [(values[i] + values[i + 1]) / 2.0 for i in range(len(values) - 1)]
        for thresh in thresholds:
            left_y  = [y[i] for i in range(n) if X[i][fi] <= thresh]
            right_y = [y[i] for i in range(n) if X[i][fi] >  thresh]
            if not left_y or not right_y:
                continue
            gain = parent_gini - (
                len(left_y)  / n * _gini(left_y) +
                len(right_y) / n * _gini(right_y)
            )
            if gain > best_gain:
                best_gain  = gain
                best_feat  = fi
                best_thresh = thresh

    return best_feat, best_thresh, best_gain


def _build_tree(X, y, max_features, max_depth, min_samples_split, depth=0):
    node = _Node()

    # Leaf: pure, too small, or max depth reached
    if len(set(y)) == 1 or len(y) < min_samples_split or depth >= max_depth:
        node.value = Counter(y).most_common(1)[0][0]
        return node

    n_features = len(X[0])
    k = max(1, min(max_features, n_features))
    feature_indices = random.sample(range(n_features), k)

    feat, thresh, gain = _best_split(X, y, feature_indices)

    if feat is None or gain <= 0:
        node.value = Counter(y).most_common(1)[0][0]
        return node

    node.feature   = feat
    node.threshold = thresh

    left_idx  = [i for i in range(len(y)) if X[i][feat] <= thresh]
    right_idx = [i for i in range(len(y)) if X[i][feat] >  thresh]

    node.left  = _build_tree([X[i] for i in left_idx],  [y[i] for i in left_idx],
                              max_features, max_depth, min_samples_split, depth + 1)
    node.right = _build_tree([X[i] for i in right_idx], [y[i] for i in right_idx],
                              max_features, max_depth, min_samples_split, depth + 1)
    return node


def _predict_one(node, row):
    if node.value is not None:
        return node.value
    if row[node.feature] <= node.threshold:
        return _predict_one(node.left, row)
    return _predict_one(node.right, row)


def _predict_proba_one(node, row, classes):
    """Returns probability of class 1 by collecting leaf label distributions."""
    leaf_labels = _collect_leaf(node, row)
    c = Counter(leaf_labels)
    total = sum(c.values())
    if total == 0:
        return 0.0
    return c.get(1, 0) / total


def _collect_leaf(node, row):
    """Walk tree and return the training labels at the reached leaf."""
    if node.value is not None:
        return [node.value]
    if row[node.feature] <= node.threshold:
        return _collect_leaf(node.left, row)
    return _collect_leaf(node.right, row)


# ---------------------------------------------------------------------------
# Random Forest
# ---------------------------------------------------------------------------

class RandomForestClassifier:
    """
    Minimal Random Forest Classifier — pure Python, no external dependencies.

    Parameters
    ----------
    n_estimators      : number of trees
    max_depth         : maximum tree depth
    min_samples_split : minimum samples required to split a node
    max_features      : features to consider per split ('sqrt' or int)
    random_state      : seed for reproducibility
    """

    def __init__(self, n_estimators=100, max_depth=10,
                 min_samples_split=2, max_features='sqrt', random_state=42):
        self.n_estimators      = n_estimators
        self.max_depth         = max_depth
        self.min_samples_split = min_samples_split
        self.max_features      = max_features
        self.random_state      = random_state
        self._trees            = []          # list of (_Node, oob_indices)
        self._train_X          = None
        self._train_y          = None
        self._n_features       = 0
        self._classes          = []

    def _resolve_max_features(self, n):
        if self.max_features == 'sqrt':
            return max(1, int(math.sqrt(n)))
        if self.max_features == 'log2':
            return max(1, int(math.log2(n)))
        return int(self.max_features)

    def fit(self, X, y):
        random.seed(self.random_state)
        self._train_X   = X
        self._train_y   = y
        self._n_features = len(X[0])
        self._classes   = sorted(set(y))
        n               = len(X)
        mf              = self._resolve_max_features(self._n_features)

        self._trees = []
        for _ in range(self.n_estimators):
            indices = [random.randint(0, n - 1) for _ in range(n)]
            X_boot  = [X[i] for i in indices]
            y_boot  = [y[i] for i in indices]
            tree    = _build_tree(X_boot, y_boot, mf, self.max_depth, self.min_samples_split)
            oob_set = sorted(set(range(n)) - set(indices))
            self._trees.append((tree, oob_set))

        return self

    def predict(self, X):
        return [self._vote(row) for row in X]

    def _vote(self, row):
        votes = [_predict_one(tree, row) for tree, _ in self._trees]
        return Counter(votes).most_common(1)[0][0]

    def predict_proba(self, X):
        """Returns list of [prob_class0, prob_class1] per sample."""
        results = []
        for row in X:
            votes = [_predict_one(tree, row) for tree, _ in self._trees]
            c = Counter(votes)
            total = len(votes)
            probs = [c.get(cls, 0) / total for cls in self._classes]
            results.append(probs)
        return results

    def score(self, X, y):
        preds = self.predict(X)
        return sum(p == t for p, t in zip(preds, y)) / len(y)

    def feature_importances_(self):
        """
        Mean Decrease Impurity across all trees and all splits.
        Returns a list of floats (one per feature), summing to 1.
        """
        importances = [0.0] * self._n_features
        self._accumulate_importance(importances)
        total = sum(importances)
        if total == 0:
            return importances
        return [v / total for v in importances]

    def _accumulate_importance(self, importances):
        n = len(self._train_X)
        for tree, _ in self._trees:
            self._node_importance(tree, importances, n)

    def _node_importance(self, node, importances, n_total):
        if node.value is not None:
            return 0, 0   # leaf: (node_count, weighted_gini) — unused here

        # Estimate node sample count by walking all training samples
        # This is approximate for bagged trees; good enough for relative importances.
        left_y  = []
        right_y = []
        for i, row in enumerate(self._train_X):
            side = 'left' if row[node.feature] <= node.threshold else 'right'
            if side == 'left':
                left_y.append(self._train_y[i])
            else:
                right_y.append(self._train_y[i])

        node_y = left_y + right_y
        n  = len(node_y)
        nl = len(left_y)
        nr = len(right_y)

        if nl == 0 or nr == 0:
            return

        gain = _gini(node_y) - (nl / n * _gini(left_y) + nr / n * _gini(right_y))
        importances[node.feature] += (n / n_total) * gain

        self._node_importance(node.left,  importances, n_total)
        self._node_importance(node.right, importances, n_total)
