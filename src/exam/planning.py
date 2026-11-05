"""
planning.py -- AREA 22. Is a plan STATE?

WHY THIS AREA
-------------
The stub said: "a plan must be state -- ordered steps, dependencies,
partial failure, and a rollback path. a plan that cannot be abandoned is
not a plan."

The substrate has `simself/src/executive_planner.py`, which produces a
`TaskDecomposition` with components, specs, milestones, risks and an
estimate. That is most of a plan. What it does NOT have is the part
the stub names last and the part that matters most:

    A PLAN THAT CANNOT BE ABANDONED IS NOT A PLAN.

A list of things to do is a TODO. A plan is a structure that can be
PARTLY DONE and partly failed, and can be STOPPED.

THE FOUR THINGS THIS AREA MEASURES
----------------------------------
    P1  THE PLAN IS ORDERED. The steps have a sequence, and the
        sequence is not an accident of a set's iteration order.

    P2  THE DEPENDENCIES ARE NAMED. A step says what it needs. A plan
        whose steps all depend on nothing is a plan whose steps can
        all be done in any order, which is a list.

    P3  PARTIAL FAILURE IS REPRESENTED. A step can fail, and the plan
        can still say what happens to the steps that come after it.
        This is the property that separates a plan from a checklist.

    P4  THE PLAN CAN BE ABANDONED. There is a way to stop, and it
        leaves the plan in a state that says it was stopped.

AND WHY THE LAST ONE IS THE LOAD-BEARING ONE
---------------------------------------------
P1, P2 and P3 can all be satisfied by a structure that is only ever
executed to completion. So P4 is checked FIRST: if the substrate
cannot abandon a plan, then the other three are a description of a
program and not a plan, and the area says so.

THE CONTROL, because the first three are easy to fake
------------------------------------------------------
A plan structure can be built that satisfies P1, P2 and P3 on paper
and is completely inert: it holds the steps and never runs them. So
the area also measures that the plan EXECUTES -- that running the plan
actually visits the steps in order, in a sandbox, and that a failure at
one step is VISIBLE in the outcome.

That is what makes it an area rather than a data-shape check: the
structure is graded by RUNNING it.

WHY A SUBPROCESS
----------------
The exam points AT the substrate. A bug in the substrate's helper would
become a passing grade. The plan runs in a sandbox the probe owns, so
the substrate's real tree is never touched.

Run: python -m exam.planning
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Tuple

from .result import AreaResult, Status

HERMES = os.path.expanduser("~/AppData/Local/hermes")
WORK_REPOS = os.path.join(HERMES, "work_repos")
SIMSELF_SRC = os.path.join(WORK_REPOS, "simself", "src")
FIELDCORE_SRC = os.path.join(WORK_REPOS, "fieldcore", "src")

PROBE_TIMEOUT_S = 180

#: The request the substrate's planner is asked to plan.
REQUEST = "Build a thing that reads files and writes a report"

#: The step the probe makes fail. It is a FOUNDATION-layer step, so
#: failing it SKIPS the layers above it -- which is what makes P3
#: measurable rather than assumed.
FAIL_AT = "core_logic"


def _run(code: str, timeout: int = PROBE_TIMEOUT_S
         ) -> Tuple[bool, Dict[str, Any], str]:
    """run a probe in a fresh interpreter. loud failure only."""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [SIMSELF_SRC, FIELDCORE_SRC, env.get("PYTHONPATH", "")]
    ).strip(os.pathsep)
    try:
        r = subprocess.run([sys.executable, "-c", code],
                           capture_output=True, text=True, env=env,
                           timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, {}, "probe exceeded %ds" % timeout
    if r.returncode != 0:
        tail = (r.stderr or "").strip().splitlines()
        return False, {}, (tail[-1] if tail else "exit %d" % r.returncode)
    out = (r.stdout or "").strip()
    if not out:
        return False, {}, "probe produced no output"
    try:
        return True, json.loads(out.splitlines()[-1]), ""
    except ValueError as exc:
        return False, {}, "probe emitted non-JSON: %s" % exc


#: THE PROBE.
#:
#: The substrate's own planner produces the decomposition, and the
#: substrate's own plan state is exercised by running it.
PROBE_PLAN = r"""
import json, sys, os, tempfile
sys.path.insert(0, os.path.join(os.path.expanduser("~"), "AppData", "Local",
                                "hermes", "work_repos", "simself", "src"))
