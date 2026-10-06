"""
test_exam.py — the exam testing itself.

The rules that matter, checked:
  R1 unimplemented is FAIL, never a pass
  R2 binary
  R3 every area declares what it does not establish
  a missing substrate is SKIP, never PASS
  the exam is independent of what it grades

Run: python -m pytest tests/ -q
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from exam.result import (  # noqa: E402
    Status, AreaResult, ExamReport, make, skip, todo,
)
from exam import AREAS, AREA_COUNT  # noqa: E402


class StructureTests(unittest.TestCase):
    def test_exactly_ten_areas(self):
        self.assertEqual(AREA_COUNT, 10)
        self.assertEqual(len(AREAS), 10)

    def test_area_numbers_are_1_to_10(self):
        self.assertEqual([n for n, _ in AREAS], list(range(1, 11)))

    def test_area_names_are_unique(self):
        names = [nm for _, nm in AREAS]
        self.assertEqual(len(names), len(set(names)))


class ScoringRuleTests(unittest.TestCase):
    def test_unimplemented_counts_as_fail(self):
        """R1. v2 scored 15/27 while most items were literals."""
        r = ExamReport([todo(1, "x", "not written"),
                        make(2, "y", True, "ok", "limit")])
        self.assertEqual(r.passed, 1)
        self.assertEqual(r.verdict(), "FAIL")

    def test_skip_counts_as_fail(self):
        """An exam that passes because it could not run is worse than
        no exam at all."""
        r = ExamReport([skip(1, "x", "substrate absent"),
                        make(2, "y", True, "ok", "limit")])
        self.assertEqual(r.passed, 1)
        self.assertEqual(r.verdict(), "FAIL")

    def test_all_pass_gives_pass(self):
        r = ExamReport([make(i, f"a{i}", True, "ok", "limit")
                        for i in range(1, 11)])
        self.assertEqual(r.verdict(), "PASS")
        self.assertEqual(r.passed, 10)

    def test_empty_report_is_not_pass(self):
        self.assertEqual(ExamReport([]).verdict(), "NOT RUN")

    def test_binary_only(self):
        """R2. no partial credit, ever."""
        a = make(1, "x", True, "ok", "limit")
        self.assertIs(a.status, Status.PASS)
        b = make(1, "x", False, "nope", "limit")
        self.assertIs(b.status, Status.FAIL)

    def test_every_area_declares_a_limit(self):
        """R3."""
        for i in range(1, 11):
            r = make(i, f"a{i}", True, "ok", "does not establish X")
            self.assertTrue(r.does_not_establish.strip())


class IndependenceTests(unittest.TestCase):
    def test_exam_does_not_import_the_substrate(self):
        """The load-bearing architectural property.

        If the exam imported fieldcore or simself, a bug in their
        helpers would become a PASSING GRADE. That is how v2 scored
        itself: it sat inside simself and graded itself with simself's
        own code.
        """
        # AST, not text. The probes are stored as STRING LITERALS that
        # legitimately contain "from constitutional ..." as source to
        # be exec'd in a subprocess, so a text search produces false
        # positives on the very design that keeps the exam independent.
        import ast as _ast
        exam_dir = Path(__file__).resolve().parent.parent / "src" / "exam"
        banned = {"constitutional", "fieldcore"}
        offenders = []
        for f in exam_dir.glob("*.py"):
            tree = _ast.parse(f.read_text(encoding="utf-8"))
            for node in _ast.walk(tree):
                if isinstance(node, _ast.Import):
                    for a in node.names:
                        if a.name.split(".")[0] in banned:
                            offenders.append(f"{f.name}: import {a.name}")
                elif isinstance(node, _ast.ImportFrom) and node.module:
                    if node.module.split(".")[0] in banned:
                        offenders.append(f"{f.name}: from {node.module}")
        self.assertEqual(offenders, [],
                         f"exam must not import the substrate: {offenders}")

    def test_substrate_is_reached_only_by_subprocess(self):
        from exam import substrate
        import subprocess
        src = Path(substrate.__file__).read_text(encoding="utf-8")
        self.assertIn("subprocess.run", src)
        self.assertIn("sys.executable", src)


class ProbeDisciplineTests(unittest.TestCase):
    def test_probes_never_swallow_an_exception(self):
        """A probe must let an exception ESCAPE so run_probe reports a
        failure. A probe with a bare except would turn a broken
        substrate into a passing area."""
        from exam import substrate
        for name, code in substrate.PROBES.items():
            self.assertNotIn("except", code,
                             f"probe {name} swallows an exception")
            self.assertIn("print(json.dumps", code,
                          f"probe {name} does not emit JSON")

    def test_return_probe_reports_whether_it_measured(self):
        """REGRESSION: the first return probe used an input the gate
        refused, so drift stayed 0.0 and rel_error came out 0.0 --
        indistinguishable from a perfect result."""
        from exam import substrate
        self.assertIn("measured_anything",
                      substrate.PROBES["return"])

    def test_run_probe_reports_failure_rather_than_passing(self):
        from exam import substrate
        ok, payload, err = substrate.run_probe("liveness", "raise ValueError('x')")
        self.assertFalse(ok)
        self.assertTrue(err)

    def test_run_probe_rejects_non_json(self):
        from exam import substrate
        ok, _, err = substrate.run_probe("x", "print('not json')")
        self.assertFalse(ok)
        self.assertIn("non-JSON", err)


class ResultSerializationTests(unittest.TestCase):
    def test_to_dict_round_trips_the_verdict(self):
        r = ExamReport([todo(1, "a", "todo"), make(2, "b", True, "ok", "L")])
        d = r.to_dict()
        self.assertEqual(d["verdict"], "FAIL")
        self.assertEqual(d["total"], 2)
        self.assertEqual(d["not_implemented_areas"], [1])


if __name__ == "__main__":
    unittest.main(verbosity=2)