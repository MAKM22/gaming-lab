"""Narrow mock of a CPU-to-SYSCON battery-serial API, not the battery bus.

The reverse-engineered uOFW source describes the command and response layout:
https://github.com/uofw/uofw/blob/f7b0623168842f02cddbdbf9437ac0c2380c51c8/include/syscon.h
https://github.com/uofw/uofw/blob/f7b0623168842f02cddbdbf9437ac0c2380c51c8/src/syscon/syscon.c#L2150-L2153
https://github.com/uofw/uofw/blob/f7b0623168842f02cddbdbf9437ac0c2380c51c8/src/syscon/syscon.c#L2180-L2208

Only the four-data-byte response is modeled. Transport, checksums, shorter
responses, hardware access, and PSP service boot are outside this model.
"""

from dataclasses import dataclass
from enum import Enum

from psp_boot_model import BootPath, ServiceSupport, select_boot_path

BATTERY_GET_SERIAL = 0x6C
REQUEST_LENGTH = 2
FOUR_BYTE_RESPONSE_LENGTH = 7


class ResultStatus(Enum):
    SUCCESS = "success"
    TRANSPORT_ERROR = "transport_error"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class BatterySerialRequest:
    """Logical request fields; not a complete transmittable packet."""
    command: int = BATTERY_GET_SERIAL
    length: int = REQUEST_LENGTH


@dataclass(frozen=True)
class BatterySerialResponse:
    """Data from an assumed transport, not raw wire-frame validation."""
    status: ResultStatus
    reported_length: int | None
    data: bytes


def decode_serial_response(response: BatterySerialResponse) -> int:
    """Return the unsigned bit pattern of a successful four-byte response."""
    if not isinstance(response, BatterySerialResponse):
        raise ValueError("expected a BatterySerialResponse")
    if not isinstance(response.status, ResultStatus):
        raise ValueError("unknown response status")
    if response.status is not ResultStatus.SUCCESS:
        raise RuntimeError(f"serial query failed: {response.status.value}")
    if (isinstance(response.reported_length, bool)
            or not isinstance(response.reported_length, int)
            or response.reported_length != FOUR_BYTE_RESPONSE_LENGTH):
        raise ValueError("only a reported response length of 7 is modeled")
    if not isinstance(response.data, bytes) or len(response.data) != 4:
        raise ValueError("expected exactly four response data bytes")
    return int.from_bytes(response.data, byteorder="little", signed=False)


def classify_response(response: BatterySerialResponse, *,
                      service_support: ServiceSupport) -> BootPath:
    """Pass the decoded value to the separate, explicitly hypothetical classifier."""
    value = decode_serial_response(response)
    return select_boot_path(value.to_bytes(4, byteorder="little"),
                            byteorder="little", service_support=service_support)
