"""Contract tests for the proposed manifest schema; enhanced replay is not implemented."""

import copy
import json
from pathlib import Path
import unittest

try:
    import jsonschema
except ModuleNotFoundError as exc:
    if exc.name != "jsonschema":
        raise
    raise SystemExit('Install the required dependency: python -m pip install "jsonschema[format]"') from exc


ROOT = Path(__file__).resolve().parent


class ManifestSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        schema = json.loads((ROOT / "manifest_schema.json").read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        cls.validator = jsonschema.Draft202012Validator(schema)

    def setUp(self):
        self.manifest = {
            "case_id": "missing-uncertainty",
            "input_file": "missing_uncertainty_v1.json",
            "input_schema": "schema_v1.json",
            "output_mode": "enhanced",
            "expected": {
                "outcome": "replay",
                "classification": "INDETERMINATE",
                "reason_codes": ["MISSING_UNCERTAINTY", "SKEW_LIMIT_EXCEEDED"],
                "balance_interval_w": None,
            },
            "comparison": {"relative_tolerance": 1e-12, "absolute_tolerance": 1e-12},
        }

    def test_valid_contract_variants(self):
        legacy = copy.deepcopy(self.manifest)
        legacy["output_mode"] = "legacy"
        legacy["expected"] = {
            "outcome": "replay",
            "classification": "NEGATIVE_BALANCE_DISCREPANCY",
            "balance_interval_w": [-2.0, -1.0],
        }
        validation = copy.deepcopy(self.manifest)
        validation["expected"] = {"outcome": "validation_error", "error_stage": "schema"}
        semantic = copy.deepcopy(validation)
        semantic["expected"]["error_stage"] = "replay"
        for case in (self.manifest, legacy, validation, semantic):
            with self.subTest(case=case):
                self.validator.validate(case)

    def test_reject_invalid_contracts(self):
        def cases():
            case = copy.deepcopy(self.manifest)
            del case["expected"]["reason_codes"]
            yield case
            case = copy.deepcopy(self.manifest)
            case["expected"]["reason_codes"] = []
            yield case
            case = copy.deepcopy(self.manifest)
            case["expected"]["reason_codes"] = ["MISSING_UNCERTAINTY"] * 2
            yield case
            case = copy.deepcopy(self.manifest)
            case["expected"]["reason_codes"] = ["TYPO"]
            yield case
            case = copy.deepcopy(self.manifest)
            case["expected"]["balance_interval_w"] = [0, 1]
            yield case
            case = copy.deepcopy(self.manifest)
            case["output_mode"] = "legacy"
            yield case
            case = copy.deepcopy(self.manifest)
            case["expected"] = {"outcome": "validation_error", "error_stage": "schema",
                                "reason_codes": ["MISSING_UNCERTAINTY"]}
            yield case
            case = copy.deepcopy(self.manifest)
            case["expected"] = {"outcome": "replay", "classification": "SUCCESS",
                                "balance_interval_w": [0, 1]}
            yield case
            case = copy.deepcopy(self.manifest)
            case["expected"] = {"outcome": "replay", "classification": "CONSISTENT_WITH_ZERO",
                                "balance_interval_w": [0, 1, 2]}
            yield case
            case = copy.deepcopy(self.manifest)
            case["comparison"]["absolute_tolerance"] = -1
            yield case
            case = copy.deepcopy(self.manifest)
            case["unexpected"] = True
            yield case
            case = copy.deepcopy(self.manifest)
            case["case_id"] = " "
            yield case

        for case in cases():
            with self.subTest(case=case):
                self.assertFalse(self.validator.is_valid(case))


if __name__ == "__main__":
    unittest.main(verbosity=2)
