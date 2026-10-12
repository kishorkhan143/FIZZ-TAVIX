"""
Train the lightweight model.   Usage:  python -m ml.train        (from backend/)

Model stack (all scikit-learn, CPU, trains in seconds, artifact < 1 MB)
  1. RandomForest (80 trees, depth 10)  -> multi-class threat type + probabilities
  2. IsolationForest (trained on NORMAL only) -> "unseen pattern" anomaly score
"""
import json
import os
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

from ml.features import extract, FEATURE_NAMES
from ml.synth_data import generate, LABELS

HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(HERE, "model.joblib")
REPORT_PATH = os.path.join(HERE, "training_report.json")


def build_dataset(n_per_class, seed):
    X, y = [], []
    for recs, label, key in generate(n_per_class, seed):
        feats, wins = extract(recs)
        # pick the window that holds the attack/entity of interest (largest relevant window)
        best, best_score = None, -1
        for f, w in zip(feats, wins):
            match = (w[0]["ip"] == key[1]) and (key[0] is None or w[0]["user"] == key[0])
            score = (1000 if match else 0) + len(w)
            if score > best_score:
                best, best_score = f, score
        X.append(best); y.append(label)
    return np.array(X), np.array(y)


def main():
    X, y = build_dataset(n_per_class=700, seed=42)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, stratify=y, random_state=1)

    clf = RandomForestClassifier(n_estimators=80, max_depth=10, min_samples_leaf=2,
                                 class_weight="balanced", random_state=0, n_jobs=-1)
    clf.fit(Xtr, ytr)
    pred = clf.predict(Xte)
    rep = classification_report(yte, pred, target_names=LABELS, output_dict=True, digits=3)
    print(classification_report(yte, pred, target_names=LABELS, digits=3))
    print("confusion matrix (rows=true):\n", confusion_matrix(yte, pred))

    iso = IsolationForest(n_estimators=100, contamination=0.02, random_state=0)
    iso.fit(Xtr[ytr == 0])
    # calibrate anomaly score -> 0..1 using normal-train distribution
    raw = -iso.score_samples(Xtr[ytr == 0])
    lo, hi = float(np.percentile(raw, 5)), float(np.percentile(raw, 99.5))

    clf.fit(X, y)  # final fit on all data
    joblib.dump({"clf": clf, "iso": iso, "iso_range": (lo, hi),
                 "labels": LABELS, "features": FEATURE_NAMES},
                MODEL_PATH, compress=3)

    imp = sorted(zip(FEATURE_NAMES, clf.feature_importances_), key=lambda t: -t[1])[:8]
    with open(REPORT_PATH, "w") as f:
        json.dump({"holdout": rep, "top_features": [(n, round(float(v), 4)) for n, v in imp],
                   "train_samples": int(len(y)),
                   "note": "Metrics are on SYNTHETIC data and are optimistic."}, f, indent=2)
    print("top features:", imp)
    print(f"saved {MODEL_PATH} ({os.path.getsize(MODEL_PATH)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
