"""Pure content-addressed evidence record encoding and validation."""

from __future__ import annotations

import hashlib
import json


def canonical_evidence_bytes(record: dict[str, object]) -> bytes:
    """Encode one evidence record in its stable content-addressed form."""
    return json.dumps(
        record, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def evidence_identifier(record: dict[str, object]) -> str:
    """Return the identifier bound to the canonical record bytes."""
    return hashlib.sha256(canonical_evidence_bytes(record)).hexdigest()


def validate_evidence_receipt(
    receipt: object,
    kind: str,
    *,
    error_type: type[ValueError] = ValueError,
) -> str:
    """Validate the minimal runtime receipt and return its content id."""
    if (
        not isinstance(receipt, dict)
        or set(receipt) != {"kind", "evidence_id"}
        or receipt.get("kind") != kind
        or not isinstance(receipt.get("evidence_id"), str)
        or len(receipt["evidence_id"]) != 64
        or any(value not in "0123456789abcdef" for value in receipt["evidence_id"])
    ):
        raise error_type(f"completed outcome 必须引用 runtime 生成的 {kind}_receipt")
    return receipt["evidence_id"]


def validate_evidence_bytes(
    raw: bytes,
    evidence_id: str,
    kind: str,
    *,
    error_type: type[ValueError] = ValueError,
) -> dict[str, object]:
    """Decode canonical bytes and verify their content-addressed identity."""
    try:
        record = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise error_type(f"{kind} evidence record 无法读取") from exc
    if not isinstance(record, dict):
        raise error_type(f"{kind} evidence record 无法读取")
    canonical = canonical_evidence_bytes(record)
    if raw != canonical + b"\n" or hashlib.sha256(canonical).hexdigest() != evidence_id:
        raise error_type(f"{kind} evidence record 已漂移")
    return record
