"""Associate mock SYSCON results with supplied power measurements.

Timestamps and coverage are caller-supplied, not independently verified.
No causal relationship or physical hardware access is asserted.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import math
import uuid

from power_auditor import Channel, UncertaintyType, audit_power_state
from psp_boot_model import ServiceSupport
from psp_syscon_model import BatterySerialResponse, classify_response, decode_serial_response


def _timestamp(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware datetimes")
    return value.astimezone(timezone.utc)


def _limit(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError("max_association_skew_seconds must be finite and non-negative")
    try:
        value = float(value)
    except OverflowError as exc:
        raise ValueError("max_association_skew_seconds must be finite and non-negative") from exc
    if not math.isfinite(value) or value < 0:
        raise ValueError("max_association_skew_seconds must be finite and non-negative")
    return value


@dataclass(frozen=True)
class CoverageAttestations:
    coverage_complete: bool | None
    outputs_non_overlapping: bool | None

    def __post_init__(self):
        for value in (self.coverage_complete, self.outputs_non_overlapping):
            if value is not None and type(value) is not bool:
                raise ValueError("coverage attestations must be True, False, or None")


@dataclass(frozen=True)
class SysconObservation:
    timestamp: datetime
    status: str
    identifier: int | None
    service_support: str
    boot_path_candidate: str | None
    error: str | None


@dataclass(frozen=True)
class ChannelSnapshot:
    name: str
    timestamp: datetime
    voltage_v: float
    current_a: float
    uncertainty_pct: float | None
    uncertainty_w: float | None


@dataclass(frozen=True)
class PowerObservation:
    input_channel: ChannelSnapshot
    rails: tuple[ChannelSnapshot, ...]
    workload: str
    boundary: str
    input_power_w: float
    rail_power_w: tuple[tuple[str, float], ...]
    output_power_w: float
    balance_w: float
    balance_interval_w: tuple[float, float] | None
    classification: str
    indeterminate_reasons: tuple[str, ...]
    observed_skew_seconds: float
    max_skew_seconds: float
    uncertainty_type: str | None
    confidence: float | None


@dataclass(frozen=True)
class Observation:
    session_id: str
    syscon: SysconObservation
    power: PowerObservation
    attestations: CoverageAttestations
    association_skew_seconds: float
    max_association_skew_seconds: float
    timestamps_within_limit: bool
    causality_asserted: bool = False

    def to_dict(self) -> dict:
        """Return a detached, JSON-compatible copy of the immutable record."""
        def encode(value):
            if isinstance(value, datetime):
                return _timestamp(value).isoformat()
            raise TypeError(f"cannot encode {type(value).__name__}")

        return json.loads(json.dumps(asdict(self), default=encode, allow_nan=False))


def observe_syscon(*, timestamp: datetime, response: BatterySerialResponse,
                   service_support: ServiceSupport) -> SysconObservation:
    timestamp = _timestamp(timestamp)
    if not isinstance(service_support, ServiceSupport):
        raise ValueError("service_support must be a ServiceSupport value")
    if not isinstance(response, BatterySerialResponse):
        raise ValueError("response must be a BatterySerialResponse")
    try:
        identifier = decode_serial_response(response)
        candidate = classify_response(response, service_support=service_support)
    except (ValueError, RuntimeError) as exc:
        return SysconObservation(timestamp, "error", None, service_support.value, None, str(exc))
    return SysconObservation(timestamp, "ok", identifier, service_support.value,
                             candidate.value, None)


def _channel_snapshot(name: str, channel: Channel) -> ChannelSnapshot:
    return ChannelSnapshot(name, _timestamp(channel.timestamp), float(channel.voltage_v),
                           float(channel.current_a),
                           None if channel.uncertainty_pct is None else float(channel.uncertainty_pct),
                           None if channel.uncertainty_w is None else float(channel.uncertainty_w))


def observe_power(*, workload: str, boundary: str, input_channel: Channel,
                  rails: dict[str, Channel], attestations: CoverageAttestations,
                  max_channel_skew_seconds: float, uncertainty_type: UncertaintyType | None,
                  confidence: float = 0.95) -> PowerObservation:
    if not isinstance(attestations, CoverageAttestations):
        raise ValueError("attestations must be CoverageAttestations")
    result = audit_power_state(
        workload=workload, boundary=boundary, input_channel=input_channel, rails=rails,
        coverage_complete=attestations.coverage_complete,
        outputs_non_overlapping=attestations.outputs_non_overlapping,
        max_skew_seconds=max_channel_skew_seconds,
        uncertainty_type=uncertainty_type, confidence=confidence,
    )
    return PowerObservation(
        input_channel=_channel_snapshot("input", input_channel),
        rails=tuple(_channel_snapshot(name, channel) for name, channel in sorted(rails.items())),
        workload=result["workload"], boundary=result["boundary"],
        input_power_w=result["input_power_w"],
        rail_power_w=tuple(sorted(result["rail_power_w"].items())),
        output_power_w=result["output_power_w"], balance_w=result["balance_w"],
        balance_interval_w=result["balance_interval_w"], classification=result["classification"],
        indeterminate_reasons=tuple(result["indeterminate_reasons"]),
        observed_skew_seconds=result["observed_skew_seconds"],
        max_skew_seconds=result["max_skew_seconds"],
        uncertainty_type=result["uncertainty_type"], confidence=result["confidence"],
    )


class IntegratedObservationSession:
    def __init__(self, session_id: str | None = None):
        if session_id is not None and (not isinstance(session_id, str) or not session_id.strip()):
            raise ValueError("session_id must be a non-empty string")
        self._session_id = session_id if session_id is not None else str(uuid.uuid4())
        self._observations: list[Observation] = []

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def observations(self) -> tuple[Observation, ...]:
        return tuple(self._observations)

    def record(self, *, syscon_timestamp: datetime, response: BatterySerialResponse,
               service_support: ServiceSupport, workload: str, boundary: str,
               input_channel: Channel, rails: dict[str, Channel],
               attestations: CoverageAttestations, max_channel_skew_seconds: float,
               max_association_skew_seconds: float, uncertainty_type: UncertaintyType | None,
               confidence: float = 0.95) -> Observation:
        association_limit = _limit(max_association_skew_seconds)
        syscon = observe_syscon(timestamp=syscon_timestamp, response=response,
                                service_support=service_support)
        power = observe_power(workload=workload, boundary=boundary, input_channel=input_channel,
                              rails=rails, attestations=attestations,
                              max_channel_skew_seconds=max_channel_skew_seconds,
                              uncertainty_type=uncertainty_type, confidence=confidence)
        times = [syscon.timestamp, power.input_channel.timestamp,
                 *(channel.timestamp for channel in power.rails)]
        skew = (max(times) - min(times)).total_seconds()
        observation = Observation(self._session_id, syscon, power, attestations, skew,
                                  association_limit, skew <= association_limit)
        self._observations.append(observation)
        return observation


if __name__ == "__main__":
    from psp_syscon_model import ResultStatus

    now = datetime.now(timezone.utc)
    record = IntegratedObservationSession("mock-example").record(
        syscon_timestamp=now,
        response=BatterySerialResponse(ResultStatus.SUCCESS, 7, b"\xff" * 4),
        service_support=ServiceSupport.UNKNOWN,
        workload="illustrative", boundary="example power boundary",
        input_channel=Channel(now, 3.62, 0.85, 2),
        rails={"core": Channel(now, 1.2, 1, 3)},
        attestations=CoverageAttestations(False, True),
        max_channel_skew_seconds=0.01,
        max_association_skew_seconds=0.01,
        uncertainty_type=UncertaintyType.CONSERVATIVE,
    )
    print(json.dumps(record.to_dict(), indent=2))
