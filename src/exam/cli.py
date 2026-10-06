"""
exam.py — the ten areas, run against fieldcore and simself.

DIRECTION OF DEPENDENCY, which is the whole architecture
------------------------------------------------------
    atlas-exam  ──points at──>  fieldcore, simself
    fieldcore, simself  ──knows nothing about──>  atlas-exam

The exam is the load-bearing artifact. The substrate is one
implementation that must satisfy it. When the substrate is replaced --
a new model, a new geometry, a different runtime -- the exam does not
change, and neither do the ten areas. That is what makes evolution
safe rather than merely possible.

The corollary is why every probe runs in a SUBPROCESS (see
substrate.py): if the exam imported a substrate helper, a bug in that
helper would become a passing grade. Independence is not tidiness
here, it is the property being tested.

SCORING
-------
    PASS   only if every area passes
    FAIL   anything else, including skips and TODOs

A missing substrate is a SKIP, not a pass. An exam that passes
because it could not run is worse than no exam.

Run:
    python src/exam.py --list
    python src/exam.py --run
    python src/exam.py --json
    python src/exam.py --selfcheck
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Dict, List

from .result import AreaResult, ExamReport, Status, make, skip, todo
from . import substrate as sub


# ---------------------------------------------------------------------------
# areas 1-5: probe-backed
# ---------------------------------------------------------------------------

def area_1_refusal() -> AreaResult:
    ok, p, err = sub.run_probe("refusal", sub.PROBES["refusal"])
    if not ok:
        return skip(1, "refusal", err or "probe failed")
    checks = {
        "accepts coherent input": p.get("accepts_coherent"),
        "refuses orthogonal": p.get("refuses_orthogonal"),
        "refuses oversize": p.get("refuses_oversize"),
        "refuses zero": p.get("refuses_zero"),
        "every refusal carries a reason": p.get("reasons_present"),
    }
    bad = [k for k, v in checks.items() if not v]
    return make(
        1, "refusal", not bad,
        "all four gate cases behave as coded" if not bad
        else f"wrong: {bad}",
        "that the thresholds are RIGHT. cos >= 0.4 and |x| <= 4 are "
        "choices with no derivation behind them; this area checks the "
        "code does what it says, not that what it says is correct.",
        p,
    )


def area_2_identity() -> AreaResult:
    ok, p, err = sub.run_probe("identity", sub.PROBES["identity"])
    if not ok:
        return skip(2, "identity", err or "probe failed")
    changed = p.get("max_change", 1.0)
    unit = p.get("unit_norm", False)
    return make(
        2, "identity", changed == 0.0 and unit,
        f"psi_0 changed by {changed} over 300 observations + ticks; "
        f"unit norm = {unit}",
        "that psi_0 is the RIGHT ground. A system with a wrong but "
        "immutable ground passes. Also does not cover a write that "
        "does not go through SimSelf.observe/tick.",
        p,
    )


def area_3_boundedness() -> AreaResult:
    ok, p, err = sub.run_probe("boundedness", sub.PROBES["boundedness"])
    if not ok:
        return skip(3, "boundedness", err or "probe failed")
    return make(
        3, "boundedness", bool(p.get("inside")),
        f"max drift {p.get('max_drift'):.4f} against R = {p.get('R')} "
        f"over 1000 accepted inputs",
        "that R = 3 is the right bound. Only that the bound holds. "
        "Choosing R is a separate decision needing its own evidence.",
        p,
    )


def area_4_liveness() -> AreaResult:
    ok, p, err = sub.run_probe("liveness", sub.PROBES["liveness"])
    if not ok:
        return skip(4, "liveness", err or "probe failed")
    return make(
        4, "liveness", bool(p.get("moved")),
        f"{p.get('accepted')} accepted of 200, peak drift "
        f"{p.get('peak_drift'):.4f} (R = {p.get('R')})",
        "that the motion is CORRECT, only that it exists. A system "
        "drifting in the wrong direction passes this area. Paired with "
        "area 1 so a system that refuses everything cannot pass both.",
        p,
    )


def area_5_return() -> AreaResult:
    ok, p, err = sub.run_probe("return", sub.PROBES["return"])
    if not ok:
        return skip(5, "return", err or "probe failed")
    # an area that measured nothing must not read as a pass. the first
    # version of this probe used an input the gate refused, so drift
    # stayed at 0.0 and the result looked perfect.
    measured = bool(p.get("measured_anything"))
    rel = p.get("rel_error")
    decays = bool(p.get("contracts")) and (rel is not None and rel < 0.01)
    return make(
        5, "return", measured and decays,
        (f"d0 {p.get('d0'):.6f} -> d20 {p.get('d20'):.6f}, predicted "
         f"{p.get('predicted'):.6f}, rel error {rel:.2e}")
        if measured else
        "PROBE MEASURED NOTHING: the input was refused so drift never "
        "left zero. This is not a pass.",
        "that 20 ticks is the right settling budget, or that the decay "
        "law is the correct model of recovery. It checks the measured "
        "decay matches exp(-eta t) over one window.",
        p,
    )


# ---------------------------------------------------------------------------
# areas 6-9: not yet implemented
# ---------------------------------------------------------------------------

def area_6_provenance() -> AreaResult:
    return todo(
        6, "provenance",
        "not implemented. requires a claim-to-source audit over the "
        "papers and repos: every factual assertion must resolve to a "
        "checkable source or be labelled hypothesis.",
        "any provenance checking at all",
    )


def area_7_reconciliation() -> AreaResult:
    return todo(
        7, "reconciliation",
        "not implemented. the pattern is proven elsewhere -- damping "
        "recovered from a trajectory by log-decay agrees with the "
        "dynamics to 0.1%, and the atlas curvature detector agrees "
        "with finite differences -- but it is not yet applied across "
        "the substrate.",
        "any cross-check of independent derivations",
    )


def area_8_observability() -> AreaResult:
    return todo(
        8, "observability",
        "not implemented. simself/src/constitutional/innovation.py "
        "exists and detects the 2026-10-06 inertness signature "
        "(residual 0.0 with 40 accepted inputs). Wiring it in as a "
        "graded area is the remaining work.",
        "any detection of unannounced change",
    )


def area_9_envelope() -> AreaResult:
    return todo(
        9, "envelope",
        "not implemented. no subsystem has declared its operating "
        "range or its behaviour outside it. A 747 documents both for "
        "every system; we document neither.",
        "any declared operating limit",
    )


# ---------------------------------------------------------------------------
# area 10: the exam judging itself
# ---------------------------------------------------------------------------

def area_10_selfcheck() -> AreaResult:
    """deliberately break the substrate and confirm this exam notices.

    This is the area that replaces "pass rate" as the measure of
    quality. v2 scored 15/27 and reacted to NOTHING when the system
    was sabotaged. A qualification suite that cannot distinguish a
    working system from a broken one is decoration.

    The mutation below is the 2026-10-06 inert bug: the integration
    step multiplied by zero. It is applied in a scratch copy so the
    real substrate is untouched, and area 4 must go red.
    """
    import os
    import shutil
    import tempfile

    src = sub.SIMSELF_SRC
    if not os.path.isdir(src):
        return skip(10, "exam_self_check", "simself source not present")

    target = os.path.join(src, "constitutional", "simself.py")
    if not os.path.isfile(target):
        return skip(10, "exam_self_check", "simself.py not found")

    original = open(target, encoding="utf-8").read()
    marker = "(self.eta * self.R * 0.5) * direction"
    if marker not in original:
        return AreaResult(
            10, "exam_self_check", Status.FAIL,
            "mutation pattern not found; the substrate source has "
            "drifted and this area cannot verify itself",
            "that the exam detects the oct-6 class of defect",
        )

    tmp = tempfile.mkdtemp(prefix="atlas_mut_")
    try:
        shutil.copytree(src, os.path.join(tmp, "src"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        open(os.path.join(tmp, "src", "constitutional", "simself.py"),
             "w", encoding="utf-8").write(original.replace(marker, "0.0 * direction", 1))

        import subprocess
        env = dict(os.environ)
        env["PYTHONPATH"] = os.path.join(tmp, "src")
        code = sub.PROBE_LIVENESS
        r = subprocess.run([sys.executable, "-c", code],
                           capture_output=True, text=True, env=env,
                           timeout=sub.PROBE_TIMEOUT_S)
        # with the integration step zeroed, the probe should report
        # moved == False. if it still says True, this exam is blind.
        detected = False
        detail = "probe errored under mutation"
        try:
            payload = json.loads(r.stdout.strip().splitlines()[-1])
            detected = not payload.get("moved", True)
            detail = (f"under mutation peak drift "
                      f"{payload.get('peak_drift')}, moved="
                      f"{payload.get('moved')}")
        except (ValueError, IndexError):
            pass

        return make(
            10, "exam_self_check", detected,
            f"oct-6 mutation applied; {detail}",
            "that this exam catches every defect class. It catches one. "
            "A different sabotage may still slip through, which is why "
            "mutation yield -- defects found over defects planted -- is "
            "the number to track, not pass rate.",
            {"mutation": "integration step x 0", "detected": detected},
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# the exam
# ---------------------------------------------------------------------------

def run() -> ExamReport:
    present = sub.substrate_present()
    if not present["simself"]:
        results = [skip(n, name, "simself source not present")
                   for n, name in [(1, "refusal"), (2, "identity"),
                                   (3, "boundedness"), (4, "liveness"),
                                   (5, "return")]]
        results += [a6(), a7(), a8(), a9(), a10()]
        return ExamReport(results)
    return ExamReport([area_1_refusal(), area_2_identity(),
                       area_3_boundedness(), area_4_liveness(),
                       area_5_return(), a6(), a7(), a8(), a9(), a10()])


def a6(): return area_6_provenance()
def a7(): return area_7_reconciliation()
def a8(): return area_8_observability()
def a9(): return area_9_envelope()
def a10(): return area_10_selfcheck()


def _main(argv: List[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    if argv[0] == "--list":
        from . import AREAS
        for n, name in AREAS:
            print(f"  {n:>2}  {name}")
        print(f"\n  {len(AREAS)} areas")
        return 0

    if argv[0] == "--run":
        rep = run()
        print("=" * 70)
        print("ATLAS EXAM — the load-bearing artifact")
        print("=" * 70)
        for r in rep.results:
            print(f"\n  [{r.status.value:4}] {r.number:>2} {r.name}")
            print(f"         {r.detail}")
            print(f"         does NOT establish: {r.does_not_establish}")
        print(f"\n  passed {rep.passed}/{rep.total}")
        print(f"  not implemented: {rep.todo}")
        if rep.skipped:
            print(f"  skipped: {rep.skipped}")
        print(f"\n  VERDICT: {rep.verdict()}")
        return 0 if rep.verdict() == "PASS" else 1

    if argv[0] == "--json":
        print(json.dumps(run().to_dict(), indent=2))
        return 0

    print(f"unknown command: {argv[0]}")
    return 1


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))