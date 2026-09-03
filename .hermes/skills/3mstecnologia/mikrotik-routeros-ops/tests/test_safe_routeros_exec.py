"""Unit tests for the atomic RouterOS SSH mutation contract.

Fixtures are synthetic. No live equipment, no real IPs, credentials, or keys.
Secret-like strings are clearly fake (SYNTHETIC_* / quoted lab phrases).
"""

from __future__ import annotations

import unittest

from safe_routeros_exec import (
    AggregatedMutationError,
    ExecutionResult,
    MutationKind,
    MutationStep,
    Outcome,
    Presence,
    StateSnapshot,
    assert_single_mutation,
    classify_compact_field,
    expected_matches,
    parse_property_line,
    reconcile_state,
    rollback_allowed,
    safe_routeros_exec,
    sanitize_evidence,
    sanitize_public,
)


WG0 = {"name": "wg0", "listen-port": "51820", "comment": "lab"}


def _add(
    cmd: str = "/interface wireguard add name=wg0 listen-port=51820 comment=lab",
    expected: dict | None = None,
    identity: str | None = "name",
) -> MutationStep:
    return MutationStep(
        sanitized_command=cmd,
        kind=MutationKind.ADD,
        expected=expected or dict(WG0),
        critical_keys=("name", "listen-port", "comment"),
        compact_known_keys=frozenset({"name", "listen-port"}),
        identity_key=identity,
    )


def _snap(props: dict, source: str = "get", known: frozenset | None = None) -> StateSnapshot:
    return StateSnapshot(
        source=source,
        properties=dict(props),
        compact_known_keys=known or frozenset(),
    )


class Scripted:
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
            return _snap({}, "compact", frozenset({"name", "listen-port"})), _snap({})
        return self.posts.pop(0)


def _ok_post():
    return (
        _snap({"name": "wg0", "listen-port": "51820"}, "compact", frozenset({"name", "listen-port"})),
        _snap(WG0, "get"),
    )


class ParseAndSanitizeTests(unittest.TestCase):
    def test_property_order_does_not_create_false_divergence(self):
        a = parse_property_line("name=wg0 listen-port=51820 comment=lab")
        b = parse_property_line("comment=lab listen-port=51820 name=wg0")
        self.assertEqual(a, b)
        self.assertTrue(expected_matches({"name": "wg0", "comment": "lab"}, a))

    def test_quoted_and_line_wrap_parse(self):
        text = 'name=wg0 \\\ncomment="lab tunnel" listen-port=51820'
        props = parse_property_line(text)
        self.assertEqual(props["comment"], "lab tunnel")
        self.assertEqual(props["name"], "wg0")

    def test_single_quoted_parse(self):
        props = parse_property_line("comment='lab tunnel' name=wg0")
        self.assertEqual(props["comment"], "lab tunnel")

    def test_compact_omission_is_inconclusive_not_absent(self):
        compact = {"name": "wg0", "listen-port": "51820"}
        self.assertEqual(
            classify_compact_field(compact, "comment", compact_known_to_project=False),
            Presence.INCONCLUSIVE,
        )

    def test_sanitize_redacts_secret_literals(self):
        raw = (
            "password=SYNTHETIC_PASSWORD_ALPHA token=SYNTHETIC_TOKEN_BETA "
            "community=SYNTHETIC_COMMUNITY_GAMMA "
            "private-key=SYNTHETICPRIVATEKEYAAAAAAAAAAAAAAAAAAAA= "
            "preshared-key=SYNTHETICPRESHAREDKEYBBBBBBBBBBBBBBBB="
        )
        cleaned = sanitize_evidence(raw)
        assert cleaned is not None
        for forbidden in (
            "SYNTHETIC_PASSWORD_ALPHA",
            "SYNTHETIC_TOKEN_BETA",
            "SYNTHETIC_COMMUNITY_GAMMA",
            "SYNTHETICPRIVATEKEYAAAAAAAAAAAAAAAAAAAA=",
            "SYNTHETICPRESHAREDKEYBBBBBBBBBBBBBBBB=",
        ):
            self.assertNotIn(forbidden, cleaned)
        self.assertIn("<REDACTED>", cleaned)

    def test_e_quoted_secret_with_space_double_quotes(self):
        raw = 'password="quoted secret value"'
        cleaned = sanitize_evidence(raw)
        assert cleaned is not None
        self.assertNotIn("quoted secret value", cleaned)
        self.assertIn("password=<REDACTED>", cleaned)

    def test_f_quoted_secret_single_quotes(self):
        raw = "token='quoted secret value'"
        cleaned = sanitize_evidence(raw)
        assert cleaned is not None
        self.assertNotIn("quoted secret value", cleaned)
        self.assertIn("token=<REDACTED>", cleaned)

    def test_g_double_quotes_cli_argument_form(self):
        raw = '/user add name=lab password="quoted secret value" group=full'
        cleaned = sanitize_evidence(raw)
        assert cleaned is not None
        self.assertNotIn("quoted secret value", cleaned)


