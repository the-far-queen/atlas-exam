"""
test_self_coding_area.py -- AREA 18's CHECKS CAN GO RED.

THE RULE
--------
CENTRAL-RULES.md rule 7: a test that cannot fail is not a test. And
the rule that governs this file specifically: an area that PASSED while
establishing nothing is WORSE than an area that failed, because a pass
reads as coverage.

**AND AREA 18 IS THE PROOF.** Until 2026-11-09 it was graded by
reachability alone -- "is `coding_operator_object.py` referenced by
anything?" -- and it PASSED, while the module it names had no sandbox,
no comparison against the running system, and no rollback. So this file
does what the old area never did: it breaks the SUBSTRATE on purpose
and requires the area to go RED.

THE MUTATIONS
-------------
Each one removes one of the four shapes from the substrate's own
cycle, and each must turn area 18 RED:

    M1  the sandbox IS the live tree
        -> the live tree must be untouched by a trial
    M2  the comparison stops counting the tasks a variant completes
        -> a variant that completes FEWER tasks must not hold
    M3  the rollback does not restore the tree
        -> an adoption whose verification fails must be undone
    M4  the goal contract stops requiring a stop rule
        -> a goal that describes EFFORT and never ends must be refused

AND THE HARNESS'S OWN RULES, which the substrate's harness taught:
  * the baseline must be GREEN FIRST;
  * the mutated source must still COMPILE -- a RED caused by a file
    that does not parse is not a caught mutation;
  * the source must be restored BYTE-EXACTLY, because the working tree
    is CRLF on this machine and a text round trip changes the bytes;
  * the bytecode cache is purged before every run.

Run:
    cd atlas-exam && python -m pytest tests/test_self_coding_area.py -q
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
SUBSTRATE = pathlib.Path(
    os.path.expanduser("~/AppData/Local/hermes/work_repos/simself/src/"
                       "autocode/self_coding_cycle.py"))
AREA = REPO / "src" / "exam" / "self_coding.py"

PYTHON = os.environ.get("SELF_CODING_PYTHON", sys.executable)


# ---------------------------------------------------------------------------
# THE MUTATIONS -- each removes ONE mechanism from the substrate
# ---------------------------------------------------------------------------

def m1_the_sandbox_is_the_live_tree(src: str) -> str:
    old = "    return Sandbox(repo=repo, path=dest, root=root)"
    new = ("    return Sandbox(repo=repo, path=repo, root=root)"
           "  # MUTATED: the sandbox IS the live tree")
    if old not in src:
        raise SystemExit("mutation 1: the sandbox's path is not in the "
                         "substrate")
    return src.replace(old, new, 1)


def m2_the_task_count_is_not_compared(src: str) -> str:
    old = "    if after.completed < before.completed:"
    new = ("    if False and after.completed < before.completed:"
           "  # MUTATED")
    if old not in src:
        raise SystemExit("mutation 2: the comparison's task-count rule "
                         "is not in the substrate")
    return src.replace(old, new, 1)


def m3_the_rollback_does_not_restore(src: str) -> str:
    old = "            restored = _restore_tree(repo)"
    new = "            restored = True  # MUTATED: nothing is restored"
    if old not in src:
        raise SystemExit("mutation 3: the rollback's restore is not in "
                         "the substrate")
    return src.replace(old, new, 1)


def m4_the_stop_rule_is_not_required(src: str) -> str:
    old = "        if parse_stop_rule(self.stop_rule) is None:"
    new = ("        if False and parse_stop_rule(self.stop_rule) is None:"
           "  # MUTATED")
    if old not in src:
        raise SystemExit("mutation 4: the stop-rule check is not in the "
                         "substrate")
    return src.replace(old, new, 1)


MUTATIONS = (
    ("M1 the sandbox IS the live tree", m1_the_sandbox_is_the_live_tree),
    ("M2 the comparison stops counting the tasks",
     m2_the_task_count_is_not_compared),
    ("M3 the rollback does not restore the tree",
     m3_the_rollback_does_not_restore),
    ("M4 the goal contract stops requiring a stop rule",
     m4_the_stop_rule_is_not_required),
)


# ---------------------------------------------------------------------------
# THE HARNESS
# ---------------------------------------------------------------------------

def _purge_bytecode() -> None:
    for root in (SUBSTRATE.parent, REPO / "src" / "exam"):
        for pyc in root.rglob("__pycache__/*.pyc"):
            try:
                pyc.unlink()
            except OSError:
                pass


def run_area() -> tuple:
    """Run area 18. Returns (status, the detail).

    AND THE PACKAGE'S OWN `src/` IS ON THE PATH, because the exam
    package lives in `src/exam/` -- and a subprocess that cannot import
    it measures the PATH, not the area.
    """
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO / "src"), env.get("PYTHONPATH", "")]
    ).strip(os.pathsep)
    proc = subprocess.run(
        [PYTHON, "-m", "exam.self_coding"], cwd=str(REPO),
        capture_output=True, text=True, timeout=600, env=env)
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()
        return "ERROR", tail[-1] if tail else "exit %d" % proc.returncode
    try:
        data = json.loads(proc.stdout)
    except ValueError:
        return "ERROR", "the area did not emit JSON"
    return data.get("status", "?"), data.get("detail", "")


def test_the_area_is_green_on_the_real_substrate():
    """The area PASSES on the substrate as it stands.

    AND THIS IS THE BASELINE. A mutation run against a red baseline
    proves nothing, so the baseline is asserted first.
    """
    status, detail = run_area()
    assert status == "PASS", "the area is %s on the real substrate: %s" % (
        status, detail[:300])


def test_each_mutation_turns_the_area_red():
    """Each mutation must turn area 18 RED.

    AND THE MUTATED SOURCE MUST COMPILE. A RED caused by a file that
    does not parse is not a caught mutation -- it is a broken
    measurement wearing a result's clothes.
    """
    original = SUBSTRATE.read_bytes()
    original_digest = hashlib.sha256(original).hexdigest()
    backup = SUBSTRATE.with_suffix(".py.area-mutation-backup")
    failures = []

    try:
        for label, mutate in MUTATIONS:
            src = mutate(original.decode("utf-8"))
            if src == original.decode("utf-8"):
                failures.append("%s: the mutation changed nothing" % label)
                continue
            try:
                compile(src, str(SUBSTRATE), "exec")
            except SyntaxError as exc:
                failures.append("%s: the mutated source did not compile: %s"
                                % (label, exc))
                continue
            backup.write_bytes(original)
            SUBSTRATE.write_bytes(src.encode("utf-8"))
            _purge_bytecode()
            status, detail = run_area()
            SUBSTRATE.write_bytes(original)
            _purge_bytecode()
            if status == "PASS":
                failures.append("%s: the area stayed GREEN (rc %s)"
                                % (label, status))
            else:
                print("   %s -> %s: %s" % (label, status, detail[:120]))
    finally:
        if backup.is_file():
            SUBSTRATE.write_bytes(backup.read_bytes())
            try:
                backup.unlink()
            except OSError:
                pass
        _purge_bytecode()

    # -- and the substrate must be back BYTE-EXACTLY ------------------
    after = hashlib.sha256(SUBSTRATE.read_bytes()).hexdigest()
    if after != original_digest:
        failures.append("the substrate was left mutated: %s -> %s"
                        % (original_digest[:12], after[:12]))

    assert not failures, "; ".join(failures)
