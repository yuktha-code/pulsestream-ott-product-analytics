from __future__ import annotations

import json
import sqlite3
from pathlib import Path
import pandas as pd

EXPECTED_ROWS = {
    "users": 10_000,
    "content": 300,
    "subscriptions": 10_000,
    "devices": 10_000,
    "watch_sessions": 160_000,
    "search_events": 45_000,
    "recommendation_impressions": 120_000,
    "support_events": 8_000,
}


def run_quality_checks(db_path="data/pulsestream.db"):
    retention = pd.read_csv("results/d1_d7_d30_rolling_retention.csv")
    rates = retention["rolling_retention_rate"].tolist()

    checks = {
        "retention_monotonic": bool(rates[0] >= rates[1] >= rates[2]),
        "retention_not_all_one": bool(any(r < 0.999 for r in rates)),
        "retention_nonnegative": bool(all(r >= 0 for r in rates)),
        "retention_at_most_one": bool(all(r <= 1 for r in rates)),
    }

    churn_path = Path("results/churn_model_metrics.json")
    if churn_path.exists():
        churn = json.loads(churn_path.read_text(encoding="utf-8"))
        checks["churn_auc_valid"] = bool(0.5 <= churn["roc_auc"] <= 1.0)
        checks["churn_test_rows_positive"] = bool(churn["test_rows"] > 0)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    fk_violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    checks["foreign_keys_valid"] = len(fk_violations) == 0

    for table, expected in EXPECTED_ROWS.items():
        actual = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        checks[f"row_count_{table}"] = actual == expected

    key_specs = {
        "users": "user_id",
        "content": "content_id",
        "subscriptions": "subscription_id",
        "devices": "device_id",
        "watch_sessions": "session_id",
        "search_events": "search_id",
        "recommendation_impressions": "impression_id",
        "payments": "payment_id",
        "support_events": "support_event_id",
    }
    for table, key in key_specs.items():
        total, unique = conn.execute(
            f"SELECT COUNT(*), COUNT(DISTINCT {key}) FROM {table}"
        ).fetchone()
        checks[f"unique_key_{table}"] = total == unique

    conn.close()

    Path("results").mkdir(exist_ok=True)
    Path("results/quality_checks.json").write_text(
        json.dumps(checks, indent=2), encoding="utf-8"
    )

    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise RuntimeError(f"Quality checks failed: {failed}")

    print("QUALITY CHECKS PASSED")
    for k, v in checks.items():
        print(f"  {k}: {v}")
    return checks


if __name__ == "__main__":
    run_quality_checks()
