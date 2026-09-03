"""Unit tests for the atomic RouterOS SSH mutation contract.

Fixtures are synthetic. No live equipment, no real IPs, credentials, or keys.
"""

from __future__ import annotations

import unittest

from safe_routeros_exec import (
    ExecutionResult,
    MutationStep,
    Outcome,
    Presence,
    StateSnapshot,
    classify_compact_field,
    expected_matches,
    parse_property_line,
    rollback_allowed,
    safe_routeros_exec,
    sanitize_evidence,
)


def _step(
    cmd: str = "/interface wireguard add name=wg0 listen-port=51820 comment=lab",
    expected: dict | None = None,
    identity: str | None = "name",
) -> MutationStep:
    exp = expected or {"name": "wg0", "listen-port": "51820", "comment": "lab"}
    return MutationStep(
        sanitized_command=cmd,
        expected=exp,
        critical_keys=("name", "listen-port", "comment"),
        compact_known_keys=frozenset({"name", "listen-port"}),
        identity_key=identity,
    )


class Scripted:
    """Deterministic fake transport + reader for sequence tests."""

    def __init__(self, executions, posts, pres=None):
        self.executions = list(executions)
        self.posts = list(posts)
        self.pres = list(pres or [])
        self.exec_calls = 0
        self.commands: list[str] = []

    def execute(self, command: str) -> ExecutionResult:
        self.commands.append(command)
        self.exec_calls += 1
        return self.executions.pop(0)

    def reader(self, step: MutationStep, phase: str):
        if phase == "pre":
            if self.pres:
                return self.pres.pop(0)
            return StateSnapshot(source="compact", properties={}), None
        return self.posts.pop(0)


class ParseAndSanitizeTests(unittest.TestCase):
    def test_property_order_does_not_create_false_divergence(self):
        a = parse_property_line("name=wg0 listen-port=51820 comment=lab")
        b = parse_property_line("comment=lab listen-port=51820 name=wg0")
        self.assertEqual(a, b)
        self.assertTrue(expected_matches({"name": "wg0", "comment": "lab"}, a))

    def test_compact_omission_is_inconclusive_not_absent(self):
        compact = {"name": "wg0", "listen-port": "51820"}
        self.assertEqual(
            classify_compact_field(compact, "comment", compact_known_to_project=False),
            Presence.INCONCLUSIVE,
        )
        self.assertNotEqual(
            classify_compact_field(compact, "comment", compact_known_to_project=False),
            Presence.ABSENT,
        )

    def test_sanitize_redacts_secret_literals(self):
        raw = (
            "password=supersecret token=tok_abc123 community=public "
            "private-key=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= "
            "preshared-key=BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB="
        )
        cleaned = sanitize_evidence(raw)
        self.assertIsNotNone(cleaned)
        assert cleaned is not None
        for forbidden in (
            "supersecret",
            "tok_abc123",
            "public",
            "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
            "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB=",
        ):
            self.assertNotIn(forbidden, cleaned)
        self.assertIn("<REDACTED>", cleaned)


