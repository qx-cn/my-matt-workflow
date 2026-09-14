import unittest

from tools.workflow_lib.evidence_records import (
    canonical_evidence_bytes,
    evidence_identifier,
    validate_evidence_bytes,
    validate_evidence_receipt,
)


class EvidenceRecordTests(unittest.TestCase):
    def test_record_identity_is_stable_and_round_trips(self):
        record = {"kind": "test", "status": "pass", "exit_code": 0}
        identifier = evidence_identifier(record)
        raw = canonical_evidence_bytes(record) + b"\n"
        self.assertEqual(record, validate_evidence_bytes(raw, identifier, "test"))

    def test_receipt_rejects_wrong_kind_and_non_hex_identifier(self):
        for receipt in (
            {"kind": "review", "evidence_id": "0" * 64},
            {"kind": "test", "evidence_id": "z" * 64},
        ):
            with self.subTest(receipt=receipt):
                with self.assertRaisesRegex(ValueError, "test_receipt"):
                    validate_evidence_receipt(receipt, "test")

    def test_record_rejects_noncanonical_or_drifted_bytes(self):
        record = {"kind": "test", "status": "pass"}
        identifier = evidence_identifier(record)
        for raw in (
            b'{"status":"pass","kind":"test"}\n',
            canonical_evidence_bytes({"kind": "test", "status": "fail"}) + b"\n",
        ):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(ValueError, "已漂移"):
                    validate_evidence_bytes(raw, identifier, "test")


if __name__ == "__main__":
    unittest.main()
