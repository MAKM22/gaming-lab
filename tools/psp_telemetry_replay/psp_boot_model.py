"""Mock PSP battery-ID decision model. No real serial or EEPROM access.

The four-byte encoding is an explicit simulation convention, not a claim about
the wire protocol or the actual location or layout of any battery EEPROM.
"""

from dataclasses import dataclass
from enum import Enum

SERVICE_ID = 0xFFFFFFFF


class ServiceSupport(Enum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


class BootPath(Enum):
    NORMAL_CANDIDATE = "normal_boot_candidate"
    SERVICE_CANDIDATE = "service_boot_candidate"
    SERVICE_UNSUPPORTED = "service_mode_unsupported"
    UNKNOWN = "unknown"


def _validate_id(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0xFFFFFFFF:
        raise ValueError("battery identifier must be an unsigned 32-bit integer")
    return value


def _validate_byteorder(byteorder: str) -> None:
    if byteorder not in ("big", "little"):
        raise ValueError("byteorder must be 'big' or 'little'")


def encode_id(value: int, *, byteorder: str) -> bytes:
    _validate_byteorder(byteorder)
    return _validate_id(value).to_bytes(4, byteorder)


def decode_id(data: bytes, *, byteorder: str) -> int:
    _validate_byteorder(byteorder)
    if not isinstance(data, bytes) or len(data) != 4:
        raise ValueError("identifier payload must be exactly four bytes")
    return int.from_bytes(data, byteorder)


@dataclass
class MockBattery:
    """In-memory mock only; writes never access or persist to a real device."""
    identifier: int

    def __post_init__(self):
        self.identifier = _validate_id(self.identifier)

    def read(self, *, byteorder: str) -> bytes:
        return encode_id(self.identifier, byteorder=byteorder)

    def write(self, payload: bytes, *, byteorder: str) -> None:
        self.identifier = decode_id(payload, byteorder=byteorder)


def select_boot_path(payload: bytes | None, *, byteorder: str,
                     service_support: ServiceSupport) -> BootPath:
    """Classify a supplied mock ID; no firmware is loaded or authenticated."""
    _validate_byteorder(byteorder)
    if not isinstance(service_support, ServiceSupport):
        raise ValueError("service_support must be a ServiceSupport value")
    if payload is None:
        return BootPath.UNKNOWN
    try:
        identifier = decode_id(payload, byteorder=byteorder)
    except ValueError:
        return BootPath.UNKNOWN
    if identifier == SERVICE_ID:
        if service_support is ServiceSupport.SUPPORTED:
            return BootPath.SERVICE_CANDIDATE
        if service_support is ServiceSupport.UNSUPPORTED:
            return BootPath.SERVICE_UNSUPPORTED
        return BootPath.UNKNOWN
    if identifier == 0:
        # Other special IDs, including reported auto-boot behavior, need
        # model-specific evidence and are deliberately not classified.
        return BootPath.UNKNOWN
    return BootPath.NORMAL_CANDIDATE


if __name__ == "__main__":
    battery = MockBattery(0x12345678)
    for label, payload in (
        ("example identifier", battery.read(byteorder="big")),
        ("service identifier", encode_id(SERVICE_ID, byteorder="big")),
    ):
        outcome = select_boot_path(payload, byteorder="big",
                                   service_support=ServiceSupport.UNKNOWN)
        print(f"{label}: {payload.hex().upper()} -> {outcome.value}")
    print("Mock only: card contents, authentication, and boot success are not modeled.")