class SequenceContractTests(unittest.TestCase):
    def test_a_mutation_zero_and_state_correct_is_applied(self):
        """A: exit 0 + matching post-state → applied / PASS."""
        env = Scripted(
            executions=[
                ExecutionResult(True, 0, "", ""),
            ],
            posts=[
                (
                    StateSnapshot(
                        source="compact",
                        properties={"name": "wg0", "listen-port": "51820"},
                        compact_known_keys=frozenset({"name", "listen-port"}),
                    ),
                    StateSnapshot(
                        source="get",
                        properties={
                            "name": "wg0",
                            "listen-port": "51820",
                            "comment": "lab",
                        },
                    ),
                )
            ],
        )
        report = safe_routeros_exec(
            [_step()], executor=env.execute, reader=env.reader
        )
        self.assertEqual(report.outcomes, [Outcome.APPLIED])
        self.assertFalse(report.stopped)
        self.assertEqual(env.exec_calls, 1)

    def test_b_nonzero_exit_but_state_applied_is_failed_after_apply(self):
        """B: exit != 0 but post-state shows change → not 'nothing happened'."""
        env = Scripted(
            executions=[
                ExecutionResult(True, 1, "", "failure: late session error"),
            ],
            posts=[
                (
                    StateSnapshot(
                        source="compact",
                        properties={"name": "wg0", "listen-port": "51820"},
                    ),
                    StateSnapshot(
                        source="get",
                        properties={
                            "name": "wg0",
                            "listen-port": "51820",
                            "comment": "lab",
                        },
                    ),
                )
            ],
        )
        report = safe_routeros_exec(
            [_step(), _step("/ip address add address=10.0.0.1/24 interface=wg0")],
            executor=env.execute,
            reader=env.reader,
        )
        self.assertEqual(report.outcomes[0], Outcome.FAILED_AFTER_APPLY)
        self.assertTrue(report.stopped)
        self.assertEqual(env.exec_calls, 1)
        self.assertFalse(rollback_allowed(report.evidences[0]))

    def test_c_nonzero_exit_and_absent_state_is_not_applied(self):
        """C: exit != 0 and authoritative absence → confirmed failure."""
        env = Scripted(
            executions=[ExecutionResult(True, 1, "", "failure: bad command name")],
            posts=[
                (
                    StateSnapshot(
                        source="compact",
                        properties={},
                        compact_known_keys=frozenset({"name", "listen-port"}),
                    ),
                    StateSnapshot(source="get", properties={}),
                )
            ],
        )
        report = safe_routeros_exec(
            [_step(), _step("/ip address add address=10.0.0.1/24 interface=wg0")],
            executor=env.execute,
            reader=env.reader,
        )
        self.assertEqual(report.outcomes[0], Outcome.NOT_APPLIED)
        self.assertTrue(report.stopped)
        self.assertEqual(env.exec_calls, 1)

    def test_1_first_mutation_fails_later_not_attempted(self):
        env = Scripted(
            executions=[ExecutionResult(True, 1, "", "syntax error")],
            posts=[
                (
                    StateSnapshot(source="compact", properties={}),
                    StateSnapshot(source="get", properties={}),
                )
            ],
        )
        later = _step("/ip address add address=10.0.0.1/24 interface=wg0")
        report = safe_routeros_exec(
            [_step(), later], executor=env.execute, reader=env.reader
        )
        self.assertEqual(env.exec_calls, 1)
        self.assertNotIn(later.sanitized_command, env.commands)

    def test_2_first_applies_second_fails_boundary_identified(self):
        env = Scripted(
            executions=[
                ExecutionResult(True, 0, "", ""),
                ExecutionResult(True, 1, "", "failure: no such item"),
            ],
            posts=[
                (
                    StateSnapshot(
                        source="compact",
                        properties={"name": "wg0", "listen-port": "51820"},
                    ),
                    StateSnapshot(
                        source="get",
                        properties={
                            "name": "wg0",
                            "listen-port": "51820",
                            "comment": "lab",
                        },
                    ),
                ),
                (
                    StateSnapshot(source="compact", properties={"name": "wg0"}),
                    StateSnapshot(source="get", properties={"name": "wg0"}),
                ),
            ],
        )
        step2 = MutationStep(
            sanitized_command="/ip address add address=10.0.0.1/24 interface=wg0",
            expected={"address": "10.0.0.1/24", "interface": "wg0"},
            critical_keys=("address", "interface"),
            compact_known_keys=frozenset({"address", "interface"}),
            identity_key="address",
        )
        report = safe_routeros_exec(
            [_step(), step2], executor=env.execute, reader=env.reader
        )
        self.assertEqual(report.outcomes[0], Outcome.APPLIED)
        self.assertEqual(report.outcomes[1], Outcome.NOT_APPLIED)
        self.assertTrue(report.stopped)
        self.assertIn("order=2", report.stop_reason or "")

    def test_3_ssh_close_without_exit_is_indeterminate_and_stops(self):
        env = Scripted(
            executions=[
                ExecutionResult(None, None, None, None),
            ],
            posts=[
                (
                    StateSnapshot(source="compact", properties={}),
                    None,
                )
            ],
        )
        report = safe_routeros_exec(
            [_step(), _step("/ip address add address=10.0.0.1/24 interface=wg0")],
            executor=env.execute,
            reader=env.reader,
        )
        self.assertEqual(report.outcomes[0], Outcome.INDETERMINATE)
        self.assertTrue(report.stopped)
        self.assertEqual(env.exec_calls, 1)
        self.assertFalse(report.evidences[0].rollback_permitted)

    def test_d_incomplete_evidence_requires_reconcile_no_blind_rollback(self):
        env = Scripted(
            executions=[ExecutionResult(True, None, None, None)],
            posts=[
                (
                    StateSnapshot(source="compact", properties={}),
                    None,
                )
            ],
        )
        report = safe_routeros_exec(
            [_step()], executor=env.execute, reader=env.reader
        )
        self.assertEqual(report.outcomes[0], Outcome.INDETERMINATE)
        self.assertFalse(rollback_allowed(report.evidences[0]))

    def test_4_cli_error_with_transport_success_is_not_pass(self):
        env = Scripted(
            executions=[
                ExecutionResult(True, 0, "bad command name addx", ""),
            ],
            posts=[
                (
                    StateSnapshot(source="compact", properties={}),
                    StateSnapshot(source="get", properties={}),
                )
            ],
        )
        report = safe_routeros_exec(
            [_step()], executor=env.execute, reader=env.reader
        )
        self.assertNotEqual(report.outcomes[0], Outcome.APPLIED)
        self.assertIn(report.outcomes[0], (Outcome.NOT_APPLIED, Outcome.FAILED_AFTER_APPLY))

    def test_5_indeterminate_retry_prestate_prevents_duplicate(self):
        env = Scripted(
            executions=[],  # must not be called
            posts=[],
            pres=[
                (
                    StateSnapshot(
                        source="compact",
                        properties={"name": "wg0", "listen-port": "51820"},
                    ),
                    None,
                )
            ],
        )
        report = safe_routeros_exec(
            [_step()], executor=env.execute, reader=env.reader
        )
        self.assertEqual(env.exec_calls, 0)
        self.assertEqual(report.outcomes[0], Outcome.APPLIED)
        self.assertIn("idempotent", report.evidences[0].notes)

    def test_6_and_f_post_state_mismatch_blocks_later_mutations(self):
        env = Scripted(
            executions=[ExecutionResult(True, 0, "", "")],
            posts=[
                (
                    StateSnapshot(
                        source="compact",
                        properties={"name": "wg0", "listen-port": "9999"},
                        compact_known_keys=frozenset({"name", "listen-port"}),
                    ),
                    StateSnapshot(
                        source="get",
                        properties={
                            "name": "wg0",
                            "listen-port": "9999",
                            "comment": "other",
                        },
                    ),
                )
            ],
        )
        later = _step("/ip address add address=10.0.0.1/24 interface=wg0")
        report = safe_routeros_exec(
            [_step(), later], executor=env.execute, reader=env.reader
        )
        self.assertEqual(report.outcomes[0], Outcome.MISMATCH)
        self.assertTrue(report.stopped)
        self.assertEqual(env.exec_calls, 1)
        self.assertTrue(report.evidences[0].rollback_permitted)

    def test_g_partial_operation_no_blind_rollback(self):
        env = Scripted(
            executions=[ExecutionResult(None, None, "truncated", None)],
            posts=[
                (
                    StateSnapshot(source="compact", properties={"name": "wg0"}),
                    None,
                )
            ],
        )
        report = safe_routeros_exec(
            [_step()], executor=env.execute, reader=env.reader
        )
        self.assertEqual(report.outcomes[0], Outcome.INDETERMINATE)
        self.assertFalse(rollback_allowed(report.evidences[0]))

    def test_8_e_compact_omits_attribute_secondary_confirms_applied(self):
        env = Scripted(
            executions=[ExecutionResult(True, 0, "", "")],
            posts=[
                (
                    StateSnapshot(
                        source="compact",
                        properties={"name": "wg0", "listen-port": "51820"},
                        compact_known_keys=frozenset({"name", "listen-port"}),
                    ),
                    StateSnapshot(
                        source="get",
                        properties={
                            "name": "wg0",
                            "listen-port": "51820",
                            "comment": "lab",
                        },
                    ),
                )
            ],
        )
        report = safe_routeros_exec(
            [_step()], executor=env.execute, reader=env.reader
        )
        self.assertEqual(report.outcomes[0], Outcome.APPLIED)
        self.assertIn("secondary confirmed comment", report.evidences[0].notes)
        self.assertFalse(rollback_allowed(report.evidences[0]))

    def test_9_compact_and_secondary_confirm_absence(self):
        env = Scripted(
            executions=[ExecutionResult(True, 0, "", "")],
            posts=[
                (
                    StateSnapshot(
                        source="compact",
                        properties={},
                        compact_known_keys=frozenset({"name", "listen-port"}),
                    ),
                    StateSnapshot(source="get", properties={}),
                )
            ],
        )
        later = _step("/ip address add address=10.0.0.1/24 interface=wg0")
        report = safe_routeros_exec(
            [_step(), later], executor=env.execute, reader=env.reader
        )
        self.assertEqual(report.outcomes[0], Outcome.NOT_APPLIED)
        self.assertTrue(report.stopped)
        self.assertEqual(env.exec_calls, 1)

    def test_11_stored_evidence_uses_safe_projection_and_is_sanitized(self):
        secret_cmd = (
            "/interface wireguard add name=wg0 "
            "private-key=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= "
            "password=supersecret"
        )
        env = Scripted(
            executions=[
                ExecutionResult(
                    True,
                    0,
                    "private-key=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
                    "password=supersecret",
                )
            ],
            posts=[
                (
                    StateSnapshot(
                        source="compact",
                        properties={"name": "wg0", "listen-port": "51820"},
                    ),
                    StateSnapshot(
                        source="get",
                        properties={
                            "name": "wg0",
                            "listen-port": "51820",
                            "comment": "lab",
                            "private-key": "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
                        },
                    ),
                )
            ],
        )
        report = safe_routeros_exec(
            [_step(cmd=secret_cmd)], executor=env.execute, reader=env.reader
        )
        public = report.evidences[0].to_public_dict()
        blob = str(public)
        self.assertNotIn("supersecret", blob)
        self.assertNotIn("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=", blob)
        self.assertNotIn("private-key", report.evidences[0].observed)
        self.assertIn("name", report.evidences[0].observed)
        self.assertIn("<REDACTED>", public["stdout"] or "")
        self.assertIn("<REDACTED>", public["stderr"] or "")


if __name__ == "__main__":
    unittest.main()
