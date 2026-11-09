import unittest

from psp_boot_model import (
    BootPath, MockBattery, SERVICE_ID, ServiceSupport, decode_id, encode_id,
    select_boot_path,
)


class BootModelTests(unittest.TestCase):
    def test_roundtrip_and_explicit_endianness(self):
        for order, expected in (("big", bytes.fromhex("12345678")),
                                ("little", bytes.fromhex("78563412"))):
            with self.subTest(order=order):
                self.assertEqual(encode_id(0x12345678, byteorder=order), expected)
                self.assertEqual(decode_id(expected, byteorder=order), 0x12345678)

    def test_service_compatibility_is_not_assumed(self):
        payload = encode_id(SERVICE_ID, byteorder="big")
        for support, outcome in (
            (ServiceSupport.SUPPORTED, BootPath.SERVICE_CANDIDATE),
            (ServiceSupport.UNSUPPORTED, BootPath.SERVICE_UNSUPPORTED),
            (ServiceSupport.UNKNOWN, BootPath.UNKNOWN),
        ):
            self.assertEqual(select_boot_path(payload, byteorder="big",
                                              service_support=support), outcome)

    def test_normal_missing_invalid_and_zero(self):
        def classify(payload):
            return select_boot_path(payload, byteorder="big",
                                    service_support=ServiceSupport.SUPPORTED)
        self.assertEqual(classify(bytes.fromhex("12345678")), BootPath.NORMAL_CANDIDATE)
        for payload in (None, b"", b"\xff" * 5, b"\x00" * 4):
            self.assertEqual(classify(payload), BootPath.UNKNOWN)

    def test_write_only_affects_mock_and_invalid_write_is_atomic(self):
        battery = MockBattery(0x12345678)
        with self.assertRaises(ValueError):
            battery.write(b"\xff", byteorder="big")
        self.assertEqual(battery.identifier, 0x12345678)
        battery.write(b"\xff" * 4, byteorder="big")
        self.assertEqual(battery.identifier, SERVICE_ID)

    def test_reject_invalid_configuration(self):
        for value in (-1, 2**32, True, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                MockBattery(value)
        with self.assertRaises(ValueError):
            decode_id(b"\x00" * 4, byteorder="native")
        with self.assertRaises(ValueError):
            select_boot_path(None, byteorder="big", service_support="supported")


if __name__ == "__main__":
    unittest.main()
