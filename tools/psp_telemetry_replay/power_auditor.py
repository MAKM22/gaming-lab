"""Power balance estimates for supplied measurements; not a hardware safety system.

Uncertainties may be percentages of power or absolute watts, but not both.
Conservative uncertainties are hard absolute bounds. Statistical uncertainties
represent one standard deviation of power; the model
assumes independent, normally distributed channel errors. Neither model includes
timing error, calibration correlation, or unmeasured loads automatically.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import math
from statistics import NormalDist
from typing import Optional


class UncertaintyType(Enum):
    CONSERVATIVE = "conservative_bound"
    STATISTICAL = "independent_normal_1sigma"


def _finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


def _aware_timestamp(value, name):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value


@dataclass(frozen=True)
class Channel:
    timestamp: datetime
    voltage_v: float
    current_a: float
    uncertainty_pct: Optional[float]
    uncertainty_w: Optional[float] = None

    def __post_init__(self):
        _aware_timestamp(self.timestamp, "channel timestamp")
        for value, name in ((self.voltage_v, "voltage_v"), (self.current_a, "current_a")):
            if _finite(value, name) < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.uncertainty_pct is not None and _finite(self.uncertainty_pct, "uncertainty_pct") < 0:
            raise ValueError("uncertainty_pct must be non-negative")
        if self.uncertainty_w is not None and _finite(self.uncertainty_w, "uncertainty_w") < 0:
            raise ValueError("uncertainty_w must be non-negative")
        if self.uncertainty_pct is not None and self.uncertainty_w is not None:
            raise ValueError("specify only one power uncertainty")

    @property
    def power_w(self):
        power = self.voltage_v * self.current_a
        if not math.isfinite(power):
            raise OverflowError("channel power is not finite")
        return power


def audit_power_state(*, workload: str, boundary: str,
                      input_channel: Channel, rails: dict[str, Channel],
                      coverage_complete: Optional[bool],
                      outputs_non_overlapping: Optional[bool],
                      max_skew_seconds: float,
                      uncertainty_type: Optional[UncertaintyType],
                      confidence: float = 0.95) -> dict:
    """Assess one boundary. Results classify a balance, not conversion loss.

    coverage_complete and outputs_non_overlapping are caller attestations, not
    automatically verified. Statistical confidence is a two-sided interval.
    """
    if not isinstance(workload, str) or not workload.strip():
        raise ValueError("workload must be a non-empty string")
    if not isinstance(boundary, str) or not boundary.strip():
        raise ValueError("boundary must be a non-empty string")
    if not isinstance(input_channel, Channel):
        raise ValueError("input_channel must be a Channel")
    if not isinstance(rails, dict) or not rails:
        raise ValueError("at least one named output channel is required")
    if any(not isinstance(k, str) or not k.strip() or not isinstance(v, Channel)
           for k, v in rails.items()):
        raise ValueError("rails must map non-empty names to Channels")
    for value, name in ((coverage_complete, "coverage_complete"),
                        (outputs_non_overlapping, "outputs_non_overlapping")):
        if value is not None and type(value) is not bool:
            raise ValueError(f"{name} must be True, False, or None")
    skew_limit = _finite(max_skew_seconds, "max_skew_seconds")
    if skew_limit < 0:
        raise ValueError("max_skew_seconds must be non-negative")
    if uncertainty_type is not None and not isinstance(uncertainty_type, UncertaintyType):
        raise ValueError("uncertainty_type must be an UncertaintyType or None")
    confidence = _finite(confidence, "confidence")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between zero and one")

    channels = [input_channel, *rails.values()]
    times = [channel.timestamp.astimezone(timezone.utc) for channel in channels]
    skew = (max(times) - min(times)).total_seconds()
    input_power = input_channel.power_w
    rail_powers = {name: channel.power_w for name, channel in rails.items()}
    try:
        output_power = math.fsum(rail_powers.values())
        balance = input_power - output_power
    except OverflowError as exc:
        raise OverflowError("power balance overflow") from exc
    if not math.isfinite(balance):
        raise OverflowError("power balance is not finite")

    reasons = []
    if skew > skew_limit:
        reasons.append("channel timestamps exceed maximum skew")
    if coverage_complete is None:
        reasons.append("coverage is unspecified")
    if outputs_non_overlapping is not True:
        reasons.append("non-overlapping outputs are not confirmed")
    if uncertainty_type is None or any(c.uncertainty_pct is None and c.uncertainty_w is None
                                       for c in channels):
        reasons.append("uncertainty model or channel uncertainty is missing")

    interval = None
    classification = "INDETERMINATE"
    if not reasons:
        uncertainties = [
            float(c.uncertainty_w) if c.uncertainty_w is not None
            else c.power_w * (float(c.uncertainty_pct) / 100.0)
            for c in channels
        ]
        if not all(math.isfinite(x) for x in uncertainties):
            raise OverflowError("channel uncertainty is not finite")
        if uncertainty_type is UncertaintyType.CONSERVATIVE:
            try:
                margin = math.fsum(uncertainties)
            except OverflowError as exc:
                raise OverflowError("uncertainty sum overflow") from exc
        else:
            quantile = (1.0 + confidence) / 2.0
            if quantile >= 1.0:
                raise ValueError("confidence is too close to one for float precision")
            z = NormalDist().inv_cdf(quantile)
            margin = z * math.hypot(*uncertainties)
        lower, upper = balance - margin, balance + margin
        if not all(math.isfinite(x) for x in (margin, lower, upper)):
            raise OverflowError("uncertainty interval is not finite")
        interval = (lower, upper)
        if lower > 0:
            classification = "POSITIVE_UNACCOUNTED_POWER"
        elif upper < 0:
            classification = "NEGATIVE_BALANCE_DISCREPANCY"
        else:
            classification = "CONSISTENT_WITH_ZERO"

    return {
        "workload": workload,
        "boundary": boundary,
        "input_power_w": input_power,
        "rail_power_w": rail_powers,
        "output_power_w": output_power,
        "balance_w": balance,
        "balance_interval_w": interval,
        "classification": classification,
        "indeterminate_reasons": reasons,
        "observed_skew_seconds": skew,
        "max_skew_seconds": skew_limit,
        "coverage_complete": coverage_complete,
        "outputs_non_overlapping": outputs_non_overlapping,
        "uncertainty_type": uncertainty_type.value if uncertainty_type else None,
        "confidence": confidence if uncertainty_type is UncertaintyType.STATISTICAL else None,
    }


if __name__ == "__main__":
    from pprint import pprint

    now = datetime.now(timezone.utc)
    result = audit_power_state(
        workload="illustrative",
        boundary="example power boundary",
        input_channel=Channel(now, 3.62, 0.85, 2.0),
        rails={
            "core": Channel(now, 1.2, 1.0, 3.0),
            "display": Channel(now, 3.3, 0.1, 3.0),
        },
        coverage_complete=False,
        outputs_non_overlapping=True,
        max_skew_seconds=0.01,
        uncertainty_type=UncertaintyType.CONSERVATIVE,
    )
    pprint(result)
