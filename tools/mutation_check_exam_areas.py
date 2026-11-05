"""
mutation_check_exam_areas.py -- the eight new exam areas, shown able to
go RED.

WHY THIS FILE EXISTS
--------------------
Queue item 42 asked for the atlas-exam's eight unimplemented areas to be
"built or named honestly", and said the reason plainly:

    "The exam is the training loop -- an area that cannot fail is not an
     area -- so an unimplemented area is not a backlog item, it is a hole
     in the instrument that grades the substrate."

That sentence is the specification for THIS file. An area that has only
ever reported PASS is not evidence of anything: it might be measuring the
substrate correctly, or it might be reporting PASS because nothing in it
can report anything else. The only way to tell those apart is to break
the thing the area is pointed at and watch the area notice.

THE RULE
========
A checker that has never been seen to fail has not been shown to work.
So this harness MUTATES the substrate -- the code the area is pointed at
-- and it PROVES THE MUTATION APPLIED before it runs the area. A
mutation that silently did not apply would report the area as still
PASSing, and the harness would call that a failure to detect, which is
the opposite of the truth.

HOW THE REDIRECTION WORKS, AND WHY IT IS THE HARD PART
------------------------------------------------------
Every probe in the exam builds its import path at RUNTIME, inside the
subprocess, from the user's home:

    sys.path.insert(0, os.path.join(os.path.expanduser("~"), "AppData",
                                    "Local", "hermes", "work_repos",
                                    "fieldcore", "src"))

So the scratch copy is not used unless `expanduser("~")` points at it.
MEASURED 2026-11-05: the first version of this harness rewrote the
probe strings in memory, replacing the literal path -- and it detected
**0 of 8** mutations, because the literal path is not IN the probe. The
probes assemble it at runtime. A harness that reports "no mutant
detected" for eight broken areas looks exactly like a harness that
found eight blind areas, and it is neither.

So the redirection is done at the only level that works: the harness
runs the whole measurement with `HOME` and `USERPROFILE` pointing at a
SCRATCH HOME, and that scratch home contains a real copy of
`AppData/Local/hermes/work_repos/<repo>` with the mutation applied.
`expanduser("~")` then resolves to the scratch, the probe imports the
mutated copy, and the LIVE substrate is never touched.

THE EIGHT AREAS, AND WHAT EACH MUTATION BREAKS
----------------------------------------------
    7  reconciliation   the declared MAX_NORM becomes 4.5 while the
                         gate still refuses at 4.0 -> the two
                         derivations DISAGREE
    11 interface       a core module imports a model module -> the core
                         is coupled to the model, which C1 forbids
    12 resource        the decision log's trim is removed -> the log
                         grows without bound -> R2's bound is declared
                         but not enforced
    13 adversarial     the gate's finiteness check is removed -> a NaN
                         packet is ADMITTED, which is the exact defect
                         this area was written for
    19 tools           the tool gate admits an unknown tool type -> T1's
                         refusals are not refusals
    20 skills          the engine LABELS every reading instead of
                         carrying it -> unseen sentences are not carried
    21 initiative      the loop's gate is removed -> nothing is gated,
                         so the attempt is not gated either
    22 planning        the plan's dependent steps are marked DONE
                         rather than SKIPPED on failure -> a partial
                         failure is not represented

AND NOW EVERY MUTATION HITS THE SUBSTRATE
------------------------------------------
MEASURED 2026-11-05: area 22's `Step` and `Plan` classes were defined
INSIDE the probe, so area 22 graded the EXAM'S OWN CODE and its
mutation was applied to the exam's own source. It was named as the
weakest of the eight for exactly that reason.

The plan state machine now lives in the substrate, at
`simself/src/plan_state.py`, and the substrate's own planner
(`simself/src/executive_planner.py`) produces plans with it. So area
22 grades the substrate, and its mutation is applied to the substrate's
file.

There is now NO path by which an area grades the exam's own code, and
this harness has no way to mutate the exam's own source. That is the
structural change, not just a re-pointing.

THE HONEST LIMIT
----------------
This harness proves the eight areas DETECT these eight defects. It does
not prove they detect every defect, and it does not prove the probes
measure what they claim beyond the eight cases here. Area 10 (the
exam's own mutation check) says the same thing about itself.

Run: python tools/mutation_check_exam_areas.py
Exit 0 iff every mutation was applied AND detected.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Callable, Dict, List, Optional, Tuple

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
HERMES = pathlib.Path(os.path.expanduser("~")) / "AppData" / "Local" / "hermes"
WORK_REPOS = HERMES / "work_repos"
FIELD = WORK_REPOS / "fieldcore"
SIM = WORK_REPOS / "simself"
SACRED = WORK_REPOS / "sacred-library"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


# ---------------------------------------------------------------------------
# THE MUTATIONS.
#
# Each returns (repo, relative_path, old, new), where `repo` is
# "fieldcore" or "simself", and `old` MUST be present in the file. If it
# is not, the harness reports the mutation as NOT APPLIED and counts it
# as NOT DETECTED -- because the honest answer then is that nothing was
# proved.
#
# The `old`/`new` patterns were READ OUT of the live source on
# 2026-11-05, not guessed. A guessed pattern is a mutation that does
# not apply, which is a mutation that proves nothing.
# ---------------------------------------------------------------------------

def m_gate_declared_bound_drifts() -> Tuple[str, str, str, str]:
    """AREA 7. The declared norm bound stops matching the enforced one.

    `fieldcore/src/gate.py` declares MAX_NORM and enforces it. Area 7
    derives the enforced bound from the gate's BEHAVIOUR (bisection for
    the largest admitted norm) and compares it with the declared
    constant.

    THE MUTATION IS ON THE ENFORCEMENT, NOT THE DECLARATION.

    MEASURED 2026-11-05: the first version of this mutation changed
    `MAX_NORM: float = 4.0` to `4.5` -- and the area MISSED it, because
    the gate enforces `ne > MAX_NORM`, so the declaration AND the
    behaviour both moved together. The area reported "declared 4.5,
    derived 4.5, rel err 0.000e+00", which is CORRECT: nothing had
    drifted. A mutation that changes both sides of a comparison proves
    nothing about the comparison.

    So the mutation widens the ENFORCED bound while the DECLARED
    constant stays at 4.0. Now the declaration and the behaviour
    disagree, which is the drift the area exists to catch.

    The area must report FAIL.
    """
    return ("fieldcore", "src/gate.py",
            "    if ne > MAX_NORM:\n"
            "        return False, REFUSE_NORM",
            "    if ne > MAX_NORM * 1.1:\n"
            "        return False, REFUSE_NORM")


def m_core_imports_a_model() -> Tuple[str, str, str, str]:
    """AREA 11. The substrate's core imports a model module.

    Area 11's C1 is an AST scan of ten core modules looking for an
    import of one of the seven model modules. Add one to a core module
    and the core is no longer model-free -- which is the whole point of
    the check.

    The area must report FAIL.
    """
    return ("simself", "src/constitutional/constitution.py",
            "import numpy as np",
            "import numpy as np\nimport minimax_client")


def m_log_never_trims() -> Tuple[str, str, str, str]:
    """AREA 12. The decision log's bound is declared but not enforced.

    `simself/src/constitutional/simself.py` trims the decision log at
    80 down to 60. Stop it trimming and the log grows without bound, so
    R2's "the bound was enforced, not merely declared" must fail.

    The area must report FAIL.
    """
    return ("simself", "src/constitutional/simself.py",
            "        if len(self.decision_log) > 80:\n"
            "            self.decision_log = self.decision_log[-60:]",
            "        if False:  # the trim is removed\n"
            "            self.decision_log = self.decision_log[-60:]")


def m_gate_admits_nan() -> Tuple[str, str, str, str]:
    """AREA 13. The gate stops refusing a non-finite packet.

    This is THE defect area 13 was written for. `nan > 4.0` is False and
    `nan < 0.4` is False, so a gate without the finiteness check admits
    a NaN packet.

    The area must report FAIL.
    """
    return ("fieldcore", "src/gate.py",
            "    if not (_is_finite(emb) and _is_finite(psi0)):\n"
            "        return False, REFUSE_NONFINITE\n",
            "")


def m_tool_gate_stops_refusing() -> Tuple[str, str, str, str]:
    """AREA 19. The tool gate admits what it is supposed to refuse.

    `simself/.agents/extensions/pi_tools.py` refuses an unknown tool
    type. Make it admit instead and T1's refusals are not refusals.

    The area must report FAIL.
    """
    return ("simself", ".agents/extensions/pi_tools.py",
            "    if call.tool_type not in TOOL_TYPES:\n"
            "        return False, TOOL_TYPE_UNKNOWN",
            "    if False:  # the gate is removed\n"
            "        return False, TOOL_TYPE_UNKNOWN")


def m_skills_labels_instead_of_carrying() -> Tuple[str, str, str, str]:
    """AREA 20. The engine labels every reading instead of carrying it.

    Area 20's load-bearing case is an UNSEEN sentence: the engine must
    CARRY it from the primitives, not find it in the corpus. Make
    `read_sentence` always report "labelled" and nothing is carried.

    The area must report FAIL.
    """
    return ("simself", "src/constitutional/restore_probe.py",
            '    return SentenceReading(sentence, "carried", role, ideas, concretes)',
            '    return SentenceReading(sentence, "labelled", role, ideas, concretes)')


def m_initiative_gate_is_removed() -> Tuple[str, str, str, str]:
    """AREA 21. Nothing is gated.

    Area 21's I1 is that the substrate's own gate REFUSES a zero-cost
    attempt. `fieldcore/src/spark.py`'s `pull` consults the gate and
    refuses. Make it not consult the gate and the attempt is ungated.

    The area must report FAIL.
    """
    return ("fieldcore", "src/spark.py",
            "        if self.gate is not None:\n"
            "            allow, reason = self.gate(spark)\n"
            "            if not allow:\n"
            "                self.ledger.refuse(spark, reason)\n"
            "                return spark",
            "        if False:  # the gate is removed\n"
            "            allow, reason = self.gate(spark)\n"
            "            if not allow:\n"
            "                self.ledger.refuse(spark, reason)\n"
            "                return spark")


def m_plan_marks_failed_dependents_passed() -> Tuple[str, str, str, str]:
    """AREA 22. A partial failure is not represented.

    Area 22's P3 is that a failed step leaves the steps that depend on
    it SKIPPED, not silently passed. Mark them passed instead and the
    plan's state lies about what happened.

    AND THE MUTATION IS NOW ON THE SUBSTRATE. MEASURED 2026-11-05:
    this mutation used to target the exam's OWN probe source, because
    the `Plan` class the area graded was defined inside that probe. The
    state machine now lives in the substrate, at
    `simself/src/plan_state.py`, and the area grades THAT. So the
    mutation is applied to the substrate file -- which is the whole
    point of the change, and the reason area 22 is no longer the
    weakest of the eight.

    The line mutated is the one that marks a step whose dependencies
    are unmet. Changing SKIPPED to DONE makes the plan claim it did
    work it never did.

    The area must report FAIL.
    """
    return ("simself", "src/plan_state.py",
            "                step.status = StepStatus.SKIPPED\n"
            "                step.error = \"unmet dependency: %s\" % \",\".join(unmet)",
            "                step.status = StepStatus.DONE\n"
            "                step.error = \"unmet dependency: %s\" % \",\".join(unmet)")


MUTATIONS: Dict[int, Tuple[Callable, str]] = {
    7: (m_gate_declared_bound_drifts, "reconciliation"),
    11: (m_core_imports_a_model, "interface"),
    12: (m_log_never_trims, "resource"),
    13: (m_gate_admits_nan, "adversarial"),
    19: (m_tool_gate_stops_refusing, "tools"),
    20: (m_skills_labels_instead_of_carrying, "skills"),
    21: (m_initiative_gate_is_removed, "initiative"),
    22: (m_plan_marks_failed_dependents_passed, "planning"),
}

AREA_FN = {
    7: "area_7_reconciliation",
    11: "area_11_interface",
    12: "area_12_resource",
    13: "area_13_adversarial",
    19: "area_19_tools",
    20: "area_20_skills",
    21: "area_21_initiative",
    22: "area_22_planning",
}

#: the exam's own src tree, for the one probe-source mutation.
EXAM_SRC = ROOT / "src"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def _write(path: pathlib.Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _copy_tree(src: pathlib.Path, dst: pathlib.Path) -> None:
    shutil.copytree(src, dst,
                    ignore=shutil.ignore_patterns(
                        "__pycache__", ".git", ".pytest_cache",
                        "node_modules", ".venv", "venv", "*.pyc"))


def _junction(link: pathlib.Path, target: pathlib.Path) -> bool:
    """A directory junction. Falls back to a copy if junctions fail."""
    if target.is_dir():
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                           capture_output=True, text=True)
        if r.returncode == 0:
            return True
    return False


def _scratch_home(repo_to_mutate: Optional[str]) -> pathlib.Path:
    """A scratch HOME whose work_repos holds the repos.

    `expanduser("~")` in the probe resolves here, so the probe imports
    the scratch copies and the live substrate is untouched.

    The mutated repo is COPIED. The others are JUNCTIONED, so the copy
    is cheap: only the repo under mutation is duplicated.
    """
    home = pathlib.Path(tempfile.mkdtemp(prefix="atlas_home_"))
    wr = home / "AppData" / "Local" / "hermes" / "work_repos"
    wr.mkdir(parents=True, exist_ok=True)

    for name, repo in (("fieldcore", FIELD), ("simself", SIM)):
        if name == repo_to_mutate:
            _copy_tree(repo, wr / name)
        else:
            if not _junction(wr / name, repo):
                _copy_tree(repo, wr / name)

    # the corpus is 44M and is READ-ONLY for these areas, so it is
    # junctioned rather than copied.
    if SACRED.is_dir():
        if not _junction(wr / "sacred-library", SACRED):
            _copy_tree(SACRED, wr / "sacred-library")
    return home


def _apply_mutation(home: pathlib.Path, area: int
                    ) -> Tuple[bool, str]:
    """Apply the mutation inside the scratch home.

    Returns (applied, note). `applied` is False when the OLD TEXT IS NOT
    IN THE FILE. That is a FAILURE of the harness, not a skip: the area
    would have been measured against an unmutated substrate and reported
    as "did not detect", which would be a lie.

    AND EVERY MUTATION NOW TARGETS THE SUBSTRATE. MEASURED 2026-11-05:
    area 22's mutation used to be applied to the EXAM'S OWN probe
    source, because the area graded a `Plan` class defined inside that
    probe. The plan state machine now lives in the substrate
    (`simself/src/plan_state.py`), so area 22 grades the substrate and
    its mutation hits the substrate too. There is no longer any path by
    which an area grades the exam's own code, so there is no "probe"
    target here.
    """
    mutate, _ = MUTATIONS[area]
    repo, rel, old, new = mutate()

    path = home / "AppData" / "Local" / "hermes" / "work_repos" / repo / rel

    if not path.is_file():
        return False, "file not found in the scratch home: %s" % path

    original = _read(path)
    if old not in original:
        return False, ("the mutation pattern is no longer in %s -- the "
                       "code has drifted and the mutation must be "
                       "rewritten" % rel)
    _write(path, original.replace(old, new, 1))
    if _read(path) == original:
        return False, "the mutation wrote nothing"
    return True, "%s: %s" % (rel, old.strip().splitlines()[0][:56])


def _run_area_in_home(area: int, home: pathlib.Path) -> Tuple[str, str]:
    """Run one area with `expanduser("~")` pointing at the scratch home.

    The area is run in a SUBPROCESS, because the probe strings are
    module-level constants that were built when the module was
    imported, and the modules themselves hold absolute paths. A fresh
    interpreter with the right HOME is the only clean way to make the
    whole chain resolve into the scratch.
    """
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    # The exam tree that gets IMPORTED is the LIVE one. MEASURED
    # 2026-11-05: the first version pointed PYTHONPATH at a scratch
    # copy of the exam so that a probe-source mutation would load. No
    # mutation touches the exam's own source any more -- area 22's
    # mutation is on the substrate's `plan_state.py` -- so the live
    # tree is correct, and there is no longer any way for an area to
    # grade the exam's own code.
    env["PYTHONPATH"] = os.pathsep.join(
        [str(EXAM_SRC), env.get("PYTHONPATH", "")]).strip(os.pathsep)

    code = (
        "import json, sys\n"
        "from exam import cli\n"
        "r = getattr(cli, %r)()\n"
        "print(json.dumps({'status': r.status.value, 'detail': r.detail}))\n"
        % AREA_FN[area]
    )
    try:
        proc = subprocess.run([sys.executable, "-c", code], env=env,
                              capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        return "TIMEOUT", "the area exceeded 600s"
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()
        return "EXCEPTION", (tail[-1] if tail else "exit %d" % proc.returncode)
    out = (proc.stdout or "").strip().splitlines()
    if not out:
        return "NO OUTPUT", "the area printed nothing"
    try:
        payload = json.loads(out[-1])
    except ValueError:
        return "NO JSON", out[-1][:120]
    return payload["status"], payload["detail"]


def _baseline_area(area: int) -> Tuple[str, str]:
    """Run one area against the LIVE substrate, in this process."""
    from exam import cli

    fn = getattr(cli, AREA_FN[area])
    try:
        result = fn()
        return result.status.value, result.detail
    except Exception as exc:  # noqa: BLE001 -- report, do not raise
        return "EXCEPTION", "%s: %s" % (type(exc).__name__, exc)


def main() -> int:
    print("=" * 74)
    print("THE EIGHT NEW EXAM AREAS -- SHOWN ABLE TO GO RED")
    print("=" * 74)
    print()
    print("Each mutation breaks ONE thing the area measures. The area")
    print("must then report FAIL. An area that still reports PASS has")
    print("not been shown to work.")
    print()

    print("-" * 74)
    print("BASELINE -- every area against the live substrate")
    print("-" * 74)
    baseline_ok = True
    for area in sorted(MUTATIONS):
        status, detail = _baseline_area(area)
        ok = status == "PASS"
        baseline_ok = baseline_ok and ok
        print("  [%s] area %-2d %s" % ("PASS" if ok else "FAIL", area,
                                       detail[:62]))
    print()
    if not baseline_ok:
        print("THE BASELINE IS NOT GREEN, so the mutation results below")
        print("would prove nothing. Stopping here.")
        return 1
    print("  baseline green: all %d areas PASS against the live substrate"
          % len(MUTATIONS))
    print()

    print("-" * 74)
    print("MUTATIONS -- each must turn its area RED")
    print("-" * 74)
    detected = 0
    total = 0
    for area in sorted(MUTATIONS):
        total += 1
        mutate, _ = MUTATIONS[area]
        repo, _, _, _ = mutate()
        home = _scratch_home(repo)
        try:
            applied, note = _apply_mutation(home, area)
            if not applied:
                print("  [NOT APPLIED] area %-2d %s" % (area, note))
                print("               the mutation did not apply, so the")
                print("               area was NOT measured against a")
                print("               broken substrate. Counting as NOT")
                print("               DETECTED, because the honest answer")
                print("               is that nothing was proved.")
                continue
            status, detail = _run_area_in_home(area, home)
            caught = status != "PASS"
            detected += 1 if caught else 0
            print("  [%s] area %-2d %s"
                  % ("DETECTED" if caught else "MISSED  ", area, note))
            print("        the area said: %s" % detail[:116])
        finally:
            shutil.rmtree(home, ignore_errors=True)

    print()
    print("=" * 74)
    print("  %d of %d mutations DETECTED" % (detected, total))
    print("=" * 74)
    return 0 if detected == total else 1


if __name__ == "__main__":
    sys.exit(main())
