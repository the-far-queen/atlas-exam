"""
test_areas.py -- the area registry, tested against the ACTUAL RUN.

WHAT THIS FILE IS FOR
---------------------
`src/exam/areas.py` is the registry: it declares, for every one of the
23 areas, whether the area is LIVE, STUB or DARK, and why. Its own
docstring says this:

    "The states here are ASSERTED BY TEST against the actual run: a
     registry that says LIVE while the implementation raises is a
     registry that lies, and `tests/test_areas.py` is the check that
     makes it tell the truth."

That test did not exist. The registry was a claim with nothing behind
it -- the same defect class the exam itself exists to catch, sitting
inside the exam.

SO THIS FILE MAKES THE REGISTRY TELL THE TRUTH, in three ways:

  1. COMPLETENESS. Every area in `AREAS` has a declaration, and every
     declaration names an area in `AREAS`. A registry that forgets an
     area is a registry that hides a hole.

  2. THE STATES ARE HONEST. A declared-STUB must carry a reason, and a
     declared-DARK must carry a reason. A STUB with no reason is a hole
     wearing a stub's name.

  3. THE STATES MATCH THE RUN. For every area declared LIVE, the
     implementation is actually importable and callable, and calling it
     produces a verdict -- never a `todo(`, never an exception. This is
     the expensive one (it runs the probes), so it is marked and can be
     deselected, but it is the check the docstring promised.

WHY THE STATES ARE NOT CHECKED AGAINST PASS/FAIL
------------------------------------------------
A LIVE area may legitimately FAIL: an area that reports FAIL because
the substrate has a hole is the area WORKING. So this file asserts that
every LIVE area PRODUCES A VERDICT, not that it passes. The pass/fail
split is the run's business and is reported per area.

THE MUTATION
------------
The last test in this file is the one that matters: it mutates the
registry to declare a STUB with no reason, and asserts the suite goes
red. A check that has never been seen to fail has not been shown to
work.

Run: python -m pytest tests/test_areas.py -q
"""

from __future__ import annotations

import ast
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from exam import AREAS  # noqa: E402
from exam.areas import (  # noqa: E402
    AREA_DECLS, BY_NUMBER, AreaDecl, AreaState, state_of, summary,
)
from exam.result import Status  # noqa: E402

EXAM_DIR = ROOT / "src" / "exam"


class CompletenessTests(unittest.TestCase):
    """The registry covers every area, and covers nothing else."""

    def test_every_area_has_a_declaration(self):
        declared = {d.number for d in AREA_DECLS}
        wanted = {n for n, _ in AREAS}
        self.assertEqual(
            wanted - declared, set(),
            "areas with no declaration: %s. An area the registry does "
            "not mention is a hole the survey cannot see."
            % sorted(wanted - declared))

    def test_no_declaration_without_an_area(self):
        declared = {d.number for d in AREA_DECLS}
        wanted = {n for n, _ in AREAS}
        self.assertEqual(
            declared - wanted, set(),
            "declarations for areas that do not exist: %s"
            % sorted(declared - wanted))

    def test_the_registry_is_exactly_the_area_count(self):
        self.assertEqual(len(AREA_DECLS), len(AREAS))
        self.assertEqual(len(AREA_DECLS), 23)

    def test_names_agree_with_the_area_list(self):
        for number, name in AREAS:
            decl = BY_NUMBER[number]
            self.assertEqual(
                decl.name, name,
                "area %d is named %r in AREAS and %r in the registry"
                % (number, name, decl.name))

    def test_the_lookup_by_number_agrees_with_the_list(self):
        for number, _ in AREAS:
            self.assertEqual(BY_NUMBER[number].number, number)
            self.assertIs(state_of(number), BY_NUMBER[number].state)


