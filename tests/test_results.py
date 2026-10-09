"""Lightweight post-pipeline tests; run after python run_pipeline.py."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class OutputQualityTests(unittest.TestCase):
    def read(self, name):
        with (ROOT / "results" / name).open(encoding="utf-8") as fh:
            return json.load(fh)

    def test_quality_gate_flags(self):
        flags = self.read("quality_checks.json")
        self.assertTrue(flags, "Quality output must contain checks")
        self.assertTrue(all(flags.values()), str(flags))

    def test_expected_simulation_grain(self):
        metrics = self.read("kpi_summary.json")
        self.assertEqual(int(metrics["summary"]["total_users"]), 10000)
        self.assertEqual(int(metrics["summary"]["total_watch_sessions"]), 160000)
        self.assertEqual(int(metrics["recommendation_funnel"]["impressions"]), 120000)

    def test_model_holdout_bounds(self):
        model = self.read("churn_model_metrics.json")
        self.assertEqual(model["test_rows"], 2500)
        self.assertGreaterEqual(model["roc_auc"], 0.5)
        self.assertLessEqual(model["roc_auc"], 1.0)

if __name__ == "__main__":
    unittest.main()
