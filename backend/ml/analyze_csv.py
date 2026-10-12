"""CLI replay:  python -m ml.analyze_csv ../sample_security_events.csv"""
import csv, sys
from csv_analytics.column_detector import ColumnDetector
from csv_analytics.normalizer import DataNormalizer
from ml.predictor import predict


def load(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    mapping, unmapped = ColumnDetector.detect_columns(list(rows[0].keys()))
    recs = []
    for i, r in enumerate(rows, start=2):
        v, _q = DataNormalizer.normalize_record(i, r, mapping, unmapped)
        if v:
            recs.append(v)
    return recs


if __name__ == "__main__":
    recs = load(sys.argv[1])
    for p in predict(recs):
        tag = "ALERT" if p["prediction"] != "NORMAL" else "ok   "
        print(f"{tag} {p['prediction']:<18} risk={p['ml_risk']:>5} user={p['user']:<10} ip={p['ip']:<15} "
              f"events={p['event_ids']} fails={p['evidence']['failures']}")