class SequenceContractTests(unittest.TestCase):
    def test_a_mutation_zero_and_state_correct_is_applied(self):
        env = Scripted([ExecutionResult(True, 0, "", "")], [_ok_post()])
        report = safe_routeros_exec([_add()], executor=env.execute, reader=env.reader)
        self.assertEqual(report.outcomes, [Outcome.APPLIED])
        self.assertTrue(report.evidences[0].executed)
        self.assertFalse(report.stopped)
        self.assertEqual(env.exec_calls, 1)

    def test_b_nonzero_exit_but_state_applied_is_failed_after_apply(self):
        env = Scripted(
            [ExecutionResult(True, 1, "", "failure: late session error")],
            [_ok_post()],
        )
        later = _add("/ip address add address=10.0.0.1/24 interface=wg0")
        report = safe_routeros_exec([_add(), later], executor=env.execute, reader=env.reader)
        self.assertEqual(report.outcomes[0], Outcome.FAILED_AFTER_APPLY)
        self.assertEqual(report.evidences[0].pre_state, {})
        self.assertEqual(report.evidences[0].observed.get("name"), "wg0")
        self.assertTrue(report.stopped)
        self.assertEqual(env.exec_calls, 1)
        self.assertFalse(rollback_allowed(report.evidences[0]))

    def test_pre_already_satisfied_plus_failed_exec_not_attributed_as_apply(self):
        """If pre already matched, failure is not failed-after-apply (no delta)."""
        env = Scripted(
            [ExecutionResult(True, 1, "", "failure: late session error")],
            [_ok_post()],
            pres=[_ok_post()],
        )
        report = safe_routeros_exec([_add()], executor=env.execute, reader=env.reader)
        self.assertEqual(report.outcomes[0], Outcome.ALREADY_SATISFIED)
        self.assertFalse(report.evidences[0].executed)
        self.assertEqual(env.exec_calls, 0)

    def test_c_nonzero_exit_and_absent_state_is_not_applied(self):
        env = Scripted(
            [ExecutionResult(True, 1, "", "failure: bad command name")],
            [(_snap({}, "compact", frozenset({"name", "listen-port"})), _snap({}))],
        )
        later = _add("/ip address add address=10.0.0.1/24 interface=wg0")
        report = safe_routeros_exec([_add(), later], executor=env.execute, reader=env.reader)
        self.assertEqual(report.outcomes[0], Outcome.NOT_APPLIED)
        self.assertTrue(report.stopped)

    def test_1_first_mutation_fails_later_not_attempted(self):
        env = Scripted(
            [ExecutionResult(True, 1, "", "syntax error")],
            [(_snap({}, "compact"), _snap({}))],
        )
        later = _add("/ip address add address=10.0.0.1/24 interface=wg0")
        report = safe_routeros_exec([_add(), later], executor=env.execute, reader=env.reader)
        self.assertEqual(env.exec_calls, 1)
        self.assertNotIn(later.sanitized_command, env.commands)

    def test_2_first_applies_second_fails_boundary_identified(self):
        env = Scripted(
            [
                ExecutionResult(True, 0, "", ""),
                ExecutionResult(True, 1, "", "failure: no such item"),
            ],
            [
                _ok_post(),
                (_snap({"name": "wg0"}, "compact"), _snap({"name": "wg0"})),
            ],
        )
        step2 = MutationStep(
            sanitized_command="/ip address add address=10.0.0.1/24 interface=wg0",
            kind=MutationKind.ADD,
            expected={"address": "10.0.0.1/24", "interface": "wg0"},
            critical_keys=("address", "interface"),
            compact_known_keys=frozenset({"address", "interface"}),
            identity_key="address",
        )
        report = safe_routeros_exec([_add(), step2], executor=env.execute, reader=env.reader)
        self.assertEqual(report.outcomes[0], Outcome.APPLIED)
        self.assertEqual(report.outcomes[1], Outcome.NOT_APPLIED)
        self.assertTrue(report.stopped)
        self.assertIn("order=2", report.stop_reason or "")

    def test_3_ssh_close_without_exit_is_indeterminate_and_stops(self):
        env = Scripted(
            [ExecutionResult(None, None, None, None)],
            [(_snap({}, "compact"), None)],
        )
        later = _add("/ip address add address=10.0.0.1/24 interface=wg0")
        report = safe_routeros_exec([_add(), later], executor=env.execute, reader=env.reader)
        self.assertEqual(report.outcomes[0], Outcome.INDETERMINATE)
        self.assertTrue(report.stopped)
        self.assertFalse(report.evidences[0].rollback_permitted)

    def test_d_incomplete_evidence_requires_reconcile_no_blind_rollback(self):
        env = Scripted(
            [ExecutionResult(True, None, None, None)],
            [(_snap({}, "compact"), None)],
        )
        report = safe_routeros_exec([_add()], executor=env.execute, reader=env.reader)
        self.assertEqual(report.outcomes[0], Outcome.INDETERMINATE)
        self.assertFalse(rollback_allowed(report.evidences[0]))

    def test_4_cli_error_with_transport_success_is_not_pass(self):
        env = Scripted(
            [ExecutionResult(True, 0, "bad command name addx", "")],
            [(_snap({}, "compact"), _snap({}))],
        )
        report = safe_routeros_exec([_add()], executor=env.execute, reader=env.reader)
        self.assertNotEqual(report.outcomes[0], Outcome.APPLIED)
        self.assertIn(
            report.outcomes[0],
            (Outcome.NOT_APPLIED, Outcome.FAILED_AFTER_APPLY, Outcome.INDETERMINATE),
        )

    def test_5_retry_full_postcondition_is_already_satisfied_not_applied(self):
        env = Scripted([], [], pres=[_ok_post()])
        report = safe_routeros_exec([_add()], executor=env.execute, reader=env.reader)
        self.assertEqual(env.exec_calls, 0)
        self.assertEqual(report.outcomes[0], Outcome.ALREADY_SATISFIED)
        self.assertFalse(report.evidences[0].executed)
        self.assertIn("no-op reconciled", report.evidences[0].notes)

    def test_retry_identity_same_attributes_wrong_is_mismatch(self):
        pre = (
            _snap({"name": "wg0", "listen-port": "9999"}, "compact", frozenset({"name", "listen-port"})),
            _snap({"name": "wg0", "listen-port": "9999", "comment": "other"}, "get"),
        )
        env = Scripted([], [], pres=[pre])
        report = safe_routeros_exec([_add()], executor=env.execute, reader=env.reader)
        self.assertEqual(env.exec_calls, 0)
        self.assertEqual(report.outcomes[0], Outcome.MISMATCH)
        self.assertFalse(report.evidences[0].executed)
        self.assertFalse(rollback_allowed(report.evidences[0]))
        self.assertTrue(report.stopped)

    def test_6_and_f_post_state_mismatch_blocks_later_mutations(self):
        env = Scripted(
            [ExecutionResult(True, 0, "", "")],
            [
                (
                    _snap({"name": "wg0", "listen-port": "9999"}, "compact", frozenset({"name", "listen-port"})),
                    _snap({"name": "wg0", "listen-port": "9999", "comment": "other"}, "get"),
                )
            ],
        )
        later = _add("/ip address add address=10.0.0.1/24 interface=wg0")
        report = safe_routeros_exec([_add(), later], executor=env.execute, reader=env.reader)
        self.assertEqual(report.outcomes[0], Outcome.MISMATCH)
        self.assertTrue(report.stopped)
        self.assertEqual(env.exec_calls, 1)
        self.assertTrue(rollback_allowed(report.evidences[0]))
        self.assertIn("remove", report.evidences[0].rollback_plan or "")

    def test_mismatch_preexisting_without_delta_forbids_rollback(self):
        pre = (
            _snap({"name": "wg0", "listen-port": "1111"}, "compact", frozenset({"name", "listen-port"})),
            _snap({"name": "wg0", "listen-port": "1111", "comment": "old"}, "get"),
        )
        env = Scripted([], [], pres=[pre])
        report = safe_routeros_exec([_add()], executor=env.execute, reader=env.reader)
        self.assertEqual(report.outcomes[0], Outcome.MISMATCH)
        self.assertFalse(rollback_allowed(report.evidences[0]))

    def test_g_partial_operation_no_blind_rollback(self):
        env = Scripted(
            [ExecutionResult(None, None, "truncated", None)],
            [(_snap({"name": "wg0"}, "compact"), None)],
        )
        report = safe_routeros_exec([_add()], executor=env.execute, reader=env.reader)
        self.assertEqual(report.outcomes[0], Outcome.INDETERMINATE)
        self.assertFalse(rollback_allowed(report.evidences[0]))

    def test_8_e_compact_omits_attribute_secondary_confirms_applied(self):
        env = Scripted([ExecutionResult(True, 0, "", "")], [_ok_post()])
        report = safe_routeros_exec([_add()], executor=env.execute, reader=env.reader)
        self.assertEqual(report.outcomes[0], Outcome.APPLIED)
        self.assertIn("secondary confirmed comment", report.evidences[0].notes)
        self.assertFalse(rollback_allowed(report.evidences[0]))

    def test_9_compact_and_secondary_confirm_absence(self):
        env = Scripted(
            [ExecutionResult(True, 0, "", "")],
            [(_snap({}, "compact", frozenset({"name", "listen-port"})), _snap({}))],
        )
        later = _add("/ip address add address=10.0.0.1/24 interface=wg0")
        report = safe_routeros_exec([_add(), later], executor=env.execute, reader=env.reader)
        self.assertEqual(report.outcomes[0], Outcome.NOT_APPLIED)
        self.assertTrue(report.stopped)

    def test_mixed_inconclusive_and_absent_order_independent(self):
        compact = _snap({"name": "wg0"}, "compact", frozenset({"name", "listen-port"}))
        a = reconcile_state(compact, None, ("listen-port", "comment"))
        b = reconcile_state(compact, None, ("comment", "listen-port"))
        self.assertEqual(a[1], Presence.INCONCLUSIVE)
        self.assertEqual(b[1], Presence.INCONCLUSIVE)

    def test_reject_aggregated_command_before_executor(self):
        with self.assertRaises(AggregatedMutationError):
            assert_single_mutation(
                "/interface wireguard add name=wg0; /ip address add address=10.0.0.1/24 interface=wg0"
            )
        env = Scripted([ExecutionResult(True, 0, "", "")], [_ok_post()])
        step = _add(
            "/interface wireguard add name=wg0; /ip address add address=10.0.0.1/24 interface=wg0"
        )
        report = safe_routeros_exec([step], executor=env.execute, reader=env.reader)
        self.assertEqual(env.exec_calls, 0)
        self.assertEqual(report.outcomes[0], Outcome.INDETERMINATE)
        self.assertFalse(report.evidences[0].executed)
        self.assertIn("rejected", report.evidences[0].notes)

    def test_remove_object_still_present_is_not_applied(self):
        step = MutationStep(
            sanitized_command="/interface wireguard remove [find name=wg0]",
            kind=MutationKind.REMOVE,
            expected={"name": "wg0"},
            critical_keys=("name",),
            compact_known_keys=frozenset({"name"}),
            identity_key="name",
        )
        env = Scripted(
            [ExecutionResult(True, 0, "", "")],
            [(_snap({"name": "wg0"}, "compact", frozenset({"name"})), _snap({"name": "wg0"}))],
            pres=[(_snap({"name": "wg0"}, "compact", frozenset({"name"})), _snap({"name": "wg0"}))],
        )
        report = safe_routeros_exec([step], executor=env.execute, reader=env.reader)
        self.assertNotEqual(report.outcomes[0], Outcome.APPLIED)
        self.assertEqual(report.outcomes[0], Outcome.MISMATCH)

    def test_remove_absent_is_applied(self):
        step = MutationStep(
            sanitized_command="/interface wireguard remove [find name=wg0]",
            kind=MutationKind.REMOVE,
            expected={"name": "wg0"},
            critical_keys=("name",),
            compact_known_keys=frozenset({"name"}),
            identity_key="name",
        )
        env = Scripted(
            [ExecutionResult(True, 0, "", "")],
            [(_snap({}, "compact", frozenset({"name"})), _snap({}))],
            pres=[(_snap({"name": "wg0"}, "compact", frozenset({"name"})), _snap({"name": "wg0"}))],
        )
        report = safe_routeros_exec([step], executor=env.execute, reader=env.reader)
        self.assertEqual(report.outcomes[0], Outcome.APPLIED)

    def test_enable_and_disable_and_move(self):
        enable = MutationStep(
            sanitized_command="/ip firewall filter enable [find comment=lab]",
            kind=MutationKind.ENABLE,
            expected={"comment": "lab", "disabled": "false"},
            critical_keys=("comment", "disabled"),
            compact_known_keys=frozenset({"comment", "disabled"}),
            identity_key="comment",
        )
        disable = MutationStep(
            sanitized_command="/ip firewall filter disable [find comment=lab]",
            kind=MutationKind.DISABLE,
            expected={"comment": "lab", "disabled": "true"},
            critical_keys=("comment", "disabled"),
            compact_known_keys=frozenset({"comment", "disabled"}),
            identity_key="comment",
        )
        move = MutationStep(
            sanitized_command="/ip firewall filter move [find comment=lab] destination=0",
            kind=MutationKind.MOVE,
            expected={"comment": "lab", "order": "0"},
            critical_keys=("comment", "order"),
            compact_known_keys=frozenset({"comment", "order"}),
            identity_key="comment",
        )
        env = Scripted(
            [
                ExecutionResult(True, 0, "", ""),
                ExecutionResult(True, 0, "", ""),
                ExecutionResult(True, 0, "", ""),
            ],
            [
                (_snap({"comment": "lab", "disabled": "false"}, "get"), None),
                (_snap({"comment": "lab", "disabled": "true"}, "get"), None),
                (_snap({"comment": "lab", "order": "0"}, "get"), None),
            ],
            pres=[
                (_snap({"comment": "lab", "disabled": "true"}, "get"), None),
                (_snap({"comment": "lab", "disabled": "false"}, "get"), None),
                (_snap({"comment": "lab", "order": "3"}, "get"), None),
            ],
        )
        report = safe_routeros_exec(
            [enable, disable, move], executor=env.execute, reader=env.reader
        )
        self.assertEqual(
            report.outcomes,
            [Outcome.APPLIED, Outcome.APPLIED, Outcome.APPLIED],
        )

    def test_set_partial_change_rollback_restores_pre_state(self):
        step = MutationStep(
            sanitized_command="/interface wireguard set [find name=wg0] listen-port=51820",
            kind=MutationKind.SET,
            expected={"name": "wg0", "listen-port": "51820"},
            critical_keys=("name", "listen-port"),
            compact_known_keys=frozenset({"name", "listen-port"}),
            identity_key="name",
        )
        env = Scripted(
            [ExecutionResult(True, 0, "", "")],
            [(_snap({"name": "wg0", "listen-port": "1111"}, "get"), None)],
            pres=[(_snap({"name": "wg0", "listen-port": "9999"}, "get"), None)],
        )
        report = safe_routeros_exec([step], executor=env.execute, reader=env.reader)
        self.assertEqual(report.outcomes[0], Outcome.MISMATCH)
        self.assertTrue(rollback_allowed(report.evidences[0]))
        self.assertIn("restore pre-state", report.evidences[0].rollback_plan or "")

    def test_h_public_payload_redacts_all_sensitive_fields(self):
        secret_cmd = (
            '/interface wireguard add name=wg0 '
            'password="quoted secret value" '
            "token='quoted secret value' "
            "private-key=SYNTHETICPRIVATEKEYAAAAAAAAAAAAAAAAAAAA="
        )
        expected = {
            "name": "wg0",
            "listen-port": "51820",
            "comment": "lab",
            "password": "quoted secret value",
        }
        env = Scripted(
            [
                ExecutionResult(
                    True,
                    0,
                    'stdout password="quoted secret value"',
                    "stderr token='quoted secret value'",
                )
            ],
            [_ok_post()],
        )
        step = _add(cmd=secret_cmd, expected=expected)
        report = safe_routeros_exec([step], executor=env.execute, reader=env.reader)
        report.evidences[0].notes = (
            'operator noted password="quoted secret value" in notes'
        )
        public = report.evidences[0].to_public_dict()
        blob = str(public)
        for forbidden in (
            "quoted secret value",
            "SYNTHETICPRIVATEKEYAAAAAAAAAAAAAAAAAAAA=",
        ):
            self.assertNotIn(forbidden, blob)
        self.assertEqual(public["expected"]["password"], "<REDACTED>")
        self.assertNotIn("quoted secret value", public["notes"] or "")
        self.assertNotIn("quoted secret value", public["stdout"] or "")
        self.assertNotIn("quoted secret value", public["stderr"] or "")
        self.assertNotIn("quoted secret value", public["sanitized_command"] or "")

    def test_sanitize_public_covers_nested_expected_notes(self):
        payload = sanitize_public(
            {
                "expected": {"password": "quoted secret value"},
                "notes": 'leftover password="quoted secret value"',
                "stdout": "ok",
            }
        )
        blob = str(payload)
        self.assertNotIn("quoted secret value", blob)
        self.assertEqual(payload["expected"]["password"], "<REDACTED>")


if __name__ == "__main__":
    unittest.main()
