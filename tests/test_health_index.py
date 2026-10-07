"""Tests for the predictive-maintenance transformer health index extension."""

import unittest

from src.health_index import (
    assess_transformer_health,
    calculate_gas_trends,
)


class TestTransformerHealthIndex(unittest.TestCase):
    def setUp(self):
        self.normal_gases = {
            "H2": 20.0,
            "CH4": 8.0,
            "C2H6": 4.0,
            "C2H4": 2.0,
            "C2H2": 0.0,
        }

    def test_healthy_high_confidence_transformer_is_low_risk(self):
        result = assess_transformer_health(
            self.normal_gases, diagnosis="Normal", confidence=0.95
        )
        self.assertGreaterEqual(result.health_index, 95.0)
        self.assertEqual(result.risk_category, "LOW")
        self.assertEqual(
            result.maintenance_priority,
            "Continue routine condition monitoring",
        )

    def test_d2_fault_is_high_risk_without_trend_history(self):
        gases = {
            "H2": 500.0,
            "CH4": 50.0,
            "C2H6": 10.0,
            "C2H4": 200.0,
            "C2H2": 400.0,
        }
        result = assess_transformer_health(
            gases, diagnosis="D2", confidence=0.95
        )
        self.assertGreaterEqual(result.risk_score, 50.0)
        self.assertIn(result.risk_category, {"HIGH", "CRITICAL"})

    def test_t3_with_rising_gases_reaches_critical_band(self):
        gases = {
            "H2": 120.0,
            "CH4": 900.0,
            "C2H6": 120.0,
            "C2H4": 700.0,
            "C2H2": 15.0,
        }
        trends = {
            "H2": 30.0,
            "CH4": 225.0,
            "C2H6": 30.0,
            "C2H4": 175.0,
            "C2H2": 4.0,
        }
        result = assess_transformer_health(
            gases, diagnosis="T3", confidence=0.90,
            trends_ppm_per_month=trends,
        )
        self.assertEqual(result.risk_category, "CRITICAL")
        self.assertLessEqual(result.health_index, 25.0)

    def test_rising_acetylene_increases_risk(self):
        gases = {
            "H2": 300.0,
            "CH4": 30.0,
            "C2H6": 10.0,
            "C2H4": 20.0,
            "C2H2": 50.0,
        }
        stable = {gas: 0.0 for gas in gases}
        rising = {gas: 0.0 for gas in gases}
        rising["C2H2"] = 12.5

        stable_result = assess_transformer_health(
            gases, "D1", 0.90, stable
        )
        rising_result = assess_transformer_health(
            gases, "D1", 0.90, rising
        )
        self.assertGreater(rising_result.risk_score, stable_result.risk_score)
        self.assertTrue(
            any("C2H2" in reason for reason in rising_result.explanation)
        )

    def test_low_confidence_adds_uncertainty_risk(self):
        high_conf = assess_transformer_health(
            self.normal_gases, "Normal", 0.95
        )
        low_conf = assess_transformer_health(
            self.normal_gases, "Normal", 0.40
        )
        self.assertGreater(low_conf.risk_score, high_conf.risk_score)
        self.assertGreater(
            low_conf.uncertainty_penalty, high_conf.uncertainty_penalty
        )

    def test_calculate_monthly_gas_trends(self):
        previous = {
            "H2": 100.0, "CH4": 50.0, "C2H6": 20.0,
            "C2H4": 30.0, "C2H2": 5.0,
        }
        current = {
            "H2": 140.0, "CH4": 70.0, "C2H6": 18.0,
            "C2H4": 50.0, "C2H2": 9.0,
        }
        trends = calculate_gas_trends(current, previous, months_between=2)
        self.assertAlmostEqual(trends["H2"], 20.0)
        self.assertAlmostEqual(trends["CH4"], 10.0)
        self.assertAlmostEqual(trends["C2H6"], -1.0)
        self.assertAlmostEqual(trends["C2H4"], 10.0)
        self.assertAlmostEqual(trends["C2H2"], 2.0)

    def test_invalid_time_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_gas_trends(
                self.normal_gases, self.normal_gases, months_between=0
            )

    def test_negative_gas_value_is_rejected(self):
        gases = dict(self.normal_gases)
        gases["H2"] = -1.0
        with self.assertRaises(ValueError):
            assess_transformer_health(gases, "Normal", 0.90)

    def test_missing_gas_is_rejected(self):
        gases = dict(self.normal_gases)
        gases.pop("C2H2")
        with self.assertRaises(KeyError):
            assess_transformer_health(gases, "Normal", 0.90)

    def test_unknown_diagnosis_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_transformer_health(
                self.normal_gases, "UNKNOWN", 0.90
            )


if __name__ == "__main__":
    unittest.main()
