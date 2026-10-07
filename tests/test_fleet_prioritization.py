"""Tests for fleet-level transformer maintenance prioritisation."""

import unittest

from src.fleet_prioritization import assess_fleet, fleet_summary


def obs(timestamp, h2, ch4, c2h6, c2h4, c2h2):
    return {
        "timestamp": timestamp,
        "gases": {
            "H2": h2, "CH4": ch4, "C2H6": c2h6,
            "C2H4": c2h4, "C2H2": c2h2,
        },
    }


class TestFleetPrioritization(unittest.TestCase):
    def setUp(self):
        self.assets = [
            {
                "transformer_id": "TR-HEALTHY",
                "observations": [
                    obs("2026-01-01", 20, 8, 4, 2, 0),
                    obs("2026-03-01", 20, 8, 4, 2, 0),
                ],
                "diagnostic_result": {
                    "diagnosis": "Normal", "confidence": 0.96
                },
            },
            {
                "transformer_id": "TR-THERMAL",
                "observations": [
                    obs("2026-01-01", 70, 350, 100, 180, 4),
                    obs("2026-03-01", 80, 500, 100, 300, 5),
                ],
                "diagnostic_result": {
                    "diagnosis": "T2", "confidence": 0.89
                },
            },
            {
                "transformer_id": "TR-ARC",
                "observations": [
                    obs("2026-01-01", 250, 30, 10, 80, 80),
                    obs("2026-02-01", 350, 40, 10, 130, 180),
                    obs("2026-03-01", 500, 50, 10, 200, 400),
                ],
                "diagnostic_result": {
                    "diagnosis": "D2", "confidence": 0.93
                },
            },
        ]

    def test_critical_arc_transformer_is_ranked_first(self):
        ranked = assess_fleet(self.assets)
        self.assertEqual(ranked[0].transformer_id, "TR-ARC")
        self.assertEqual(ranked[0].rank, 1)
        self.assertEqual(ranked[-1].transformer_id, "TR-HEALTHY")

    def test_priority_scores_descend(self):
        ranked = assess_fleet(self.assets)
        scores = [item.priority_score for item in ranked]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_summary_counts_fleet_condition(self):
        ranked = assess_fleet(self.assets)
        summary = fleet_summary(ranked)
        self.assertEqual(summary["total_transformers"], 3)
        self.assertEqual(summary["highest_priority_transformer"], "TR-ARC")
        self.assertGreaterEqual(summary["critical"], 1)
        self.assertGreaterEqual(summary["low"], 1)

    def test_missing_asset_input_is_rejected(self):
        broken = [{
            "transformer_id": "TR-X",
            "observations": self.assets[0]["observations"],
        }]
        with self.assertRaises(KeyError):
            assess_fleet(broken)

    def test_empty_fleet_has_empty_summary(self):
        summary = fleet_summary([])
        self.assertEqual(summary["total_transformers"], 0)
        self.assertIsNone(summary["highest_priority_transformer"])


if __name__ == "__main__":
    unittest.main()