from executive_planner import SeniorEngineerPlanner

# AND THE PLAN STATE IS THE SUBSTRATE'S, NOT THE EXAM'S.
#
# MEASURED 2026-11-05: this probe used to DEFINE `class Step` and
# `class Plan` inline -- 60 lines of the exam's own code -- and then
# measure THAT. So the area 22 probe graded the exam's own homework:
# the substrate's plan behaviour was never what the area measured, and
# the area was named as the weakest of the eight for exactly that
# reason.
#
# The state machine now lives in the substrate, at
# `simself/src/plan_state.py`, and this probe IMPORTS it. So what the
# area measures is what the substrate does.
#
# AND THE API IS THE SUBSTRATE'S, not the exam's old inline copy:
#   - `Plan.run(runner)` takes a CALLABLE, not a `fail_on=` name
#   - `Step.needs` and `Step.status` are TYPED (StepStatus)
#   - a plan whose dependencies form a CYCLE is refused AT CONSTRUCTION
#     -- and the exam's inline copy had no such check at all, so the
#     area never measured it
from plan_state import Plan, Step, StepStatus, PlanStatus

REQUEST = %r
FAIL_AT = %r

out = {}

planner = SeniorEngineerPlanner()
d = planner.decompose(REQUEST)

out['decomposition'] = {
    'components': list(d.components),
    'n_components': len(d.components),
    'n_specs': len(d.specs),
    'milestones': list(d.milestones),
    'n_risks': len(d.risk_factors),
    'estimated_hours': d.estimated_hours,
    'understanding': d.understanding,
}

# --- THE PLAN, FROM THE SUBSTRATE'S OWN PLANNER ------------------------
# NOT assembled here. The steps, their ORDER and their DEPENDENCIES are
# the substrate's decomposition read as a layered build, so the area
# measures the SUBSTRATE's plan and not a plan the exam invented.
#
# AND THE LAYERS ARE WHY THE FAILURE PROPAGATES. The decomposition's
# milestones are the layers, and a layer needs the layer before it. So
# failing a Foundation step SKIPS the Core and Polish steps above it,
# and the area asserts they were skipped rather than passed.
plan = planner.plan_for(REQUEST)
out['plan'] = plan.to_dict()
out['n_steps'] = len(plan.steps)
out['n_dependencies'] = sum(len(s.needs) for s in plan.steps)
out['named_dependencies'] = [
    {'step': s.name, 'needs': list(s.needs)} for s in plan.steps if s.needs]

# --- THE SUBSTRATE'S OWN STATUS VOCABULARY ----------------------------
# The exam must not INVENT the words it grades against, or it would be
# grading its own vocabulary. So the probe reports the substrate's own
# enum values, and the checks below compare against THESE.
out['step_statuses'] = {s.name: s.value for s in StepStatus}
out['plan_statuses'] = {s.name: s.value for s in PlanStatus}

# --- P1: the order is DECLARED, and it is STABLE ------------------------
# Two plans built from the same request must have the same order, and
# the order must not be an accident of a set's iteration.
plan2 = planner.plan_for(REQUEST)
out['repeat_order_matches'] = ([s.name for s in plan.steps]
                               == [s.name for s in plan2.steps])
out['order_matches_components'] = ([s.name for s in plan.steps]
                                   == list(d.components))

# --- P3: PARTIAL FAILURE, and the steps that depend on it are SKIPPED --
# AND THE FAILURE IS RAISED BY THE RUNNER, because the substrate's
# `run` takes a callable -- the substrate decides what a raised error
# MEANS for the rest of the plan, which is the behaviour the area is
# for.
plan_fail = planner.plan_for(REQUEST)

