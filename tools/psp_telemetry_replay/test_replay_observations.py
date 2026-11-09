import copy
from decimal import Decimal
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from replay_observations import replay

try:
    import jsonschema
except ModuleNotFoundError as exc:
    if exc.name != "jsonschema":
        raise
    jsonschema = None

ROOT = Path(__file__).parent


def assert_json_equal(test, actual, expected, path="$"):
    """Compare JSON structures exactly, except for floating-point roundoff."""
    if isinstance(expected, dict):
        test.assertIsInstance(actual, dict, path)
        test.assertEqual(set(actual), set(expected), path)
        for key in expected:
            assert_json_equal(test, actual[key], expected[key], f"{path}.{key}")
    elif isinstance(expected, list):
        test.assertIsInstance(actual, list, path)
        test.assertEqual(len(actual), len(expected), path)
        for index, (a, e) in enumerate(zip(actual, expected)):
            assert_json_equal(test, a, e, f"{path}[{index}]")
    elif isinstance(expected, float):
        test.assertIs(type(actual), float, path)
        test.assertTrue(math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12),
                        f"{path}: {actual!r} != {expected!r}")
    else:
        test.assertIs(type(actual), type(expected), path)
        test.assertEqual(actual, expected, path)


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.document = json.loads((ROOT / "mock_observations_v1.json").read_text(encoding="utf-8"))

    def test_roundtrip_reproducibility_and_fields(self):
        original = copy.deepcopy(self.document)
        result = replay(self.document)
        self.assertEqual(result, replay(self.document))
        self.assertEqual(original, self.document)
        record = result["observations"][0]
        self.assertEqual(record["syscon"]["boot_path_candidate"], "unknown")
        self.assertEqual(record["power"]["classification"], "POSITIVE_UNACCOUNTED_POWER")
        self.assertAlmostEqual(record["association_skew_seconds"], 0.005)
        self.assertFalse(record["attestations"]["coverage_complete"])
        self.assertFalse(record["causality_asserted"])

    def test_fault_status_remains_explicit(self):
        item = self.document["observations"][0]["syscon"]
        item.update(status="transport_error", reported_length=None, data_hex="")
        result = replay(self.document)["observations"][0]["syscon"]
        self.assertEqual(result["status"], "error")
        self.assertIn("transport_error", result["error"])

    def test_reject_invalid_documents(self):
        for mutation in (
            lambda d: d.update(schema_version=True),
            lambda d: d.update(schema_version=2),
            lambda d: d.update(provenance="hardware"),
            lambda d: d.update(session_id=None),
            lambda d: d["observations"][0]["syscon"].update(timestamp="2026-01-01T00:00:00"),
            lambda d: d["observations"][0]["syscon"].update(data_hex="FF FF"),
            lambda d: d["observations"][0]["power"].update(extra=1),
        ):
            doc = copy.deepcopy(self.document)
            mutation(doc)
            with self.subTest(doc=doc), self.assertRaises(ValueError):
                replay(doc)

    def test_cli_no_partial_output_and_duplicate_rejection(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "input.json"
            self.document["observations"].append({"bad": True})
            path.write_text(json.dumps(self.document), encoding="utf-8")
            result = subprocess.run([sys.executable, str(ROOT / "replay_observations.py"), str(path)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertIn("observation 1", result.stderr)
            path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            result = subprocess.run([sys.executable, str(ROOT / "replay_observations.py"), str(path)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("duplicate JSON key", result.stderr)

    def test_quantity_uncertainties_and_cross_term(self):
        doc = json.loads((ROOT / "mock_quantities_v1.json").read_text(encoding="utf-8"))
        result = replay(doc)
        record = result["observations"][0]
        self.assertEqual(record["syscon"]["boot_path_candidate"], "service_boot_candidate")
        self.assertEqual(record["power"]["classification"], "POSITIVE_UNACCOUNTED_POWER")
        self.assertAlmostEqual(record["power"]["balance_w"], 0.12)
        margin = (3.24 + 1.8 + 1.32) * (0.005 + 0.01 + 0.005 * 0.01)
        self.assertAlmostEqual(record["power"]["balance_interval_w"][0], 0.12 - margin)
        self.assertEqual(result["source_inputs"], doc)
        result["source_inputs"]["observations"].clear()
        self.assertEqual(len(doc["observations"]), 1)

    def test_quantity_fixture_and_cli_output(self):
        source = ROOT / "mock_quantities_v1.json"
        document = json.loads(source.read_text(encoding="utf-8"))
        expected = json.loads((ROOT / "fixture_output_v1.json").read_text(encoding="utf-8"))
        assert_json_equal(self, replay(document), expected)
        result = subprocess.run([sys.executable, str(ROOT / "replay_observations.py"), str(source)],
                                capture_output=True, text=True, check=True)
        assert_json_equal(self, json.loads(result.stdout), expected)

    def test_fixture_values_against_decimal_bound(self):
        expected = json.loads((ROOT / "fixture_output_v1.json").read_text(encoding="utf-8"))
        power = expected["observations"][0]["power"]
        factor = Decimal("0.005") + Decimal("0.01") + Decimal("0.005") * Decimal("0.01")
        input_power = Decimal("3.6") * Decimal("0.9")
        rail_powers = [Decimal("1.2") * Decimal("1.5"), Decimal("3.3") * Decimal("0.4")]
        uncertainties = [p * factor for p in [input_power, *rail_powers]]
        margin = sum(uncertainties)
        balance = input_power - sum(rail_powers)
        self.assertAlmostEqual(power["input_channel"]["uncertainty_w"], float(uncertainties[0]), places=12)
        for channel, uncertainty in zip(power["rails"], uncertainties[1:]):
            self.assertAlmostEqual(channel["uncertainty_w"], float(uncertainty), places=12)
        self.assertAlmostEqual(power["balance_interval_w"][0], float(balance - margin), places=12)
        self.assertAlmostEqual(power["balance_interval_w"][1], float(balance + margin), places=12)

    def test_zero_and_statistical_absolute_uncertainties(self):
        doc = json.loads((ROOT / "mock_quantities_v1.json").read_text(encoding="utf-8"))
        power = doc["observations"][0]["power"]
        power["input_channel"].update(
            voltage_v=0, current_a=2,
            voltage_uncertainty={"value": 0.5, "unit": "V"},
            current_uncertainty={"value": 0.25, "unit": "A"},
        )
        result = replay(doc)["observations"][0]
        self.assertAlmostEqual(result["power"]["input_channel"]["uncertainty_w"], 1.125)
        power["uncertainty_type"] = "independent_normal_1sigma"
        result = replay(doc)["observations"][0]
        self.assertAlmostEqual(result["power"]["input_channel"]["uncertainty_w"], 1)

    def test_reject_incomplete_or_ambiguous_uncertainties(self):
        doc = json.loads((ROOT / "mock_quantities_v1.json").read_text(encoding="utf-8"))
        for mutation in (
            lambda c: c.pop("current_uncertainty"),
            lambda c: c.update(uncertainty_pct=0),
            lambda c: c["voltage_uncertainty"].update(unit="unknown"),
            lambda c: c["voltage_uncertainty"].update(value=-1),
            lambda c: c["voltage_uncertainty"].update(value=True),
        ):
            case = copy.deepcopy(doc)
            mutation(case["observations"][0]["power"]["input_channel"])
            with self.assertRaises(ValueError):
                replay(case)


@unittest.skipIf(jsonschema is None, "optional jsonschema[format] is not installed")
class SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        schema = json.loads((ROOT / "schema_v1.json").read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        checker = jsonschema.FormatChecker()
        if "date-time" not in checker.checkers:
            raise RuntimeError("jsonschema date-time format support is required")
        cls.validator = jsonschema.Draft202012Validator(schema, format_checker=checker)

    def test_examples_are_valid(self):
        for name in ("mock_observations_v1.json", "mock_quantities_v1.json"):
            doc = json.loads((ROOT / name).read_text(encoding="utf-8"))
            with self.subTest(name=name):
                self.validator.validate(doc)
                replay(doc)

    def test_invalid_inputs_are_rejected(self):
        source = json.loads((ROOT / "mock_quantities_v1.json").read_text(encoding="utf-8"))
        mutations = (
            lambda d: d.update(schema_version=2),
            lambda d: d.update(extra=True),
            lambda d: d["observations"][0]["syscon"].update(timestamp="not-a-date"),
            lambda d: d["observations"][0]["syscon"].update(data_hex="FF FF"),
            lambda d: d["observations"][0]["power"]["input_channel"].update(uncertainty_pct=0),
            lambda d: d["observations"][0]["power"]["input_channel"].pop("current_uncertainty"),
            lambda d: d["observations"][0]["power"]["input_channel"]["voltage_uncertainty"].update(unit="A"),
            lambda d: d["observations"][0]["power"].update(uncertainty_type=None),
            lambda d: d["observations"][0]["attestations"].update(coverage_complete=1),
        )
        for mutation in mutations:
            case = copy.deepcopy(source)
            mutation(case)
            with self.subTest(case=case):
                self.assertFalse(self.validator.is_valid(case))
                with self.assertRaises(ValueError):
                    replay(case)


if __name__ == "__main__":
    unittest.main()
