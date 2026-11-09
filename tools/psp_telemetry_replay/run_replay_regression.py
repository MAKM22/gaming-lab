"""Strict schema and golden-output replay checks. Requires jsonschema[format]."""

import copy
from decimal import Decimal
import json
from pathlib import Path
import unittest

try:
    import jsonschema
except ModuleNotFoundError as exc:
    if exc.name != "jsonschema":
        raise
    raise SystemExit("Install the required dependency: python -m pip install \"jsonschema[format]\"") from exc

from replay_observations import replay
from test_replay_observations import assert_json_equal

ROOT = Path(__file__).resolve().parent


def load_json(name):
    with (ROOT / name).open(encoding="utf-8") as file:
        return json.load(file)


class ReplayRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        schema = load_json("schema_v1.json")
        jsonschema.Draft202012Validator.check_schema(schema)
        checker = jsonschema.FormatChecker()
        if "date-time" not in checker.checkers or checker.conforms("not-a-date", "date-time"):
            raise RuntimeError("date-time validation unavailable; install jsonschema[format]")
        cls.validator = jsonschema.Draft202012Validator(schema, format_checker=checker)

    def check_replay(self, input_name, fixture_name, interval):
        document = load_json(input_name)
        expected = load_json(fixture_name)
        self.validator.validate(document)
        result = replay(document)
        assert_json_equal(self, result, expected)
        power = result["observations"][0]["power"]
        self.assertEqual(power["classification"], "POSITIVE_UNACCOUNTED_POWER")
        self.assertEqual(len(power["balance_interval_w"]), 2)
        for actual, bound in zip(power["balance_interval_w"], interval):
            self.assertAlmostEqual(actual, bound, places=12)

    def test_legacy_power_percentage(self):
        self.check_replay("mock_observations_v1.json", "fixture_output_legacy_v1.json",
                          (1.77946, 1.97454))

    def test_quantity_uncertainties(self):
        self.check_replay("mock_quantities_v1.json", "fixture_output_v1.json",
                          (0.024282, 0.215718))

    def test_quantity_interval_includes_cross_term(self):
        document = load_json("mock_quantities_v1.json")
        self.validator.validate(document)
        power = replay(document)["observations"][0]["power"]

        input_power = Decimal("3.6") * Decimal("0.9")
        rail_power = Decimal("1.2") * Decimal("1.5") + Decimal("3.3") * Decimal("0.4")
        balance = input_power - rail_power
        first_order = (input_power + rail_power) * (Decimal("0.005") + Decimal("0.01"))
        cross_term = (input_power + rail_power) * Decimal("0.005") * Decimal("0.01")
        lower, upper = power["balance_interval_w"]
        self.assertAlmostEqual(lower, float(balance - first_order - cross_term), places=12)
        self.assertAlmostEqual(upper, float(balance + first_order + cross_term), places=12)
        self.assertLess(lower, float(balance - first_order))
        self.assertGreater(upper, float(balance + first_order))

    def test_malformed_inputs_are_rejected(self):
        document = load_json("mock_observations_v1.json")
        invalid_version = copy.deepcopy(document)
        invalid_version["schema_version"] = 2
        invalid_timestamp = copy.deepcopy(document)
        invalid_timestamp["observations"][0]["syscon"]["timestamp"] = "not-a-date"
        for case in (invalid_version, invalid_timestamp):
            with self.subTest(case=case):
                with self.assertRaises(jsonschema.ValidationError):
                    self.validator.validate(case)
                with self.assertRaises(ValueError):
                    replay(case)

    def test_v1_telemetry_boundaries(self):
        source = load_json("mock_telemetry_v1.json")

        def run(document):
            self.validator.validate(document)
            return replay(document)["observations"][0]

        record = run(source)
        self.assertAlmostEqual(record["power"]["balance_w"], 20.05, places=12)
        self.assertAlmostEqual(record["power"]["balance_interval_w"][0], 19.60075, places=12)
        self.assertAlmostEqual(record["power"]["balance_interval_w"][1], 20.49925, places=12)
        self.assertEqual(record["power"]["classification"], "POSITIVE_UNACCOUNTED_POWER")

        skew = copy.deepcopy(source)
        rails = skew["observations"][0]["power"]["rails"]
        rails["rail_3v3"]["timestamp"] = "2026-05-16T11:59:59.991Z"
        rails["rail_5v0"]["timestamp"] = "2026-05-16T12:00:00.009Z"
        power = run(skew)["power"]
        self.assertAlmostEqual(power["observed_skew_seconds"], 0.018)
        self.assertEqual(power["classification"], "INDETERMINATE")
        self.assertIn("channel timestamps exceed maximum skew", power["indeterminate_reasons"])

        at_limit = copy.deepcopy(source)
        at_limit["observations"][0]["power"]["rails"]["rail_5v0"]["timestamp"] = \
            "2026-05-16T12:00:00.010Z"
        self.assertEqual(run(at_limit)["power"]["classification"], "POSITIVE_UNACCOUNTED_POWER")

        no_uncertainty = copy.deepcopy(source)
        channel = no_uncertainty["observations"][0]["power"]["input_channel"]
        channel["uncertainty_pct"] = None
        power = run(no_uncertainty)["power"]
        self.assertEqual(power["classification"], "INDETERMINATE")
        self.assertIsNone(power["balance_interval_w"])
        self.assertIn("uncertainty model or channel uncertainty is missing", power["indeterminate_reasons"])
        del channel["uncertainty_pct"]
        with self.assertRaises(jsonschema.ValidationError):
            self.validator.validate(no_uncertainty)
        with self.assertRaises(ValueError):
            replay(no_uncertainty)

        incomplete = copy.deepcopy(source)
        incomplete["observations"][0]["attestations"]["coverage_complete"] = False
        record = run(incomplete)
        self.assertFalse(record["attestations"]["coverage_complete"])
        self.assertEqual(record["power"]["classification"], "POSITIVE_UNACCOUNTED_POWER")
        incomplete["observations"][0]["attestations"]["coverage_complete"] = None
        power = run(incomplete)["power"]
        self.assertEqual(power["classification"], "INDETERMINATE")
        self.assertIn("coverage is unspecified", power["indeterminate_reasons"])

        negative = copy.deepcopy(source)
        negative["observations"][0]["power"]["input_channel"]["current_a"] = 0.0
        power = run(negative)["power"]
        self.assertEqual(power["classification"], "NEGATIVE_BALANCE_DISCREPANCY")
        self.assertLess(power["balance_interval_w"][1], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
