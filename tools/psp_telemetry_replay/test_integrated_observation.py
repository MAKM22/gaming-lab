import unittest
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

from integrated_observation import CoverageAttestations, IntegratedObservationSession
from power_auditor import Channel, UncertaintyType
from psp_boot_model import ServiceSupport
from psp_syscon_model import BatterySerialResponse, ResultStatus

NOW = datetime(2026, 11, 9, tzinfo=timezone.utc)


def args():
    return dict(
        syscon_timestamp=NOW,
        response=BatterySerialResponse(ResultStatus.SUCCESS, 7, b"\xff" * 4),
        service_support=ServiceSupport.UNKNOWN,
        workload="idle", boundary="mock converter",
        input_channel=Channel(NOW, 4, 1, 1),
        rails={"core": Channel(NOW + timedelta(milliseconds=10), 2, 1, 2)},
        attestations=CoverageAttestations(False, True),
        max_channel_skew_seconds=0.02,
        max_association_skew_seconds=0.02,
        uncertainty_type=UncertaintyType.CONSERVATIVE,
    )


class IntegratedTests(unittest.TestCase):
    def test_adapter_outputs_and_attestation_authority(self):
        record = IntegratedObservationSession("one").record(**args())
        self.assertEqual(record.syscon.identifier, 0xFFFFFFFF)
        self.assertEqual(record.syscon.boot_path_candidate, "unknown")
        self.assertEqual(record.power.classification, "POSITIVE_UNACCOUNTED_POWER")
        self.assertFalse(record.attestations.coverage_complete)
        self.assertNotIn("coverage_complete", record.to_dict()["power"])
        self.assertFalse(record.causality_asserted)
        self.assertTrue(record.timestamps_within_limit)
        self.assertAlmostEqual(record.association_skew_seconds, 0.01)

    def test_snapshot_unchanged_after_mutation(self):
        session = IntegratedObservationSession("one")
        inputs = args()
        record = session.record(**inputs)
        inputs["rails"]["new"] = Channel(NOW, 100, 1, 1)
        exported = record.to_dict()
        exported["power"]["rails"][0]["voltage_v"] = 999
        self.assertEqual(len(record.power.rails), 1)
        self.assertEqual(record.power.rails[0].voltage_v, 2)
        self.assertEqual(len(session.observations), 1)
        with self.assertRaises(FrozenInstanceError):
            record.syscon.status = "modified"
        with self.assertRaises(FrozenInstanceError):
            record.power.rails[0].voltage_v = 9

    def test_cross_subsystem_and_power_skew_separate(self):
        values = args()
        values["syscon_timestamp"] = NOW - timedelta(seconds=1)
        record = IntegratedObservationSession().record(**values)
        self.assertFalse(record.timestamps_within_limit)
        self.assertAlmostEqual(record.association_skew_seconds, 1.01)
        self.assertEqual(record.power.classification, "POSITIVE_UNACCOUNTED_POWER")
        values["syscon_timestamp"] = NOW
        values["max_channel_skew_seconds"] = 0
        record = IntegratedObservationSession().record(**values)
        self.assertTrue(record.timestamps_within_limit)
        self.assertEqual(record.power.classification, "INDETERMINATE")

    def test_syscon_failure_and_atomic_recording(self):
        session = IntegratedObservationSession()
        values = args()
        values["response"] = BatterySerialResponse(ResultStatus.TRANSPORT_ERROR, None, b"")
        record = session.record(**values)
        self.assertEqual(record.syscon.status, "error")
        self.assertIsNone(record.syscon.identifier)
        self.assertIn("transport_error", record.syscon.error)
        values["syscon_timestamp"] = datetime(2026, 1, 1)
        with self.assertRaises(ValueError):
            session.record(**values)
        self.assertEqual(len(session.observations), 1)

    def test_unknown_coverage_and_invalid_limit(self):
        values = args()
        values["attestations"] = CoverageAttestations(None, True)
        record = IntegratedObservationSession().record(**values)
        self.assertEqual(record.power.classification, "INDETERMINATE")
        values["max_association_skew_seconds"] = float("nan")
        with self.assertRaises(ValueError):
            IntegratedObservationSession().record(**values)


if __name__ == "__main__":
    unittest.main()