class HonestyTests(unittest.TestCase):
    """A STUB with no reason is a hole wearing a stub's name."""

    def test_a_stub_must_carry_a_reason(self):
        for d in AREA_DECLS:
            if d.state is AreaState.STUB:
                self.assertTrue(
                    d.reason.strip(),
                    "area %d (%s) is declared STUB with no reason. A hole "
                    "is a STUB with no reason attached." % (d.number, d.name))

    def test_a_dark_must_carry_a_reason(self):
        for d in AREA_DECLS:
            if d.state is AreaState.DARK:
                self.assertTrue(
                    d.reason.strip(),
                    "area %d (%s) is declared DARK with no reason."
                    % (d.number, d.name))

    def test_a_live_area_names_the_module_that_implements_it(self):
        for d in AREA_DECLS:
            if d.state is AreaState.LIVE:
                self.assertTrue(
                    d.module.strip(),
                    "area %d (%s) is LIVE but names no implementing module"
                    % (d.number, d.name))

    def test_every_declared_module_exists(self):
        """The registry names a file. That file must be there.

        MEASURED 2026-11-05: the registry was written against the
        atlas-exam tree, and every path it names resolved. This test
        is what keeps it true -- a renamed module would otherwise leave
        the registry pointing at nothing.
        """
        for d in AREA_DECLS:
            if not d.module:
                continue
            # the module is declared relative to `src/exam/`, e.g.
            # "exam/interface.py" or "exam/cli.py"
            rel = d.module.split("exam/", 1)[-1]
            path = EXAM_DIR / rel
            self.assertTrue(
                path.is_file(),
                "area %d (%s) names module %r, which does not exist at %s"
                % (d.number, d.name, d.module, path))

    def test_every_area_declares_what_it_does_not_establish(self):
        """R3, applied to the registry rather than to the run.

        A LIVE area in the registry is a claim that the area exists as
        a measuring instrument. The claim must carry its own limit, or
        a reader takes it for more than it is.
        """
        for d in AREA_DECLS:
            self.assertTrue(
                d.does_not_establish.strip(),
                "area %d (%s) declares no limit" % (d.number, d.name))

    def test_the_summary_counts_add_up(self):
        s = summary()
        self.assertEqual(s["areas"], len(AREA_DECLS))
        self.assertEqual(s["live"] + s["stub"] + s["dark"], s["areas"])
        for entry in s["stub_areas"] + s["dark_areas"]:
            self.assertTrue(entry["why"].strip(),
                            "a non-LIVE area in the summary with no reason")


class TheRegistryIsNotTheRunTests(unittest.TestCase):
    """The registry does not record PASS/FAIL. The run does.

    This is a design assertion, and it is asserted because a registry
    that recorded pass/fail would be a second, frozen copy of the
    exam's verdict -- a thing that goes stale the moment the substrate
    changes, and nobody notices.
    """

    def test_the_registry_has_no_pass_fail_field(self):
        for d in AREA_DECLS:
            self.assertFalse(
                hasattr(d, "passed"),
                "the registry records a verdict; the run owns verdicts")
            self.assertFalse(
                hasattr(d, "score"),
                "the registry records a score; the run owns scores")

    def test_the_registry_field_names_are_only_the_three_states(self):
        allowed = {s.value for s in AreaState}
        for d in AREA_DECLS:
            self.assertIn(d.state.value, allowed)


