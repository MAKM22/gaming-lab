# Simulated replay format, version 1

`schema_v1.json` describes the existing integer-version-1 input, not a
proposed alternative nested format. `mock_quantities_v1.json`
is the fixed input for `fixture_output_v1.json`.
`mock_observations_v1.json` is the distinct legacy input for
`fixture_output_legacy_v1.json`.
`mock_telemetry_v1.json` translates the illustrative 12 V example into the
existing v1 layout, with percentage uncertainties of power and an explicit
unknown mock service-support state.

The commands in these notes run from this directory; see [README.md](README.md)
for repository-root setup and full test discovery.

Run `python replay_observations.py mock_quantities_v1.json` to produce the
replay output, and `python -m unittest test_replay_observations` for regression
checks. All replay modules must be in the same directory. To also run the JSON
Schema conformance checks, install the optional `jsonschema` Python package
with its format dependencies (`jsonschema[format]`); without it those checks
are explicitly skipped, while the golden and runtime tests still run.

For a strict standalone regression run, install `jsonschema[format]` and run
`python run_replay_regression.py`, or run `python -m unittest -v test_replay`.
Both invoke the same checks and fail if the dependency or
date-time format validation is unavailable. It validates both inputs and
compares each replay against its own fixture. The legacy input uses
power-percentage uncertainty and has a conservative balance interval of
`[1.77946, 1.97454]` W; the quantity input uses separate voltage and current
uncertainties and has a different interval.
The strict runner also exercises the telemetry example and boundary cases.
The strict runner also independently checks that the quantity interval includes
the second-order cross term. The narrower interval `[0.0246, 0.2154]` W is
the first-order result for those quantity measurements, not the conservative
bound implemented here.

Each channel has a timezone-aware timestamp and either a percentage power
uncertainty or both voltage and current uncertainties. The latter use `pct`,
or the absolute units `V` and `A`. Conservative bounds include the cross
term; statistical uncertainty uses a first-order, independent-error
approximation. Missing uncertainties produce indeterminate results. Coverage,
non-overlap, and timing are caller-supplied and cannot prove actual hardware
synchronization or causality. No physical device is accessed. For the quantity
fixture, the independently calculated conservative balance interval is
`[0.024282, 0.215718]` W; the residual is unaccounted power, not a measured
conversion loss.

V1 uses `voltage_v`, `current_a`, and either `uncertainty_pct` or both
`voltage_uncertainty` and `current_uncertainty` objects. It does not define
`v_val` or `i_val` fields. `uncertainty_pct: null` is accepted but makes the
result indeterminate; omitting all uncertainty fields is invalid. The maximum
power-channel skew is the difference between the earliest and latest channel
timestamps; a skew equal to the limit is accepted. A false coverage attestation
is retained and does not by itself make classification indeterminate, whereas
unknown coverage does. A negative balance is a discrepancy, not proof of any
particular physical cause.

The schema describes structure, while the importer additionally validates
finite floating-point values, timestamp timezone awareness, numerical overflow,
and supported modeled responses. A syntactically valid but failed SYSCON
response is recorded as an error rather than rejected. The schema limits
`reported_length` to integer or null even though the mock records other types
as response errors; JSON Schema also considers `1.0` an integer whereas the
importer requires the version to be an actual integer. JSON Schema date-time
format validation should be enabled when using a schema validator. The runtime
accepts timezone-aware ISO 8601 strings beyond the schema's RFC 3339 format.
Statistical results may differ in the last floating-point bits across Python
versions and platforms; fixture checks use a tight numerical tolerance.

`schema_version` identifies the input format, not a calculator implementation
version. An intentional calculation change requires reviewing and updating the
golden fixture; the version alone does not guarantee historical replay results.

## Proposed test manifests

`manifest_schema.json` describes external test metadata, not replay inputs.
Its `outcome` distinguishes successful replay from validation failure; a replay
uses the auditor's actual `classification` and a two-element balance interval
or null. Schema and importer errors are distinguished by `error_stage`.
Enhanced indeterminate expectations require one or more distinct proposed
reason codes; legacy expectations have none. A negative balance remains a
discrepancy, not an indeterminate outcome.

Enhanced output, manifest execution, file-path resolution, case-ID uniqueness,
and tolerance-based comparisons are not implemented by this schema. A future
runner must validate and confine paths, enforce unique case IDs, finite numeric
values and ordered intervals, compare codes exactly (as an unordered set), and
apply the stated tolerances to floating-point results only. The schema alone
cannot check those runtime conditions. Run `python -m unittest -v
test_manifest_schema` with `jsonschema[format]` installed to check the schema
contract; that does not test enhanced replay.
