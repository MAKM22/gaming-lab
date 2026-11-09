# Simulated PSP telemetry replay

An offline Python pipeline for replaying supplied, simulated observations. It
combines an in-memory battery-ID decision model, a narrow mock SYSCON response
decoder, timestamped observation snapshots, and power-balance uncertainty
estimates. It never connects to a console, battery, serial interface, or EEPROM.

## Setup and quick start

Requires Python 3.10 or later. Replay itself uses only the standard library.
The full test suite requires `jsonschema` with its date-time format dependencies.
Keep the modules, schemas, tests, and fixtures together in this directory.

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r tools\psp_telemetry_replay\requirements-test.txt
.\.venv\Scripts\python.exe tools\psp_telemetry_replay\replay_observations.py tools\psp_telemetry_replay\mock_quantities_v1.json
.\.venv\Scripts\python.exe -m unittest discover -s tools\psp_telemetry_replay -v
.\.venv\Scripts\python.exe tools\psp_telemetry_replay\run_replay_regression.py
```

On other platforms, use the virtual environment's `bin/python` in place of
`.\.venv\Scripts\python.exe`, and the platform's path separators.

Replay writes a single JSON result to standard output. Invalid input produces
an error on standard error, a nonzero exit status, and no partial JSON output.
The CLI validates input at runtime; it does not invoke JSON Schema validation.
The strict regression runner validates the schema with date-time checking and
compares both golden fixtures, including an independent conservative
uncertainty calculation. It fails if the test dependency is missing.

For standard-library-only runtime and golden tests, change to this directory
and run:

```powershell
python -m unittest -v test_psp_boot_model test_psp_syscon_model test_power_auditor test_integrated_observation test_replay_observations
```

The optional schema checks in `test_replay_observations` explicitly skip when
`jsonschema` is absent. Full discovery also imports strict regression and
manifest-schema tests, so it requires the test dependency.

## Contents and compatibility

| Files | Purpose |
| --- | --- |
| `psp_boot_model.py`, `psp_syscon_model.py` | Hypothetical boot-path candidates and mock four-byte SYSCON responses |
| `power_auditor.py`, `integrated_observation.py` | Power balance, uncertainty intervals, and immutable timestamped records |
| `replay_observations.py`, `schema_v1.json` | Existing integer-version-1 replay importer and input schema |
| `mock_quantities_v1.json`, `fixture_output_v1.json` | Separate voltage/current uncertainty input and its golden output |
| `mock_observations_v1.json`, `fixture_output_legacy_v1.json` | Legacy power-percentage uncertainty input and its distinct golden output |
| `mock_telemetry_v1.json` | Illustrative 12 V example translated into the existing v1 format |
| `test_*.py`, `run_replay_regression.py` | Unit, CLI, schema, golden-output, and boundary regression checks |
| `manifest_schema.json`, `test_manifest_schema.py` | Contract and schema-only tests for proposed external test metadata |
| [replay_format.md](replay_format.md) | Detailed v1 behavior, numerical assumptions, and proposal limitations |

The imported Python modules, schemas, and JSON fixtures retain the original v1
behavior. Golden comparisons tolerate only floating-point roundoff. Conservative
quantity uncertainties include the second-order voltage/current cross term;
statistical uncertainty uses a first-order independent-error approximation.

## Limits and proposals

All measurements, timestamps, coverage, non-overlap, and service-support states
are caller-supplied simulation data, not verified hardware facts. A boot-path
candidate is not proof of actual compatibility or successful boot. Positive
unaccounted power is not measured conversion loss, and a negative balance is a
discrepancy, not evidence of a particular physical cause. No causal relationship
between SYSCON results and power measurements is asserted.

**Enhanced output and manifest execution are proposals, not implemented
features.** The manifest schema describes a potential test contract only.
There is no manifest CLI, enhanced output mode, reason-code emission, path
confinement, case-ID uniqueness enforcement, or manifest-driven tolerance
comparison. Passing its schema contract tests does not demonstrate those
features.