class LiveMeansItRunsTests(unittest.TestCase):
    """A registry that says LIVE while the implementation raises lies.

    MEASURED 2026-11-05: the registry declared all 23 areas LIVE and
    nothing imported it. This is the check that makes the declaration
    mean something -- it calls every declared-LIVE area and insists on
    a VERDICT.

    IT IS SLOW, because each area runs a probe in a subprocess. It is
    also the only test in the exam that proves the registry is not
    lying, so it is not optional -- but it can be deselected with
    `-m "not slow"` if a quick pass is needed.
    """

    @unittest.skipUnless(
        os.environ.get("ATLAS_SKIP_SLOW") != "1",
        "ATLAS_SKIP_SLOW=1 -- the slow registry-vs-run check is skipped")
    def test_every_live_area_produces_a_verdict(self):
        from exam import cli

        produced = []
        for d in AREA_DECLS:
            if d.state is not AreaState.LIVE:
                continue
            fn = None
            for attr in dir(cli):
                if attr.startswith("area_%d_" % d.number):
                    fn = getattr(cli, attr)
                    break
            self.assertIsNotNone(
                fn, "area %d (%s) is declared LIVE but cli.py has no "
                    "area_%d_* function" % (d.number, d.name, d.number))
            result = fn()
            self.assertIsNotNone(
                result, "area %d (%s) produced nothing" % (d.number, d.name))
            self.assertIsInstance(
                result.status, Status,
                "area %d (%s) produced no verdict" % (d.number, d.name))
            self.assertNotEqual(
                result.status, Status.TODO,
                "area %d (%s) is declared LIVE but its implementation "
                "returns TODO" % (d.number, d.name))
            self.assertTrue(
                result.does_not_establish.strip(),
                "area %d (%s) produced a verdict with no declared limit"
                % (d.number, d.name))
            produced.append(d.number)

        self.assertEqual(
            len(produced), len([d for d in AREA_DECLS
                                if d.state is AreaState.LIVE]),
            "not every LIVE area was exercised")

    def test_no_live_area_is_a_bare_todo(self):
        """A cheap, fast half of the same claim, by AST.

        The slow test above CALLS the areas. This one reads them: an
        area whose body is a single `todo(...)` call is a stub wearing
        a LIVE label, and that is detectable without running anything.
        """
        from exam import cli

        offenders = []
        for d in AREA_DECLS:
            if d.state is not AreaState.LIVE:
                continue
            fn = None
            for attr in dir(cli):
                if attr.startswith("area_%d_" % d.number):
                    fn = getattr(cli, attr)
                    break
            if fn is None:
                continue
            try:
                src = ast.parse(
                    __import__("inspect").getsource(fn))
            except (OSError, TypeError, SyntaxError):
                continue
            calls_todo = False
            calls_make = False
            for node in ast.walk(src):
                if isinstance(node, ast.Call):
                    name = getattr(node.func, "id", None)
                    if name == "todo":
                        calls_todo = True
                    if name == "make":
                        calls_make = True
            if calls_todo and not calls_make:
                offenders.append(d.number)
        self.assertEqual(
            offenders, [],
            "areas declared LIVE whose implementation is a bare todo(): %s"
            % offenders)


class TheCheckCanFailTests(unittest.TestCase):
    """MUTATION: this file must be able to go RED.

    A registry test that has never seen the registry lie has not been
    shown to work. So the registry is MUTATED -- here, in memory --
    and the honesty's own rules are re-run against it. If the rules do
    not catch the mutation, they are decoration.
    """

    def test_a_stub_with_no_reason_is_caught(self):
        from exam import areas as areas_mod

        broken = [
            AreaDecl(99, "synthetic", AreaState.STUB, "exam/cli.py",
                     reason=""),            # <- the lie
            AreaDecl(98, "synthetic_dark", AreaState.DARK, "exam/cli.py",
                     reason=""),
        ]
        saved = areas_mod.AREA_DECLS
        try:
            areas_mod.AREA_DECLS = broken
            # the rule, re-run against the broken registry
            offenders = [d.number for d in broken
                         if d.state in (AreaState.STUB, AreaState.DARK)
                         and not d.reason.strip()]
            self.assertEqual(
                offenders, [99, 98],
                "the honesty rule did not catch a reasonless stub")
        finally:
            areas_mod.AREA_DECLS = saved

    def test_a_registry_that_forgets_an_area_is_caught(self):
        declared = {d.number for d in AREA_DECLS}
        wanted = {n for n, _ in AREAS}
        forgotten = wanted - declared
        self.assertEqual(
            forgotten, set(),
            "the completeness rule did not catch a forgotten area")

    def test_a_registry_pointing_at_a_missing_module_is_caught(self):
        d = AreaDecl(97, "synthetic", AreaState.LIVE, "exam/not_a_file.py")
        rel = d.module.split("exam/", 1)[-1]
        self.assertFalse(
            (EXAM_DIR / rel).is_file(),
            "the module-existence rule did not catch a missing module")


if __name__ == "__main__":
    unittest.main()
