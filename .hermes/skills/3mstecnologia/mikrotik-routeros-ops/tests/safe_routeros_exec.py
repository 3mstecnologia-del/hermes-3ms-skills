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
    ALREADY_SATISFIED = "already-satisfied"


class MutationKind(str, Enum):
    ADD = "add"
    SET = "set"
    REMOVE = "remove"
    ENABLE = "enable"
    DISABLE = "disable"
    MOVE = "move"


class Presence(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    INCONCLUSIVE = "inconclusive"


CONTINUE_OUTCOMES = frozenset({Outcome.APPLIED, Outcome.ALREADY_SATISFIED})

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
_REDACT_KEY_SET = {k.lower() for k in _REDACT_KEYS}
_REDACT_KEY_ALT = {k.lower().replace("-", "") for k in _REDACT_KEYS}

_MUTATION_VERBS = ("add", "set", "remove", "enable", "disable", "move")
_KEY_PREFIX = re.compile(
    r"(?i)(?<![A-Za-z0-9_-])("
    + "|".join(re.escape(k) for k in sorted(_REDACT_KEYS, key=len, reverse=True))
    + r")(\s*[=:]\s*)"
)


class AggregatedMutationError(ValueError):
    """Raised when a step encodes more than one mutation."""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_correlation_id() -> str:
    return str(uuid.uuid4())


def _is_sensitive_key(key: str) -> bool:
    n = key.strip().lower().replace("_", "-")
    compact = n.replace("-", "")
    return n in _REDACT_KEY_SET or compact in _REDACT_KEY_ALT


def _skip_quoted(text: str, start: int) -> int:
    quote = text[start]
    i = start + 1
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text):
            i += 2
            continue
        if text[i] == quote:
            return i + 1
        i += 1
    return len(text)


def _skip_value(text: str, start: int) -> int:
    if start >= len(text):
        return start
    if text[start] in {"'", '"'}:
        return _skip_quoted(text, start)
    i = start
    while i < len(text) and not text[i].isspace():
        i += 1
    return i


def _extract_value(text: str, start: int) -> tuple[str, int]:
    end = _skip_value(text, start)
    raw = text[start:end]
    if len(raw) >= 2 and raw[0] in {"'", '"'} and raw[-1] == raw[0]:
        inner = raw[1:-1].replace("\\" + raw[0], raw[0])
        return inner, end
    return raw, end


def sanitize_evidence(text: Optional[str], extra_values: Optional[set[str]] = None) -> Optional[str]:
    """Redact secret-bearing literals, including quoted values with spaces."""
    if text is None:
        return None
    out: list[str] = []
    i = 0
    found_values: set[str] = set(extra_values or ())
    while i < len(text):
        m = _KEY_PREFIX.search(text, i)
        if not m:
            out.append(text[i:])
            break
        out.append(text[i : m.start()])
        out.append(f"{m.group(1)}=<REDACTED>")
        val, end = _extract_value(text, m.end())
        if val:
            found_values.add(val)
        i = end
    redacted = "".join(out)
    for secret in sorted(found_values, key=len, reverse=True):
        if secret and secret not in {"<REDACTED>", ""}:
            redacted = redacted.replace(secret, "<REDACTED>")
    return redacted


