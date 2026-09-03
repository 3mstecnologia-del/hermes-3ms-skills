"""Atomic RouterOS SSH mutation contract (executable specification).

Not a live SSH client. Hermes and any future fleet/orchestration consumer
must follow this state machine for mutable RouterOS operations.

One mutation per evidence boundary. Capture transport, exit status, stdout
and stderr independently. Reconcile authoritative post-state before the
next mutation or any rollback.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional


class Outcome(str, Enum):
    APPLIED = "applied"
    NOT_APPLIED = "not-applied"
    FAILED_AFTER_APPLY = "failed-after-apply"
    INDETERMINATE = "indeterminate"
    MISMATCH = "mismatch"


class Presence(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    INCONCLUSIVE = "inconclusive"


# Placeholders only — never match real operational values in public tests.
_REDACT_KEYS = (
    "password",
    "passphrase",
    "secret",
    "token",
    "community",
    "private-key",
    "preshared-key",
    "psk",
    "api-key",
)
_REDACT_KV = re.compile(
    r"(?i)\b(" + "|".join(re.escape(k) for k in _REDACT_KEYS) + r")\s*[=:]\s*\S+"
)
_REDACT_WG_KEYISH = re.compile(
    r"(?i)\b(private-key|preshared-key)\s*=\s*[A-Za-z0-9+/=]{20,}"
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_correlation_id() -> str:
    return str(uuid.uuid4())


def sanitize_evidence(text: Optional[str]) -> Optional[str]:
    """Remove secret-bearing literals before persistence or reports."""
    if text is None:
        return None
    redacted = _REDACT_WG_KEYISH.sub(lambda m: f"{m.group(1)}=<REDACTED>", text)
    redacted = _REDACT_KV.sub(lambda m: f"{m.group(1)}=<REDACTED>", redacted)
    return redacted


def parse_property_line(text: str) -> dict[str, str]:
    """Parse RouterOS key=value fragments regardless of field order.

    Compact `print` and `print detail` / `get` differ in which keys appear.
    Absence of a key in the parsed dict means the representation omitted it,
    not that the configuration lacks the attribute.
    """
    props: dict[str, str] = {}
    if not text:
        return props
    for part in text.replace("\n", " ").split():
        if "=" not in part:
            continue
        key, _, value = part.partition("=")
        key = key.strip().lower()
        if not key:
            continue
        props[key] = value.strip().strip('"')
    return props


def classify_compact_field(
    compact_props: dict[str, str],
    key: str,
    *,
    compact_known_to_project: bool,
) -> Presence:
    """Classify a critical attribute from a compact representation.

    If the compact form is not documented as projecting this key, omission
    is INCONCLUSIVE — never ABSENT.
    """
    if key in compact_props and compact_props[key] != "":
        return Presence.PRESENT
    if not compact_known_to_project:
        return Presence.INCONCLUSIVE
    return Presence.ABSENT


@dataclass
class ExecutionResult:
    """One SSH mutation attempt. All four evidence fields are required for certainty."""

    transport_ok: Optional[bool]
    exit_status: Optional[int]
    stdout: Optional[str]
    stderr: Optional[str]

    def evidence_complete(self) -> bool:
        return (
            self.transport_ok is not None
            and self.exit_status is not None
            and self.stdout is not None
            and self.stderr is not None
        )

    def cli_error_text(self) -> bool:
        blob = f"{self.stdout or ''}\n{self.stderr or ''}".lower()
        markers = (
            "bad command name",
            "syntax error",
            "expected end of command",
            "failure:",
            "no such item",
            "invalid value",
        )
        return any(m in blob for m in markers)


@dataclass
class StateSnapshot:
    source: str  # compact | detail | get | pre
    properties: dict[str, str]
    compact_known_keys: frozenset[str] = field(default_factory=frozenset)

    def presence(self, key: str) -> Presence:
        if self.source == "compact":
            return classify_compact_field(
                self.properties,
                key,
                compact_known_to_project=key in self.compact_known_keys,
            )
        if key in self.properties and self.properties[key] != "":
            return Presence.PRESENT
        return Presence.ABSENT


@dataclass
class MutationEvidence:
    correlation_id: str
    order: int
    started_at: str
    finished_at: str
    sanitized_command: str
    transport_ok: Optional[bool]
    exit_status: Optional[int]
    stdout: Optional[str]
    stderr: Optional[str]
    outcome: Outcome
    expected: dict[str, str]
    observed: dict[str, str]
    rollback_permitted: bool
    notes: str = ""

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "correlation_id": self.correlation_id,
            "order": self.order,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "sanitized_command": sanitize_evidence(self.sanitized_command),
            "transport_ok": self.transport_ok,
            "exit_status": self.exit_status,
            "stdout": sanitize_evidence(self.stdout),
            "stderr": sanitize_evidence(self.stderr),
            "outcome": self.outcome.value,
            "expected": self.expected,
            "observed": {k: sanitize_evidence(v) or "" for k, v in self.observed.items()},
            "rollback_permitted": self.rollback_permitted,
            "notes": self.notes,
        }


@dataclass
class MutationStep:
    sanitized_command: str
    expected: dict[str, str]
    critical_keys: tuple[str, ...]
    compact_known_keys: frozenset[str] = field(default_factory=frozenset)
    identity_key: Optional[str] = None


@dataclass
class SequenceReport:
    correlation_id: str
    evidences: list[MutationEvidence]
    stopped: bool
    stop_reason: Optional[str]

    @property
    def outcomes(self) -> list[Outcome]:
        return [e.outcome for e in self.evidences]


# Reader: (step, phase) -> compact snapshot, optional detail snapshot
Reader = Callable[[MutationStep, str], tuple[StateSnapshot, Optional[StateSnapshot]]]
# Executor: sanitized command -> ExecutionResult
Executor = Callable[[str], ExecutionResult]


def reconcile_state(
    compact: StateSnapshot,
    detail: Optional[StateSnapshot],
    keys: tuple[str, ...],
) -> tuple[dict[str, str], Presence, str]:
    """Merge compact + deterministic secondary read for critical keys.

    Returns (observed_properties, worst_presence_for_missing_expected, note).
    """
    observed: dict[str, str] = dict(compact.properties)
    notes: list[str] = []
    missing_as: Presence = Presence.PRESENT

    for key in keys:
        p = compact.presence(key)
        if p is Presence.PRESENT:
            observed[key] = compact.properties[key]
            continue
        if p is Presence.INCONCLUSIVE:
            notes.append(f"compact omitted {key}; secondary required")
            if detail is None:
                missing_as = Presence.INCONCLUSIVE
                continue
            dp = detail.presence(key)
            if dp is Presence.PRESENT:
                observed[key] = detail.properties[key]
                notes.append(f"secondary confirmed {key}")
            elif dp is Presence.ABSENT:
                missing_as = Presence.ABSENT
                notes.append(f"secondary confirmed absence of {key}")
            else:
                missing_as = Presence.INCONCLUSIVE
            continue
        # compact ABSENT (only when the compact form is known to project the key)
        if detail is not None:
            dp = detail.presence(key)
            if dp is Presence.PRESENT:
                observed[key] = detail.properties[key]
                notes.append(f"secondary overrode compact absence for {key}")
            else:
                missing_as = Presence.ABSENT
        else:
            missing_as = Presence.ABSENT

    if detail is not None:
        for key, value in detail.properties.items():
            observed.setdefault(key, value)

    return observed, missing_as, "; ".join(notes)


def expected_matches(expected: dict[str, str], observed: dict[str, str]) -> bool:
    for key, value in expected.items():
        if observed.get(key) != value:
            return False
    return True


def classify_mutation(
    execution: ExecutionResult,
    expected: dict[str, str],
    observed: dict[str, str],
    missing_presence: Presence,
) -> tuple[Outcome, bool, str]:
    """Classify one mutation. Exit status alone never proves apply/no-apply.

    rollback_permitted is True only after confirmed state divergence
    (we know what is present). Never on indeterminate/inconclusive.
    """
    match = expected_matches(expected, observed)

    if not execution.evidence_complete() or execution.transport_ok is None:
        if execution.exit_status is None or not execution.evidence_complete():
            return (
                Outcome.INDETERMINATE,
                False,
                "missing exit status, stdout, stderr, or transport result",
            )

    if missing_presence is Presence.INCONCLUSIVE and not match:
        return (
            Outcome.INDETERMINATE,
            False,
            "inconclusive read; do not rollback or continue",
        )

    if match:
        if execution.transport_ok is False or (
            execution.exit_status not in (0, None) or execution.cli_error_text()
        ):
            # Applied despite non-zero / CLI noise — do not claim "nothing happened".
            return (
                Outcome.FAILED_AFTER_APPLY,
                False,
                "post-state matches expected but execution reported failure",
            )
        if execution.exit_status == 0 and execution.transport_ok:
            return Outcome.APPLIED, False, "post-state matches expected"
        # transport_ok True, exit 0 already handled; leftover is applied-like
        return Outcome.APPLIED, False, "post-state matches expected"

    # No match
    if missing_presence is Presence.ABSENT:
        return (
            Outcome.NOT_APPLIED,
            False,
            "authoritative read confirms expected attributes are absent",
        )
    return (
        Outcome.MISMATCH,
        True,
        "post-state diverges from expected; stop sequence; rollback only of confirmed objects",
    )


def prestate_blocks_duplicate(pre: StateSnapshot, step: MutationStep) -> bool:
    """Idempotent guard: if identity already exists, do not create again."""
    key = step.identity_key
    if not key:
        return False
    expected_id = step.expected.get(key)
    if expected_id is None:
        return False
    return pre.properties.get(key) == expected_id


def safe_routeros_exec(
    steps: list[MutationStep],
    *,
    executor: Executor,
    reader: Reader,
    correlation_id: Optional[str] = None,
) -> SequenceReport:
    """Run mutations one evidence boundary at a time.

    Stops before the next mutation on error, mismatch, missing evidence,
    or failed-after-apply. Does not invoke rollback.
    """
    cid = correlation_id or new_correlation_id()
    evidences: list[MutationEvidence] = []
    stopped = False
    stop_reason: Optional[str] = None

    for order, step in enumerate(steps, start=1):
        started = utcnow().isoformat()
        compact_pre, _detail_pre = reader(step, "pre")

        if prestate_blocks_duplicate(compact_pre, step):
            finished = utcnow().isoformat()
            evidences.append(
                MutationEvidence(
                    correlation_id=cid,
                    order=order,
                    started_at=started,
                    finished_at=finished,
                    sanitized_command=step.sanitized_command,
                    transport_ok=None,
                    exit_status=None,
                    stdout=None,
                    stderr=None,
                    outcome=Outcome.APPLIED,
                    expected=step.expected,
                    observed=dict(compact_pre.properties),
                    rollback_permitted=False,
                    notes="pre-state already satisfies identity; mutation skipped (idempotent)",
                )
            )
            continue

        execution = executor(step.sanitized_command)
        compact_post, detail_post = reader(step, "post")
        observed, missing, recon_note = reconcile_state(
            compact_post, detail_post, step.critical_keys
        )
        # Safe projection: store only expected + critical keys, never a broad dump
        stored = {k: observed[k] for k in step.critical_keys if k in observed}
        stored.update({k: observed[k] for k in step.expected if k in observed})

        outcome, rollback_ok, note = classify_mutation(
            execution, step.expected, stored, missing
        )
        finished = utcnow().isoformat()
        ev = MutationEvidence(
            correlation_id=cid,
            order=order,
            started_at=started,
            finished_at=finished,
            sanitized_command=step.sanitized_command,
            transport_ok=execution.transport_ok,
            exit_status=execution.exit_status,
            stdout=sanitize_evidence(execution.stdout),
            stderr=sanitize_evidence(execution.stderr),
            outcome=outcome,
            expected=step.expected,
            observed=stored,
            rollback_permitted=rollback_ok,
            notes="; ".join(p for p in (recon_note, note) if p),
        )
        evidences.append(ev)

        if outcome is Outcome.APPLIED:
            continue
        stopped = True
        stop_reason = f"order={order} outcome={outcome.value}: {ev.notes}"
        break

    return SequenceReport(
        correlation_id=cid,
        evidences=evidences,
        stopped=stopped,
        stop_reason=stop_reason,
    )


def rollback_allowed(evidence: MutationEvidence) -> bool:
    """Blind rollback is forbidden. Only confirmed divergence may be undone."""
    return evidence.rollback_permitted and evidence.outcome is Outcome.MISMATCH
