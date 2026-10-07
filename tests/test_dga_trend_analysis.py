"""Tests for longitudinal DGA deterioration analysis."""

import unittest

from src.dga_trend_analysis import analyse_dga_history, latest_gases


class TestDGATrendAnalysis(unittest.TestCase):
    def observation(self, timestamp, h2, ch4, c2h6, c2h4, c2h2):
        return {
            "timestamp": timestamp,
            "gases": {
                "H2": h2,
                "CH4": ch4,
                "C2H6": c2h6,
                "C2H4": c2h4,
                "C2H2": c2h2,
            },
        }

    def test_rising_acetylene_is_detected(self):
        history = [
            self.observation("2026-01-01", 100, 30, 10, 20, 5),
            self.observation("2026-02-01", 110, 32, 10, 24, 12),
            self.observation("2026-03-01", 120, 34, 10, 30, 30),
        ]
        result = analyse_dga_history(history)
        self.assertEqual(result.dominant_rising_gas, "C2H2")
        self.assertGreater(result.trends_ppm_per_month["C2H2"], 0)
        self.assertGreater(result.acceleration_ppm_per_month2["C2H2"], 0)
        self.assertIn(result.status, {"DETERIORATING", "RAPID DETERIORATION"})

    def test_declining_history_is_stable_or_declining(self):
        history = [
            self.observation("2026-01-01", 100, 80, 40, 30, 10),
            self.observation("2026-02-01", 90, 70, 35, 25, 8),
        ]
        result = analyse_dga_history(history)
        self.assertEqual(result.status, "STABLE/DECLINING")
        self.assertIsNone(result.dominant_rising_gas)

    def test_unsorted_history_is_sorted_by_timestamp(self):
        history = [
            self.observation("2026-03-01", 150, 60, 20, 40, 15),
            self.observation("2026-01-01", 100, 40, 20, 20, 5),
        ]
        result = analyse_dga_history(history)
        self.assertGreater(result.trends_ppm_per_month["H2"], 0)

    def test_latest_gases_returns_latest_sample(self):
        history = [
            self.observation("2026-01-01", 100, 40, 20, 20, 5),
            self.observation("2026-03-01", 150, 60, 20, 40, 15),
        ]
        gases = latest_gases(history)
        self.assertEqual(gases["H2"], 150.0)
        self.assertEqual(gases["C2H2"], 15.0)

    def test_single_observation_is_rejected(self):
        history = [
            self.observation("2026-01-01", 100, 40, 20, 20, 5)
        ]
        with self.assertRaises(ValueError):
            analyse_dga_history(history)

    def test_duplicate_timestamps_are_rejected(self):
        history = [
            self.observation("2026-01-01", 100, 40, 20, 20, 5),
            self.observation("2026-01-01", 120, 50, 20, 25, 8),
        ]
        with self.assertRaises(ValueError):
            analyse_dga_history(history)


if __name__ == "__main__":
    unittest.main()