def _collect_sensitive_values(obj: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            if _is_sensitive_key(str(key)) and isinstance(value, str) and value:
                found.add(value)
            found.update(_collect_sensitive_values(value))
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            found.update(_collect_sensitive_values(item))
    elif isinstance(obj, str):
        i = 0
        while i < len(obj):
            m = _KEY_PREFIX.search(obj, i)
            if not m:
                break
            val, end = _extract_value(obj, m.end())
            if val:
                found.add(val)
            i = end
    return found


def sanitize_public(obj: Any, extra_values: Optional[set[str]] = None) -> Any:
    """Recursively sanitize any public payload."""
    secrets = set(extra_values or ())
    secrets.update(_collect_sensitive_values(obj))

    def walk(node: Any) -> Any:
        if node is None:
            return None
        if isinstance(node, dict):
            out: dict[str, Any] = {}
            for key, value in node.items():
                if _is_sensitive_key(str(key)):
                    out[key] = "<REDACTED>"
                else:
                    out[key] = walk(value)
            return out
        if isinstance(node, list):
            return [walk(v) for v in node]
        if isinstance(node, tuple):
            return tuple(walk(v) for v in node)
        if isinstance(node, str):
            return sanitize_evidence(node, secrets)
        return node

    return walk(obj)


def parse_property_line(text: str) -> dict[str, str]:
    """Parse RouterOS key=value fragments regardless of field order.

    Supports quoted values with spaces, single/double quotes, and `\\` line wrap.
    Omission of a key means the representation omitted it — not absence of config.
    """
    props: dict[str, str] = {}
    if not text:
        return props
    normalized = text.replace("\\\n", " ").replace("\\\r\n", " ")
    i = 0
    n = len(normalized)
    while i < n:
        while i < n and normalized[i].isspace():
            i += 1
        if i >= n:
            break
        key_start = i
        while i < n and normalized[i] not in "=: \t\n\r":
            i += 1
        key = normalized[key_start:i].strip().lower()
        while i < n and normalized[i].isspace():
            i += 1
        if i >= n or normalized[i] not in "=:":
            continue
        i += 1
        while i < n and normalized[i].isspace():
            i += 1
        value, i = _extract_value(normalized, i)
        if key:
            props[key] = value
    return props


def classify_compact_field(
    compact_props: dict[str, str],
    key: str,
    *,
    compact_known_to_project: bool,
) -> Presence:
    if key in compact_props and compact_props[key] != "":
        return Presence.PRESENT
    if not compact_known_to_project:
        return Presence.INCONCLUSIVE
    return Presence.ABSENT


def _unquoted_separators(command: str) -> list[str]:
    seps: list[str] = []
    i = 0
    while i < len(command):
        ch = command[i]
        if ch in {"'", '"'}:
            i = _skip_quoted(command, i)
            continue
        if ch == ";" or (ch == "\n" and (i == 0 or command[i - 1] != "\\")):
            seps.append(ch)
        i += 1
    return seps


def assert_single_mutation(command: str) -> None:
    """Reject aggregated SSH/CLI mutation blocks before any executor call."""
    if not command or not command.strip():
        raise AggregatedMutationError("empty command")
    lowered = command.lower()
    if "&&" in command or "||" in command:
        raise AggregatedMutationError("shell chaining is not a single mutation")
    seps = _unquoted_separators(command)
    if seps:
        raise AggregatedMutationError("command aggregation separators are forbidden")
    verb_hits = 0
    for verb in _MUTATION_VERBS:
        verb_hits += len(re.findall(rf"(?i)(?<![A-Za-z0-9_-]){re.escape(verb)}(?![A-Za-z0-9_-])", lowered))
    if verb_hits > 1:
        raise AggregatedMutationError("multiple mutation verbs in one step")


def default_postcondition(kind: MutationKind) -> tuple[bool, bool]:
    if kind is MutationKind.REMOVE:
        return False, True
    return True, False


@dataclass
class ExecutionResult:
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

    def execution_failed(self) -> bool:
        if self.transport_ok is False:
            return True
        if self.exit_status not in (0, None):
            return True
        return self.cli_error_text()

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
    source: str
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
class MutationStep:
    sanitized_command: str
    kind: MutationKind
    expected: dict[str, str]
    critical_keys: tuple[str, ...]
    compact_known_keys: frozenset[str] = field(default_factory=frozenset)
    identity_key: Optional[str] = None
    must_exist: Optional[bool] = None
    must_be_absent: Optional[bool] = None

    def __post_init__(self) -> None:
        exist, absent = default_postcondition(self.kind)
        if self.must_exist is None:
            self.must_exist = exist
        if self.must_be_absent is None:
            self.must_be_absent = absent
        if self.must_exist and self.must_be_absent:
            raise ValueError("must_exist and must_be_absent are mutually exclusive")


@dataclass
class MutationEvidence:
    correlation_id: str
    order: int
    started_at: str
    finished_at: str
    sanitized_command: str
    kind: str
    executed: bool
    transport_ok: Optional[bool]
    exit_status: Optional[int]
    stdout: Optional[str]
    stderr: Optional[str]
    outcome: Outcome
    expected: dict[str, str]
    pre_state: dict[str, str]
    observed: dict[str, str]
    rollback_permitted: bool
    rollback_plan: Optional[str] = None
    notes: str = ""

    def to_public_dict(self) -> dict[str, Any]:
        payload = {
            "correlation_id": self.correlation_id,
            "order": self.order,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "sanitized_command": self.sanitized_command,
            "kind": self.kind,
            "executed": self.executed,
            "transport_ok": self.transport_ok,
            "exit_status": self.exit_status,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "outcome": self.outcome.value,
            "expected": dict(self.expected),
            "pre_state": dict(self.pre_state),
            "observed": dict(self.observed),
            "rollback_permitted": self.rollback_permitted,
            "rollback_plan": self.rollback_plan,
            "notes": self.notes,
        }
        return sanitize_public(payload)


@dataclass
class SequenceReport:
    correlation_id: str
    evidences: list[MutationEvidence]
    stopped: bool
    stop_reason: Optional[str]

    @property
    def outcomes(self) -> list[Outcome]:
        return [e.outcome for e in self.evidences]


Reader = Callable[[MutationStep, str], tuple[StateSnapshot, Optional[StateSnapshot]]]
Executor = Callable[[str], ExecutionResult]


def safe_projection(step: MutationStep, properties: dict[str, str]) -> dict[str, str]:
    allowed = set(step.critical_keys) | set(step.expected)
    if step.identity_key:
        allowed.add(step.identity_key)
    if step.kind in {MutationKind.ENABLE, MutationKind.DISABLE}:
        allowed.add("disabled")
    if step.kind is MutationKind.MOVE:
        allowed.update({"place-before", "order"})
    out = {}
    for key, value in properties.items():
        if key in allowed and not _is_sensitive_key(key):
            out[key] = value
    return out


def identity_value(step: MutationStep) -> Optional[str]:
    if not step.identity_key:
        return None
    return step.expected.get(step.identity_key)


def identity_present(properties: dict[str, str], step: MutationStep) -> bool:
    key = step.identity_key
    if not key:
        return bool(properties)
    wanted = identity_value(step)
    if wanted is None:
        return key in properties
    return properties.get(key) == wanted


def reconcile_state(
    compact: StateSnapshot,
    detail: Optional[StateSnapshot],
    keys: tuple[str, ...],
) -> tuple[dict[str, str], Presence, str]:
    """Merge compact + deterministic secondary read.

    Precedence is conservative and order-independent: any remaining
    INCONCLUSIVE critical attribute keeps the aggregate inconclusive.
    """
    observed: dict[str, str] = dict(compact.properties)
    notes: list[str] = []
    flags: list[Presence] = []

    for key in keys:
        p = compact.presence(key)
        if p is Presence.PRESENT:
            observed[key] = compact.properties[key]
            flags.append(Presence.PRESENT)
            continue
        if p is Presence.INCONCLUSIVE:
            notes.append(f"compact omitted {key}; secondary required")
            if detail is None:
                flags.append(Presence.INCONCLUSIVE)
                continue
            dp = detail.presence(key)
            if dp is Presence.PRESENT:
                observed[key] = detail.properties[key]
                flags.append(Presence.PRESENT)
                notes.append(f"secondary confirmed {key}")
            elif dp is Presence.ABSENT:
                flags.append(Presence.ABSENT)
                notes.append(f"secondary confirmed absence of {key}")
            else:
                flags.append(Presence.INCONCLUSIVE)
            continue
        if detail is not None:
            dp = detail.presence(key)
            if dp is Presence.PRESENT:
                observed[key] = detail.properties[key]
                flags.append(Presence.PRESENT)
                notes.append(f"secondary overrode compact absence for {key}")
            else:
                flags.append(Presence.ABSENT)
        else:
            flags.append(Presence.ABSENT)

    if detail is not None:
        for key, value in detail.properties.items():
            observed.setdefault(key, value)

    if Presence.INCONCLUSIVE in flags:
        missing_as = Presence.INCONCLUSIVE
    elif Presence.ABSENT in flags:
        missing_as = Presence.ABSENT
    else:
        missing_as = Presence.PRESENT
    return observed, missing_as, "; ".join(notes)


def expected_matches(expected: dict[str, str], observed: dict[str, str]) -> bool:
    for key, value in expected.items():
        if _is_sensitive_key(key):
            continue
        if observed.get(key) != value:
            return False
    return True


def postcondition_satisfied(
    step: MutationStep,
    observed: dict[str, str],
    missing_presence: Presence,
) -> tuple[Optional[bool], str]:
    if missing_presence is Presence.INCONCLUSIVE:
        return None, "inconclusive critical attribute"
    present = identity_present(observed, step)
    if step.must_be_absent:
        if present:
            return False, "object still present"
        return True, "object absent as required"
    if not present:
        return False, "object absent"
    if not expected_matches(step.expected, observed):
        return False, "properties diverge from expected"
    return True, "post-condition satisfied"


def execution_reported_failure(execution: ExecutionResult) -> bool:
    return execution.execution_failed()


def classify_mutation(
    *,
    step: MutationStep,
    execution: ExecutionResult,
    pre: dict[str, str],
    observed: dict[str, str],
    missing_presence: Presence,
    pre_ok: Optional[bool],
    post_ok: Optional[bool],
) -> tuple[Outcome, bool, Optional[str], str]:
    """Classify one executed mutation using pre/post delta.

    failed-after-apply requires a confirmed transition into the post-condition.
    Rollback requires ownership: this attempt created or changed the object.
    """
    if not execution.evidence_complete() or execution.exit_status is None:
        return (
            Outcome.INDETERMINATE,
            False,
            None,
            "missing exit status, stdout, stderr, or transport result",
        )
    if post_ok is None:
        return (
            Outcome.INDETERMINATE,
            False,
            None,
            "inconclusive read; do not rollback or continue",
        )

    failed = execution_reported_failure(execution)
    delta_into_goal = pre_ok is False and post_ok is True
    created = not identity_present(pre, step) and identity_present(observed, step)
    removed = identity_present(pre, step) and not identity_present(observed, step)
    changed = identity_present(pre, step) and identity_present(observed, step) and pre != observed

    rollback_plan: Optional[str] = None
    if created:
        ident = identity_value(step)
        if step.identity_key and ident:
            rollback_plan = f"/{_path_hint(step)} remove [find {step.identity_key}={ident}]"
    elif removed and pre:
        rollback_plan = f"re-add from pre-state projection ({step.identity_key}={pre.get(step.identity_key or '', '')})"
    elif changed:
        rollback_plan = f"set [find {step.identity_key}={pre.get(step.identity_key or '', '')}] restore pre-state"

    if post_ok:
        if failed and delta_into_goal:
            return (
                Outcome.FAILED_AFTER_APPLY,
                False,
                None,
                "post-state matches expected after a confirmed pre→post delta, but execution reported failure",
            )
        if failed and pre_ok is True:
            return (
                Outcome.ALREADY_SATISFIED,
                False,
                None,
                "execution failed but pre-state already satisfied the post-condition; not attributed as apply",
            )
        if not failed:
            return Outcome.APPLIED, False, None, "post-state matches expected"
        return (
            Outcome.FAILED_AFTER_APPLY if delta_into_goal else Outcome.INDETERMINATE,
            False,
            None,
            "execution reported failure; apply attributed only with confirmed delta",
        )

    if step.must_be_absent and identity_present(observed, step):
        return (
            Outcome.MISMATCH,
            bool(rollback_plan),
            rollback_plan,
            "remove did not make the object absent",
        )
    if step.must_exist and not identity_present(observed, step):
        if missing_presence is Presence.ABSENT:
            return (
                Outcome.NOT_APPLIED,
                False,
                None,
                "authoritative read confirms expected object is absent",
            )
        return (
            Outcome.MISMATCH,
            bool(rollback_plan),
            rollback_plan,
            "post-state diverges from expected",
        )
    if missing_presence is Presence.ABSENT and not identity_present(observed, step):
        return (
            Outcome.NOT_APPLIED,
            False,
            None,
            "authoritative read confirms expected attributes are absent",
        )
    return (
        Outcome.MISMATCH,
        bool(rollback_plan),
        rollback_plan,
        "post-state diverges from expected; rollback only with confirmed ownership delta",
    )


def _path_hint(step: MutationStep) -> str:
    cmd = step.sanitized_command.strip()
    if cmd.startswith("/"):
        parts = cmd.split()
        if parts:
            return parts[0].lstrip("/")
    return "item"


def prestate_decision(
    step: MutationStep,
    pre_observed: dict[str, str],
    pre_missing: Presence,
) -> tuple[str, Optional[bool], str]:
    pre_ok, note = postcondition_satisfied(step, pre_observed, pre_missing)
    if pre_ok is True:
        return "already-satisfied", True, note
    if step.kind is MutationKind.ADD and identity_present(pre_observed, step):
        return "identity-mismatch", False, "identity exists with divergent attributes; will not add again"
    return "execute", pre_ok, note


def rollback_allowed(evidence: MutationEvidence) -> bool:
    return (
        evidence.rollback_permitted
        and evidence.executed
        and evidence.rollback_plan is not None
        and evidence.outcome is Outcome.MISMATCH
    )


def safe_routeros_exec(
    steps: list[MutationStep],
    *,
    executor: Executor,
    reader: Reader,
    correlation_id: Optional[str] = None,
) -> SequenceReport:
    cid = correlation_id or new_correlation_id()
    evidences: list[MutationEvidence] = []
    stopped = False
    stop_reason: Optional[str] = None

    for order, step in enumerate(steps, start=1):
        started = utcnow().isoformat()
        try:
            assert_single_mutation(step.sanitized_command)
        except AggregatedMutationError as exc:
            finished = utcnow().isoformat()
            evidences.append(
                MutationEvidence(
                    correlation_id=cid,
                    order=order,
                    started_at=started,
                    finished_at=finished,
                    sanitized_command=step.sanitized_command,
                    kind=step.kind.value,
                    executed=False,
                    transport_ok=None,
                    exit_status=None,
                    stdout=None,
                    stderr=None,
                    outcome=Outcome.INDETERMINATE,
                    expected=dict(step.expected),
                    pre_state={},
                    observed={},
                    rollback_permitted=False,
                    notes=f"aggregated mutation rejected before executor: {exc}",
                )
            )
            stopped = True
            stop_reason = f"order={order} outcome=indeterminate: aggregated mutation rejected"
            break

        compact_pre, detail_pre = reader(step, "pre")
        pre_obs, pre_missing, pre_note = reconcile_state(
            compact_pre, detail_pre, step.critical_keys
        )
        pre_stored = safe_projection(step, pre_obs)
        decision, pre_ok, decision_note = prestate_decision(step, pre_stored, pre_missing)

        if decision == "already-satisfied":
            finished = utcnow().isoformat()
            evidences.append(
                MutationEvidence(
                    correlation_id=cid,
                    order=order,
                    started_at=started,
                    finished_at=finished,
                    sanitized_command=step.sanitized_command,
                    kind=step.kind.value,
                    executed=False,
                    transport_ok=None,
                    exit_status=None,
                    stdout=None,
                    stderr=None,
                    outcome=Outcome.ALREADY_SATISFIED,
                    expected=dict(step.expected),
                    pre_state=pre_stored,
                    observed=dict(pre_stored),
                    rollback_permitted=False,
                    notes=f"no-op reconciled: {decision_note}; executed=false",
                )
            )
            continue

        if decision == "identity-mismatch":
            finished = utcnow().isoformat()
            evidences.append(
                MutationEvidence(
                    correlation_id=cid,
                    order=order,
                    started_at=started,
                    finished_at=finished,
                    sanitized_command=step.sanitized_command,
                    kind=step.kind.value,
                    executed=False,
                    transport_ok=None,
                    exit_status=None,
                    stdout=None,
                    stderr=None,
                    outcome=Outcome.MISMATCH,
                    expected=dict(step.expected),
                    pre_state=pre_stored,
                    observed=dict(pre_stored),
                    rollback_permitted=False,
                    notes=f"{decision_note}; plan a dedicated set after reconciliation",
                )
            )
            stopped = True
            stop_reason = f"order={order} outcome=mismatch: identity exists with divergent attributes"
            break

        execution = executor(step.sanitized_command)
        compact_post, detail_post = reader(step, "post")
        observed, missing, recon_note = reconcile_state(
            compact_post, detail_post, step.critical_keys
        )
        stored = safe_projection(step, observed)
        post_ok, post_note = postcondition_satisfied(step, stored, missing)
        outcome, rollback_ok, rollback_plan, note = classify_mutation(
            step=step,
            execution=execution,
            pre=pre_stored,
            observed=stored,
            missing_presence=missing,
            pre_ok=pre_ok,
            post_ok=post_ok,
        )
        finished = utcnow().isoformat()
        ev = MutationEvidence(
            correlation_id=cid,
            order=order,
            started_at=started,
            finished_at=finished,
            sanitized_command=step.sanitized_command,
            kind=step.kind.value,
            executed=True,
            transport_ok=execution.transport_ok,
            exit_status=execution.exit_status,
            stdout=execution.stdout,
            stderr=execution.stderr,
            outcome=outcome,
            expected=dict(step.expected),
            pre_state=pre_stored,
            observed=stored,
            rollback_permitted=rollback_ok,
            rollback_plan=rollback_plan,
            notes="; ".join(p for p in (pre_note, recon_note, post_note, note) if p),
        )
        evidences.append(ev)
        if outcome in CONTINUE_OUTCOMES:
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
