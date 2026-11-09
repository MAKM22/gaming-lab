import unittest
from datetime import datetime, timedelta, timezone
from math import hypot
from statistics import NormalDist

from power_auditor import Channel, UncertaintyType, audit_power_state

NOW = datetime(2026, 11, 9, tzinfo=timezone.utc)


def sample(power, uncertainty=10, timestamp=NOW):
    return Channel(timestamp, power, 1.0, uncertainty)


def audit(input_power, output_power, *, uncertainty=10, kind=UncertaintyType.CONSERVATIVE,
          timestamp=NOW, **overrides):
    args = dict(workload="idle", boundary="converter", input_channel=sample(input_power, uncertainty),
                rails={"output": sample(output_power, uncertainty, timestamp)},
                coverage_complete=True, outputs_non_overlapping=True,
                max_skew_seconds=0.1, uncertainty_type=kind)
    args.update(overrides)
    return audit_power_state(**args)


class PowerAuditorTests(unittest.TestCase):
    def test_conservative_classification_and_interval(self):
        result = audit(10, 5)
        self.assertEqual(result["classification"], "POSITIVE_UNACCOUNTED_POWER")
        self.assertEqual(result["balance_interval_w"], (3.5, 6.5))
        self.assertEqual(audit(5, 10)["classification"], "NEGATIVE_BALANCE_DISCREPANCY")
        self.assertEqual(audit(10, 10)["classification"], "CONSISTENT_WITH_ZERO")
        self.assertEqual(audit(0, 0)["classification"], "CONSISTENT_WITH_ZERO")

    def test_statistical_independent_normal(self):
        result = audit(10, 5, kind=UncertaintyType.STATISTICAL)
        margin = NormalDist().inv_cdf(0.975) * hypot(1, 0.5)
        self.assertAlmostEqual(result["balance_interval_w"][0], 5 - margin)
        self.assertAlmostEqual(result["balance_interval_w"][1], 5 + margin)

    def test_missing_metadata_and_skew(self):
        result = audit(10, 5, timestamp=NOW + timedelta(seconds=1))
        self.assertEqual(result["classification"], "INDETERMINATE")
        self.assertIsNone(result["balance_interval_w"])
        for kwargs in ({"coverage_complete": None}, {"outputs_non_overlapping": False},
                       {"uncertainty_type": None}):
            self.assertEqual(audit(10, 5, **kwargs)["classification"], "INDETERMINATE")
        self.assertEqual(audit(10, 5, uncertainty=None)["classification"], "INDETERMINATE")
        self.assertEqual(audit(10, 5, coverage_complete=False)["classification"],
                         "POSITIVE_UNACCOUNTED_POWER")

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            sample(1, timestamp=datetime(2026, 1, 1))
        for value in (float("nan"), -1, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                sample(value)
        with self.assertRaises(ValueError):
            audit(1, 1, max_skew_seconds=-1)
        with self.assertRaises(ValueError):
            audit(1, 1, confidence=1)
        with self.assertRaises(OverflowError):
            audit(1e308, 1, uncertainty=1e308)


if __name__ == "__main__":
    unittest.main()