def _runner(step):
    if step.name == FAIL_AT:
        raise RuntimeError('this step failed on purpose')

plan_fail.run(_runner)
out['partial_failure'] = plan_fail.to_dict()

# --- P4: THE PLAN CAN BE ABANDONED ------------------------------------
plan_abandon = planner.plan_for(REQUEST)
plan_abandon.abandon('the exam is measuring the abandonment')
out['abandoned'] = plan_abandon.to_dict()

# --- AND THE SUBSTRATE REFUSES A CYCLIC PLAN AT CONSTRUCTION ---------
# AND THE EXAM'S INLINE COPY HAD NO SUCH CHECK, so this was never
# measured. A plan whose dependencies form a cycle can never be run,
# and the substrate says so when the plan is BUILT -- before any work
# is done.
out['cycle_refused'] = False
try:
    Plan([Step('a', ('b',), 'a'), Step('b', ('a',), 'b')])
except ValueError:
    out['cycle_refused'] = True

# --- and the plan runs to completion when nothing fails -----------------
plan_ok = planner.plan_for(REQUEST)
plan_ok.run(lambda step: None)
out['completed'] = plan_ok.to_dict()

print(json.dumps(out))
""" % (REQUEST, FAIL_AT)


def check_planning() -> AreaResult:
    """AREA 22 -- planning.

    Four items, all binary, all measured:

      P1  the plan is ORDERED: the steps run in a declared sequence
      P2  the dependencies are NAMED: a step says what it needs
      P3  partial failure is REPRESENTED: a failed step leaves the
          steps that depend on it SKIPPED, not silently passed
      P4  the plan CAN BE ABANDONED, and the abandonment is on the
          record with a reason
    """
    measured: Dict[str, Any] = {}
    parts: List[str] = []

    ok, data, err = _run(PROBE_PLAN)
    if not ok:
        return AreaResult(
            number=22, name="planning", status=Status.SKIP,
            detail="the planning probe could not run: %s" % err,
            does_not_establish=(
                "any planning capability -- the probe did not run"),
            measured=measured,
        )

    dec = data["decomposition"]
    plan = data["plan"]
    partial = data["partial_failure"]
    abandoned = data["abandoned"]
    completed = data["completed"]

    # THE SUBSTRATE'S OWN STATUS WORDS. The exam does not invent the
    # vocabulary it grades against -- it asks the substrate what its
    # statuses are called, and compares against those. Otherwise the
    # exam would be grading its own spelling of the substrate's states.
    SS = data["step_statuses"]
    PS = data["plan_statuses"]
    measured["step_statuses"] = sorted(SS.values())
    measured["plan_statuses"] = sorted(PS.values())

    measured["planner_components"] = dec["n_components"]
    measured["planner_milestones"] = len(dec["milestones"])
    measured["planner_risks"] = dec["n_risks"]
    measured["plan_steps"] = data["n_steps"]
    measured["plan_dependencies"] = data["n_dependencies"]

    # ---- P1: the plan is ordered ---------------------------------------
    if data["n_steps"] < 2:
        return AreaResult(
            number=22, name="planning", status=Status.FAIL,
            detail="the plan has %d step(s). A plan with one step has no "
                   "order to violate, and an order that cannot be "
                   "violated is not an order." % data["n_steps"],
            does_not_establish="that the plan is ordered",
            measured=measured,
        )
    if not data["repeat_order_matches"]:
        return AreaResult(
            number=22, name="planning", status=Status.FAIL,
            detail="the substrate's own planner produced a DIFFERENT "
                   "ordering on the second build of the same request. A "
                   "plan whose order varies between two identical "
                   "requests cannot be run twice.",
            does_not_establish="that the plan is ordered",
            measured=measured,
        )
    if not data["order_matches_components"]:
        return AreaResult(
            number=22, name="planning", status=Status.FAIL,
            detail="the plan's step order does not match the order of the "
                   "decomposition it was built from. A plan whose order is "
                   "not the decomposition's order has an order that came "
                   "from somewhere else.",
            does_not_establish="that the plan is ordered",
            measured=measured,
        )
    parts.append("P1: the plan has %d steps in a declared order that "
                 "matches its decomposition, and the substrate's planner "
                 "produced the same ordering twice for the same request"
                 % data["n_steps"])

    # ---- P2: the dependencies are named --------------------------------
    if data["n_dependencies"] < 1:
        return AreaResult(
            number=22, name="planning", status=Status.FAIL,
            detail="no step names a dependency. A plan whose steps all "
                   "depend on nothing can be done in any order, and that "
                   "is a list.",
            does_not_establish="that the plan has dependencies",
            measured=measured,
        )
    named = data["named_dependencies"]
    if not named:
        return AreaResult(
            number=22, name="planning", status=Status.FAIL,
            detail="no step in the plan names what it needs.",
            does_not_establish="that the plan has dependencies",
            measured=measured,
        )
    parts.append("P2: %d step(s) name their dependencies (%d in total)"
                 % (len(named), data["n_dependencies"]))

    # ---- P3: partial failure is represented ---------------------------
    failed = [s for s in partial["steps"] if s["status"] == SS["FAILED"]]
    skipped = [s for s in partial["steps"] if s["status"] == SS["SKIPPED"]]
    if not failed:
        return AreaResult(
            number=22, name="planning", status=Status.FAIL,
            detail="the plan ran with a step set to fail, and no step was "
                   "marked failed. A plan that cannot represent failure "
                   "cannot be resumed.",
            does_not_establish="that partial failure is represented",
            measured=measured,
        )
    if partial["status"] != PS["FAILED"]:
        return AreaResult(
            number=22, name="planning", status=Status.FAIL,
            detail="a step failed but the plan's own status is %r, not "
                   "'failed'. The plan does not know it failed."
                   % partial["status"],
            does_not_establish="that partial failure is represented",
            measured=measured,
        )
    # AND THE STEPS THAT DEPENDED ON IT MUST BE SKIPPED, not passed.
    failed_names = {s["name"] for s in failed}
    dependent_skipped = True
    for s in partial["steps"]:
        if s["status"] == SS["DONE"]:
            for dep in s.get("needs", []):
                if dep in failed_names:
                    dependent_skipped = False
    if not dependent_skipped:
        return AreaResult(
            number=22, name="planning", status=Status.FAIL,
            detail="a step was marked done even though a step it depends "
                   "on FAILED. A plan that runs dependents of a failed "
                   "step is a plan that hides the failure.",
            does_not_establish="that partial failure is represented",
            measured=measured,
        )
    # AND THE SKIP MUST HAVE ACTUALLY HAPPENED. A check that asserts
    # "no dependent was wrongly done" passes just as well on a plan
    # where the failure propagated NOWHERE -- which is not a plan that
    # represents failure, it is a plan where nothing depends on
    # anything. The first version of this area passed on a plan whose
    # failure skipped nothing (MEASURED: "0 dependent step(s) were
    # skipped"). So the area now REQUIRES that the failure skipped at
    # least one dependent step.
    measured["partial_failure_skipped"] = len(skipped)
    if not skipped:
        return AreaResult(
            number=22, name="planning", status=Status.FAIL,
            detail="a step failed and NO dependent step was skipped -- the "
                   "failure propagated nowhere. A plan where nothing "
                   "depends on anything is a list, and a failure in a list "
                   "has no consequence.",
            does_not_establish="that partial failure is represented",
            measured=measured,
        )
    parts.append("P3: a failed step is marked failed, the plan's status "
                 "becomes 'failed', and %d dependent step(s) were skipped "
                 "rather than passed" % len(skipped))

    # ---- P5: THE SUBSTRATE REFUSES A PLAN THAT CAN NEVER BE RUN -----
    # AND THIS CHECK DID NOT EXIST, because the exam's inline copy of
    # the plan state had NO cycle check at all -- so the area could not
    # have measured it. Now that the probe imports the substrate's
    # real `plan_state`, the substrate REFUSES a plan whose
    # dependencies form a cycle, at CONSTRUCTION -- before any work is
    # done.
    #
    # AND A CYCLE IS WORTH MEASURING: a plan whose dependencies form a
    # cycle can never be run, and a plan that cannot be run is a
    # document, not a plan.
    measured["cycle_refused"] = bool(data.get("cycle_refused"))
    if not data.get("cycle_refused"):
        return AreaResult(
            number=22, name="planning", status=Status.FAIL,
            detail="the substrate accepted a plan whose dependencies form "
                   "a cycle. A plan that can never be run is a document, "
                   "not a plan -- and it should be refused when it is "
                   "BUILT, before any work is done.",
            does_not_establish="that the substrate refuses a plan that "
                               "can never be run",
            measured=measured,
        )
    parts.append("P5: the substrate refuses a plan whose dependencies form "
                 "a cycle, at construction")

    # ---- P4: the plan can be abandoned ---------------------------------
    if abandoned["status"] != PS["ABANDONED"]:
        return AreaResult(
            number=22, name="planning", status=Status.FAIL,
            detail="the plan could not be abandoned (status %r). A plan "
                   "that cannot be abandoned is not a plan."
                   % abandoned["status"],
            does_not_establish="that the plan can be abandoned",
            measured=measured,
        )
    if not abandoned["abandon_reason"].strip():
        return AreaResult(
            number=22, name="planning", status=Status.FAIL,
            detail="the plan was abandoned with no reason recorded. An "
                   "abandonment nobody can explain is indistinguishable "
                   "from a failure.",
            does_not_establish="that the abandonment is on the record",
            measured=measured,
        )
    still_pending = [s for s in abandoned["steps"]
                     if s["status"] == SS["PENDING"]]
    if still_pending:
        return AreaResult(
            number=22, name="planning", status=Status.FAIL,
            detail="%d step(s) are still 'pending' after the abandonment. "
                   "An abandoned plan must say what it did not do."
                   % len(still_pending),
            does_not_establish="that the abandonment is complete",
            measured=measured,
        )
    parts.append("P4: the plan was abandoned, the reason was recorded, and "
                 "every step says it was skipped")

    # ---- and the plan runs to completion when nothing fails ------------
    # WITHOUT THIS, THE AREA COULD PASS ON A PLAN THAT CAN ONLY FAIL. A
    # structure that always reports "failed" satisfies P3 trivially. So
    # the same plan, run with nothing failing, must COMPLETE, with every
    # step done.
    if completed["status"] != PS["COMPLETED"]:
        return AreaResult(
            number=22, name="planning", status=Status.FAIL,
            detail="the plan ran with no failures and its status is %r, not "
                   "'completed'. A plan that never completes is not a plan."
                   % completed["status"],
            does_not_establish="that the plan completes",
            measured=measured,
        )
    not_done = [s for s in completed["steps"] if s["status"] != SS["DONE"]]
    if not_done:
        return AreaResult(
            number=22, name="planning", status=Status.FAIL,
            detail="the plan ran with no failures and %d step(s) are not "
                   "done." % len(not_done),
            does_not_establish="that the plan completes",
            measured=measured,
        )
    parts.append("the same plan with no failure runs to completion with "
                 "every step done")

    return AreaResult(
        number=22, name="planning", status=Status.PASS,
        detail="; ".join(parts),
        does_not_establish=(
            "that the plan is GOOD, or that it would achieve anything. It "
            "establishes that a plan is STATE: ordered steps, named "
            "dependencies, a represented partial failure, and a path that "
            "can be abandoned with the reason on the record. It does not "
            "cover whether the substrate's own planner produces sensible "
            "plans -- only that it produces them consistently and that "
            "the structure can be executed, failed and abandoned."),
        measured=measured,
    )


def _main(argv: List[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    r = check_planning()
    print("=" * 70)
    print("AREA 22 planning: %s" % r.status.value)
    print("=" * 70)
    print(r.detail)
    print()
    print("does NOT establish:")
    print("  %s" % r.does_not_establish)
    print()
    print(json.dumps(r.measured, indent=2))
    return 0 if r.status is Status.PASS else 1


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
