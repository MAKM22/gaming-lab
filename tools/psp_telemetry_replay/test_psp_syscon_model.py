import unittest

from psp_boot_model import BootPath, ServiceSupport
from psp_syscon_model import (
    BATTERY_GET_SERIAL, BatterySerialRequest, BatterySerialResponse,
    ResultStatus, classify_response, decode_serial_response,
)


class SysconModelTests(unittest.TestCase):
    def test_logical_request(self):
        request = BatterySerialRequest()
        self.assertEqual((request.command, request.length), (BATTERY_GET_SERIAL, 2))
        self.assertEqual(request.command, 0x6C)

    def test_little_endian_and_service_identifier(self):
        response = BatterySerialResponse(ResultStatus.SUCCESS, 7, b"\x78\x56\x34\x12")
        self.assertEqual(decode_serial_response(response), 0x12345678)
        override = BatterySerialResponse(ResultStatus.SUCCESS, 7, b"\xff" * 4)
        self.assertEqual(decode_serial_response(override), 0xFFFFFFFF)
        self.assertEqual(classify_response(override, service_support=ServiceSupport.UNKNOWN),
                         BootPath.UNKNOWN)
        self.assertEqual(classify_response(override, service_support=ServiceSupport.SUPPORTED),
                         BootPath.SERVICE_CANDIDATE)

    def test_faults_and_unsupported_lengths(self):
        for status in (ResultStatus.TRANSPORT_ERROR, ResultStatus.UNSUPPORTED):
            with self.subTest(status=status), self.assertRaises(RuntimeError):
                decode_serial_response(BatterySerialResponse(status, None, b""))
        for length, data in ((4, b"\x01"), (6, b"\x01" * 3), (7, b"\x01" * 3),
                             (7, b"\x01" * 5), (True, b"\x01" * 4)):
            with self.subTest(length=length, data=data), self.assertRaises(ValueError):
                decode_serial_response(BatterySerialResponse(ResultStatus.SUCCESS, length, data))


if __name__ == "__main__":
    unittest.main()
