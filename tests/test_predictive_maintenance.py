"""Integration tests for the predictive-maintenance engine."""

import unittest

from src.predictive_maintenance import assess_history, assess_with_model


def obs(timestamp, h2, ch4, c2h6, c2h4, c2h2):
    return {
        "timestamp": timestamp,
        "gases": {
            "H2": h2, "CH4": ch4, "C2H6": c2h6,
            "C2H4": c2h4, "C2H2": c2h2,
        },
    }


class TestPredictiveMaintenance(unittest.TestCase):
    def test_critical_discharge_history_produces_actionable_result(self):
        history = [
            obs("2026-01-01", 250, 30, 10, 80, 80),
            obs("2026-02-01", 350, 40, 10, 130, 180),
            obs("2026-03-01", 500, 50, 10, 200, 400),
        ]
        result = assess_history(
            "TR-017", history, {"diagnosis": "D2", "confidence": 0.91}
        )
        self.assertEqual(result.transformer_id, "TR-017")
        self.assertEqual(result.diagnosis, "D2")
        self.assertEqual(result.risk_category, "CRITICAL")
        self.assertIn("Immediate engineering investigation", result.recommendation)
        self.assertIsNotNone(result.dominant_rising_gas)

    def test_normal_stable_transformer_remains_low_risk(self):
        history = [
            obs("2026-01-01", 20, 8, 4, 2, 0),
            obs("2026-03-01", 20, 8, 4, 2, 0),
        ]
        result = assess_history(
            "TR-001", history, {"diagnosis": "Normal", "confidence": 0.96}
        )
        self.assertEqual(result.risk_category, "LOW")
        self.assertEqual(result.trend_status, "STABLE/DECLINING")
        self.assertEqual(result.recommendation, "Continue routine condition monitoring.")

    def test_model_adapter_uses_latest_sample(self):
        history = [
            obs("2026-01-01", 20, 8, 4, 2, 0),
            obs("2026-02-01", 60, 300, 150, 50, 2),
        ]
        captured = {}

        def diagnose(gases):
            captured.update(gases)
            return {"diagnosis": "T1", "confidence": 0.88}

        result = assess_with_model("TR-009", history, diagnose)
        self.assertEqual(captured["CH4"], 300.0)
        self.assertEqual(result.diagnosis, "T1")

    def test_missing_diagnostic_fields_are_rejected(self):
        history = [
            obs("2026-01-01", 20, 8, 4, 2, 0),
            obs("2026-02-01", 21, 9, 4, 2, 0),
        ]
        with self.assertRaises(KeyError):
            assess_history("TR-001", history, {"diagnosis": "Normal"})


if __name__ == "__main__":
    unittest.main()
