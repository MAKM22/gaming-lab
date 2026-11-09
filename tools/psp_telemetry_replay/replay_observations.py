"""Replay version 1 mock observation inputs; never connects to hardware.

Each channel specifies either uncertainty_pct (percent of power), or both
voltage_uncertainty and current_uncertainty objects with value and unit: "pct"
or the absolute unit "V" / "A". In conservative mode, these are absolute bounds
and power error includes the product term. In statistical mode they are
independent one-sigma errors propagated using a first-order approximation;
this is not a rigorous confidence interval when nonlinearity matters, e.g.
near zero. Power channels are also assumed independent by the power auditor.
The original inputs are retained separately in output for reproducibility.
"""

import argparse
import copy
from datetime import datetime
import json
import math
import sys

from integrated_observation import CoverageAttestations, IntegratedObservationSession
from power_auditor import Channel, UncertaintyType
from psp_boot_model import ServiceSupport
from psp_syscon_model import BatterySerialResponse, ResultStatus


def _object(value, required, optional=()):
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    keys = set(value)
    if not set(required) <= keys or keys - set(required) - set(optional):
        raise ValueError(f"invalid fields: expected {sorted(required)}, optional {sorted(optional)}")
    return value


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamp must be an ISO 8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid timestamp: {value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return parsed


def _quantity_uncertainty(value, measurement, absolute_unit):
    value = _object(value, ("value", "unit"))
    magnitude = value["value"]
    if isinstance(magnitude, bool) or not isinstance(magnitude, (int, float)):
        raise ValueError("uncertainty magnitude must be a non-negative finite number")
    try:
        magnitude = float(magnitude)
    except OverflowError as exc:
        raise ValueError("uncertainty magnitude must be finite") from exc
    if not math.isfinite(magnitude) or magnitude < 0:
        raise ValueError("uncertainty magnitude must be a non-negative finite number")
    if value["unit"] == "pct":
        absolute = measurement * (magnitude / 100.0)
    elif value["unit"] == absolute_unit:
        absolute = magnitude
    else:
        raise ValueError(f"uncertainty unit must be 'pct' or {absolute_unit!r}")
    if not math.isfinite(absolute):
        raise ValueError("uncertainty conversion overflow")
    return absolute


def _channel(value, uncertainty_type):
    value = _object(value, ("timestamp", "voltage_v", "current_a"),
                    ("uncertainty_pct", "voltage_uncertainty", "current_uncertainty"))
    has_pct = "uncertainty_pct" in value
    has_v = "voltage_uncertainty" in value
    has_i = "current_uncertainty" in value
    if has_pct == (has_v or has_i) or has_v != has_i:
        raise ValueError("provide uncertainty_pct or both voltage_uncertainty and current_uncertainty")
    timestamp = _timestamp(value["timestamp"])
    if has_pct:
        return Channel(timestamp, value["voltage_v"], value["current_a"], value["uncertainty_pct"])
    if uncertainty_type is None:
        raise ValueError("quantity uncertainties require an uncertainty_type")
    # Channel validates the measurements before they are used in propagation.
    base = Channel(timestamp, value["voltage_v"], value["current_a"], None)
    voltage, current = float(base.voltage_v), float(base.current_a)
    dv = _quantity_uncertainty(value["voltage_uncertainty"], voltage, "V")
    di = _quantity_uncertainty(value["current_uncertainty"], current, "A")
    if uncertainty_type is UncertaintyType.CONSERVATIVE:
        # Triangle bound for (V+dV)(I+dI)-VI, including the cross term.
        absolute = current * dv + voltage * di + dv * di
    else:
        # First-order standard uncertainty under independent V and I errors.
        absolute = math.hypot(current * dv, voltage * di)
    if not math.isfinite(absolute):
        raise ValueError("power uncertainty overflow")
    return Channel(timestamp, voltage, current, None, uncertainty_w=absolute)


def _enum(enum, value, name):
    try:
        return enum(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"invalid {name}: {value!r}") from exc


def _hex_bytes(value):
    if not isinstance(value, str) or len(value) % 2:
        raise ValueError("data_hex must contain an even number of hexadecimal characters")
    if any(c not in "0123456789abcdefABCDEF" for c in value):
        raise ValueError("data_hex must contain only hexadecimal characters")
    return bytes.fromhex(value)


def _no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError(f"non-standard JSON number: {value}")


def replay(document):
    """Validate all records before returning detached, derived observations."""
    document = _object(document, ("schema_version", "provenance", "session_id", "observations"))
    if type(document["schema_version"]) is not int or document["schema_version"] != 1:
        raise ValueError("unsupported schema_version; expected 1")
    if document["provenance"] != "simulation":
        raise ValueError("provenance must be 'simulation'")
    if not isinstance(document["session_id"], str) or not document["session_id"].strip():
        raise ValueError("session_id must be a non-empty string")
    if not isinstance(document["observations"], list):
        raise ValueError("observations must be a list")
    session = IntegratedObservationSession(document["session_id"])
    for index, item in enumerate(document["observations"]):
        try:
            item = _object(item, ("syscon", "power", "attestations", "max_association_skew_seconds"))
            syscon = _object(item["syscon"], ("timestamp", "status", "reported_length",
                                               "data_hex", "service_support"))
            power = _object(item["power"], ("workload", "boundary", "input_channel", "rails",
                                             "max_channel_skew_seconds", "uncertainty_type"),
                            ("confidence",))
            attestations = _object(item["attestations"],
                                   ("coverage_complete", "outputs_non_overlapping"))
            if not isinstance(power["rails"], dict):
                raise ValueError("power rails must be an object")
            uncertainty = power["uncertainty_type"]
            if uncertainty is not None:
                uncertainty = _enum(UncertaintyType, uncertainty, "uncertainty_type")
            response = BatterySerialResponse(
                _enum(ResultStatus, syscon["status"], "syscon status"),
                syscon["reported_length"], _hex_bytes(syscon["data_hex"]),
            )
            session.record(
                syscon_timestamp=_timestamp(syscon["timestamp"]), response=response,
                service_support=_enum(ServiceSupport, syscon["service_support"], "service_support"),
                workload=power["workload"], boundary=power["boundary"],
                input_channel=_channel(power["input_channel"], uncertainty),
                rails={name: _channel(channel, uncertainty) for name, channel in power["rails"].items()},
                attestations=CoverageAttestations(**attestations),
                max_channel_skew_seconds=power["max_channel_skew_seconds"],
                max_association_skew_seconds=item["max_association_skew_seconds"],
                uncertainty_type=uncertainty, confidence=power.get("confidence", 0.95),
            )
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError(f"observation {index}: {exc}") from exc
    return {
        "schema_version": 1,
        "provenance": "simulation",
        "session_id": session.session_id,
        "source_inputs": copy.deepcopy(document),
        "observations": [record.to_dict() for record in session.observations],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Version 1 simulation JSON file")
    args = parser.parse_args()
    try:
        with open(args.input, encoding="utf-8") as file:
            document = json.load(file, object_pairs_hook=_no_duplicates,
                                 parse_constant=_invalid_constant)
        result = replay(document)
        print(json.dumps(result, indent=2, allow_nan=False))
    except (OSError, ValueError, OverflowError) as exc:
        print(f"Replay failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
