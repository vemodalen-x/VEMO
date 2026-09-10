"""A judge verdict must bind to the code it reviewed.

These cover the defect where an empty in-scope diff hashed to sha256("") — a valid-looking
digest that every other empty diff reproduces — so a verdict recorded against nothing satisfied
the gate, and local (staged) and CI (range) runs disagreed about the same commit.
"""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if ROOT.name == "eval":
    ROOT = ROOT.parent
TS_SPEC = importlib.util.spec_from_file_location("task_state_snapshot_test",
                                                 ROOT / "enforcement" / "validators" / "task_state.py")


def _load(root):
    """Load task_state bound to a throwaway repository root."""
    module = importlib.util.module_from_spec(TS_SPEC)
    with mock.patch.dict(os.environ, {"VEMO_ROOT": str(root)}, clear=False):
        TS_SPEC.loader.exec_module(module)
    return module


class JudgeSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp(prefix="vemo_judge_snapshot_"))
        for command in (["git", "init", "-q"], ["git", "config", "user.email", "t@example.invalid"],
                        ["git", "config", "user.name", "t"]):
            subprocess.run(command, cwd=self.temp, check=True, capture_output=True)
        (self.temp / "tasks").mkdir()
        (self.temp / ".vemo").mkdir()
        (self.temp / "src").mkdir()
        (self.temp / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
        (self.temp / "tasks" / "T-demo.md").write_text(
            "---\nid: T-demo\nrisk: R2\nchange_class: ci-narrow\nstate: AcceptancePassed\n"
            'scope_in: ["src/**"]\nscope_out: []\n'
            "judge:\n  required: true\n  verdict: pass\n"
            "heartbeat: 2026-09-10T00:00:00Z\n---\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self.temp, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=self.temp, check=True, capture_output=True)
        self.ts = _load(self.temp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp, ignore_errors=True)
        os.environ.pop("VEMO_DIFF_RANGE", None)

    def _fm(self):
        return self.ts._parse_front_matter(str(self.temp / "tasks" / "T-demo.md"))

    def _stage_change(self):
        (self.temp / "src" / "app.py").write_text("x = 2\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self.temp, check=True, capture_output=True)

    def _record(self, verdict="pass"):
        return self.ts.judge_record("T-demo", verdict, evidence="e", confidence="high")

    def test_empty_diff_is_not_a_content_hash(self):
        """The regression: an empty in-scope diff must not hash like reviewed content."""
        snapshot = self.ts._judge_snapshot(self._fm())
        self.assertEqual(self.ts.EMPTY_SNAPSHOT, snapshot)
        self.assertNotEqual(hashlib.sha256(b"").hexdigest(), snapshot)

    def test_staged_change_produces_a_real_snapshot(self):
        self._stage_change()
        snapshot = self.ts._judge_snapshot(self._fm())
        self.assertNotIn(snapshot, (self.ts.EMPTY_SNAPSHOT, self.ts.LEGACY_EMPTY_SNAPSHOT, ""))

    def test_judge_record_refuses_a_pass_bound_to_nothing(self):
        env = os.environ.copy()
        env["VEMO_ROOT"] = str(self.temp)
        env.pop("VEMO_DIFF_RANGE", None)
        result = subprocess.run(
            [sys.executable, str(ROOT / "enforcement" / "validators" / "task_state.py"),
             "judge-record", "--task", "T-demo", "--verdict", "pass"],
            cwd=self.temp, env=env, capture_output=True, text=True,
        )
        self.assertEqual(1, result.returncode, result)
        self.assertTrue(result.stdout.startswith("refused:"), result)
        self.assertFalse((self.temp / ".vemo" / "judge.jsonl").exists(),
                         "a refused verdict must not reach the append-only log")

    def test_judge_record_still_accepts_a_fail_with_no_staged_diff(self):
        """A judge may fail a task precisely because the change is missing."""
        out = self._record("fail")
        self.assertTrue(out.startswith("recorded:"), out)

    def test_gate_blocks_when_no_in_scope_change_is_visible(self):
        """Even a real pass row cannot carry the gate once its diff is no longer visible."""
        self._stage_change()
        self.assertTrue(self._record("pass").startswith("recorded:"))
        subprocess.run(["git", "reset", "-q"], cwd=self.temp, check=True, capture_output=True)
        result = self.ts._judge_gate_result(self._fm(), 1)
        self.assertTrue(result.startswith("block:judge-snapshot-unbound"), result)

    def _inject(self, snapshot, verdict="pass"):
        """Append a row directly, bypassing judge_record's write-time refusal.

        The gate must stand on its own: a row can reach the log from an older version of the tool,
        a hand edit, or a judge that ran before the refusal existed.
        """
        row = {"ts": "2026-09-09T00:00:00Z", "task": "T-demo", "verdict": verdict,
               "session": "injected", "snapshot": snapshot, "evidence": "e", "confidence": "high"}
        with open(self.temp / ".vemo" / "judge.jsonl", "a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")

    def test_binds_to_content_accepts_only_real_digests(self):
        """The whitelist is the whole defense, so pin its shape directly."""
        self.assertTrue(self.ts._binds_to_content("a" * 64))
        for rejected in (None, "", "empty-diff", "invalid-range", "unresolved-range",
                         self.ts.LEGACY_EMPTY_SNAPSHOT, "a" * 63, "A" * 64, "z" * 64,
                         " " + "a" * 63, "a" * 65):
            self.assertFalse(self.ts._binds_to_content(rejected), repr(rejected))

    def test_gate_rejects_rows_that_bind_to_no_code(self):
        """Legacy sha256("") rows, sentinel rows, and snapshot-less rows all fail to carry the gate.

        Honest scope note: with a binding current snapshot, plain equality is what rejects these —
        no sentinel can equal a content digest. This asserts the OUTCOME callers depend on; the
        `_binds_to_content` whitelist itself is pinned by
        `test_binds_to_content_accepts_only_real_digests` and by the two range-bypass tests, which
        cover the case equality alone cannot (a sentinel matching itself).
        """
        self._stage_change()
        real = self.ts._judge_snapshot(self._fm())
        for unbound in (self.ts.LEGACY_EMPTY_SNAPSHOT, self.ts.EMPTY_SNAPSHOT,
                        "unresolved-range", "invalid-range", None):
            with self.subTest(snapshot=unbound):
                (self.temp / ".vemo" / "judge.jsonl").write_text("", encoding="utf-8")
                self._inject(unbound)
                self.assertNotEqual(real, unbound)
                result = self.ts._judge_gate_result(self._fm(), 1)
                self.assertTrue(result.startswith("block:judge-pass-count=0"), result)

    def test_unresolvable_range_cannot_mint_a_pass(self):
        """The bypass an independent judge demonstrated: a sentinel matches itself.

        With a nonexistent range, `_judge_snapshot` returns "unresolved-range" both when the verdict
        is recorded and when the gate re-reads it, so a blacklist-free equality check would see a
        match and open an R2 gate on a verdict bound to no code.
        """
        self._stage_change()
        os.environ["VEMO_DIFF_RANGE"] = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef...HEAD"
        try:
            self.assertEqual("unresolved-range", self.ts._judge_snapshot(self._fm()))
            self.assertTrue(self._record("pass").startswith("refused:"))
            self._inject("unresolved-range")
            result = self.ts._judge_gate_result(self._fm(), 1)
            self.assertTrue(result.startswith("block:judge-snapshot-unbound"), result)
        finally:
            os.environ.pop("VEMO_DIFF_RANGE", None)

    def test_injected_option_like_range_cannot_mint_a_pass(self):
        """Same class via the argument-injection guard's "invalid-range" return."""
        self._stage_change()
        os.environ["VEMO_DIFF_RANGE"] = "--output=/tmp/should-not-be-written"
        try:
            self.assertEqual("invalid-range", self.ts._judge_snapshot(self._fm()))
            self.assertTrue(self._record("pass").startswith("refused:"))
            self._inject("invalid-range")
            self.assertTrue(self.ts._judge_gate_result(self._fm(), 1).startswith(
                "block:judge-snapshot-unbound"))
        finally:
            os.environ.pop("VEMO_DIFF_RANGE", None)

    def test_gate_rejects_rows_with_no_snapshot_key(self):
        """28 of the log's historical rows predate snapshots entirely; they bind to nothing."""
        self._stage_change()
        row = {"ts": "2026-07-02T00:00:00Z", "task": "T-demo", "verdict": "pass",
               "session": "ancient", "evidence": "e", "confidence": "high"}
        (self.temp / ".vemo" / "judge.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
        self.assertTrue(self.ts._judge_gate_result(self._fm(), 1).startswith("block:judge-pass-count=0"))

    def test_gate_accepts_a_pass_bound_to_the_staged_diff(self):
        self._stage_change()
        self.assertTrue(self._record("pass").startswith("recorded:"))
        self.assertEqual("ok", self.ts._judge_gate_result(self._fm(), 1))

    def test_staged_and_range_modes_agree_for_the_same_content(self):
        """Local (staged) and CI (range) runs must not disagree about one commit."""
        self._stage_change()
        staged = self.ts._judge_snapshot(self._fm())
        subprocess.run(["git", "commit", "-qm", "change"], cwd=self.temp, check=True, capture_output=True)
        os.environ["VEMO_DIFF_RANGE"] = "HEAD~1...HEAD"
        try:
            self.assertEqual(staged, self.ts._judge_snapshot(self._fm()))
        finally:
            os.environ.pop("VEMO_DIFF_RANGE", None)

    def test_out_of_scope_only_change_counts_as_empty(self):
        """A diff touching nothing in scope_in gives the judge nothing to review."""
        (self.temp / "unrelated.md").write_text("doc\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=self.temp, check=True, capture_output=True)
        self.assertEqual(self.ts.EMPTY_SNAPSHOT, self.ts._judge_snapshot(self._fm()))


if __name__ == "__main__":
    unittest.main()
