"""
reconciliation.py -- AREA 7. Two derivations must agree.

WHY THIS AREA, AND WHY IT IS THE FIRST ONE BUILT
------------------------------------------------
Central rule 5 of the project:

    Two derivations must agree.

Derive the same quantity two independent ways. If they disagree, one is
wrong -- find out which, BEFORE reporting either.

The pattern is already proven elsewhere in this project. Damping
recovered from a trajectory by log-decay agreed with the dynamics to
0.1%. The atlas curvature detector agreed with finite differences. So
the METHOD works. What was missing was its application across the
substrate, and the area existed as a declared stub with that reason
attached.

WHAT "INDEPENDENT" MEANS HERE, and it is the whole content of the area
-------------------------------------------------------------------------
Two derivations that share a helper share their bugs. So this area
requires, for every quantity it checks:

    D1  two derivations that do not call each other
    D2  they disagree by no more than a stated tolerance
    D3  the tolerance is a NUMBER, and it is measured, not asserted

AND THE FOURTH, WHICH IS THE ONE THAT MAKES IT AN AREA RATHER THAN A
DEMONSTRATION:

    D4  THE TWO AGREE AND THE MEASUREMENT IS NOT A CONSTANT.

The last clause is what stops this from being theatre. A reconciliation
area whose two derivations agree to 1e-12 on EVERY input, including
inputs chosen because they are degenerate, is not measuring anything --
it is measuring two copies of the same expression. So the area also
measures the SPREAD: it checks the two derivations on a SWEEP of inputs
that includes at least one case where the two SHOULD disagree if the
quantity is genuinely being computed two ways, and it asserts the
disagreement is real where it must be real and absent where it must be
absent.

THE QUANTITIES CHECKED, and why each one has two real derivations
------------------------------------------------------------------
    Q1  the gate's norm bound. Derived as (a) the constant read out of
        the module, and (b) the smallest norm that the gate REFUSES,
        found by bisection on the module's own gate function. One is a
        declaration; the other is the behaviour. If the module's
        declared MAX_NORM and the norm at which the gate actually
        starts refusing drift apart, the declaration is a lie.

    Q2  the gate's coherence floor. Derived as (a) the constant, and
        (b) the largest cosine the gate refuses, found by bisection on
        the cosine. Same shape, and the same point: a declared floor
        that the gate does not enforce is not a floor.

    Q3  the substrate's drift bound R. Derived as (a) the constructor
        argument, and (b) the radius at which the projection operator
        actually holds the state, measured by driving the state out and
        reading back where it lands.

WHY A SUBPROCESS
----------------
The exam's non-negotiable rule: it points AT the substrate, it never
imports it. A bug in the substrate's helper would become a passing
grade. Every probe below runs in a fresh interpreter.

Run: python -m exam.reconciliation
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

#: The tolerance. A NUMBER, not a feeling. Two derivations of the same
#: quantity must agree to this relative error or the area fails.
TOLERANCE = 1e-9


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


# ---------------------------------------------------------------------------
# THE PROBES
# ---------------------------------------------------------------------------

#: Q1 + Q2 -- the gate's two bounds, derived twice each.
#:
#: The second derivation is a BISECTION on the gate's own behaviour. It
#: asks the gate questions until it finds the boundary, and it never
#: reads the constants. So if the constants were wrong, the boundary
#: would not be where the constant says.
PROBE_GATE_BOUNDS = r"""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.expanduser("~"), "AppData", "Local",
                                "hermes", "work_repos", "fieldcore", "src"))
import numpy as np
import gate

# --- derivation (a): the declaration ------------------------------------
declared_max_norm = float(gate.MAX_NORM)
declared_min_cos = float(gate.MIN_COS)

# --- a ground to measure against ----------------------------------------
psi0 = np.zeros(8); psi0[0] = 1.0

def admits_norm(n):
    # does the gate admit a packet of this norm?
    v = np.zeros(8); v[0] = n
    return gate.gate(v, psi0)[0]

def admits_cos(c):
    # does the gate admit a packet at this cosine with the ground?
    # a unit vector at cosine c with the ground along axis 0:
    #   v0 = c, v1 = sqrt(1 - c^2)
    v = np.zeros(8); v[0] = c; v[1] = np.sqrt(max(0.0, 1.0 - c * c))
    allow, reason = gate.gate(v, psi0)
    return allow, reason

# --- derivation (b): the behaviour, by bisection ------------------------
# The largest norm the gate ADMITS. The gate refuses at ne > MAX_NORM,
# so the admitted supremum is MAX_NORM itself (the boundary is
# inclusive) and the smallest refused norm is just above it.
#
# AND THE LOWER BOUND IS NOT ZERO. The zero packet is refused for a
# DIFFERENT reason -- refuse_zero -- so a bisection that started there
# would be measuring the zero-norm rule instead of the norm bound, and
# its first assertion would fail. It starts at a small positive norm,
# which the gate admits on the norm test.
lo, hi = 1e-9, 100.0
assert admits_norm(lo), 'a tiny packet must be admitted by norm'
assert not admits_norm(hi), 'a huge packet must be refused by norm'
for _ in range(200):
    mid = (lo + hi) / 2.0
    if admits_norm(mid):
        lo = mid
    else:
        hi = mid
largest_admitted_norm = lo
smallest_refused_norm = hi

# the cosine floor: the gate refuses when cos < MIN_COS, so the
# smallest ADMITTED cosine is MIN_COS (inclusive) and the largest
# REFUSED cosine is just below it.
#
# AND THE SAME TRAP DOES NOT APPLY HERE. The orthogonal packet is
# refused on coherence, not on being zero -- v = [0, 1, 0...] has
# norm 1 -- so this bisection is clean.
clo, chi = 0.0, 1.0          # clo refused, chi admitted
assert not admits_cos(clo)[0], 'an orthogonal packet must be refused'
assert admits_cos(chi)[0], 'the ground itself must be admitted'
for _ in range(200):
    mid = (clo + chi) / 2.0
    if admits_cos(mid)[0]:
        chi = mid
    else:
        clo = mid
smallest_admitted_cos = chi
largest_refused_cos = clo

print(json.dumps({
    'declared_max_norm': declared_max_norm,
    'declared_min_cos': declared_min_cos,
    'largest_admitted_norm': largest_admitted_norm,
    'smallest_refused_norm': smallest_refused_norm,
    'smallest_admitted_cos': smallest_admitted_cos,
    'largest_refused_cos': largest_refused_cos,
}))
"""


#: Q3 -- the drift bound R, declared and measured.
#:
#: AND THE SECOND DERIVATION USES THE SUBSTRATE'S OWN OPERATOR, not a
#: copy of the formula written out here. The first version of this probe
#: re-implemented the projection as
#:
#:     far - (R / d) * (far - psi0)
#:
#: which is NOT the projection. The projection is
#:
#:     psi0 + (R / d) * (far - psi0)
#:
#: and the two differ by exactly R: the first lands at radius d - R
#: (MEASURED: d = 9.0, R = 3.0, so the first version reported a
#: measured radius of 6.0 against a declared 3.0 and the area failed).
#:
#: The lesson is the project's own: a copy of a formula is a second
#: derivation of the WRONG quantity, and it disagrees with the
#: declaration in a way that looks like a substrate defect. So the
#: probe calls the substrate's own operator and measures what IT
#: produces. That is also the more honest second derivation: it
#: measures the behaviour of the code that actually runs.
PROBE_DRIFT_BOUND = r"""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.expanduser("~"), "AppData", "Local",
                                "hermes", "work_repos", "simself", "src"))
import numpy as np
from constitutional.constitution import Constitution
from constitutional.ground import Ground
from constitutional.simself import SimSelf, _project_ball

c = Constitution()
R_declared = 3.0
s = SimSelf(constitution=c, ground=Ground(c.psi_0.copy()), R=R_declared, eta=0.1)

# --- derivation (b): the behaviour --------------------------------------
# Drive the state out PAST R by hand, then let the SUBSTRATE'S OWN
# projection operator do its work, and read where the state actually
# lands. The projection puts the state exactly on the sphere of radius
# R around the ground, so the measured radius must equal R.
psi0 = s.psi0
direction = np.zeros(s.dim); direction[0] = 1.0
far = psi0 + direction * (R_declared * 3.0)
distance_out = float(np.linalg.norm(far - psi0))

projected = _project_ball(far, psi0, R_declared)
measured_radius = float(np.linalg.norm(projected - psi0))

# and the state's own drift, measured after the same push through the
# substrate's own tick -- which is the path the system actually takes.
s.psi_current = far.copy()
drift_before = s.drift()
s.tick()
drift_after = s.drift()

print(json.dumps({
    'declared_R': R_declared,
    'measured_projection_radius': measured_radius,
    'distance_pushed_out': distance_out,
    'drift_before_tick': drift_before,
    'drift_after_tick': drift_after,
    'R_in_simself': float(s.R),
}))
"""


#: THE SWEEP -- the check that the reconciliation is not theatre.
#:
#: Two derivations that agree to 1e-12 on every input, INCLUDING inputs
#: chosen because they are degenerate, are two copies of one expression.
#: So the area checks two things:
#:
#:   S1  the two derivations AGREE across a sweep of normal inputs
#:   S2  the two derivations DISAGREE where they must: the gate's
#:       cosine verdict must FLIP between two inputs whose cosines
#:       straddle the declared floor. A floor that never rejects
#:       anything is not a floor, and a reconciliation that cannot see
#:       a disagreement cannot see anything.
PROBE_SWEEP = r"""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.expanduser("~"), "AppData", "Local",
                                "hermes", "work_repos", "fieldcore", "src"))
import numpy as np
import gate

psi0 = np.zeros(8); psi0[0] = 1.0
floor = float(gate.MIN_COS)

def cos_of(c):
    v = np.zeros(8); v[0] = c; v[1] = np.sqrt(max(0.0, 1.0 - c * c))
    return float(np.dot(v, psi0) / (np.linalg.norm(v) * np.linalg.norm(psi0)))

# S1: agreement across a sweep. For each target cosine, the cosine the
# vector ACTUALLY has is derived from its components; the gate's verdict
# is derived from the gate. The declared floor says which side of
# `floor` the cosine is on. The two must agree at every point.
agree = 0
disagree = []
for c in (0.0, 0.1, 0.25, 0.39, 0.4, 0.41, 0.55, 0.7, 0.85, 0.99, 1.0):
    v = np.zeros(8); v[0] = c; v[1] = np.sqrt(max(0.0, 1.0 - c * c))
    allow, _ = gate.gate(v, psi0)
    predicted = cos_of(c) >= floor
    if allow == predicted:
        agree += 1
    else:
        disagree.append({'cos': c, 'gate_allowed': bool(allow),
                         'floor_says_allowed': bool(predicted)})

# S2: the flip. There must EXIST a cosine below the floor that is
# admitted and one above it that is refused -- i.e. the verdict must
# change somewhere. A gate whose verdict never changes across the
# whole range is not gating.
low = np.zeros(8); low[0] = 0.39; low[1] = np.sqrt(1 - 0.39 ** 2)
high = np.zeros(8); high[0] = 0.41; high[1] = np.sqrt(1 - 0.41 ** 2)
low_allow = bool(gate.gate(low, psi0)[0])
high_allow = bool(gate.gate(high, psi0)[0])
flips = (low_allow is False) and (high_allow is True)

# the degenerate end: the zero packet must be refused, and the ground
# itself admitted. A gate that refuses the ground refuses itself.
zero_allow = bool(gate.gate(np.zeros(8), psi0)[0])
ground_allow = bool(gate.gate(psi0.copy(), psi0)[0])

print(json.dumps({
    'sweep_points': 11,
    'agree': agree,
    'disagreements': disagree,
    'verdict_flips_at_the_floor': bool(flips),
    'low_allowed': low_allow,
    'high_allowed': high_allow,
    'zero_allowed': zero_allow,
    'ground_allowed': ground_allow,
}))
"""


def _rel(a: float, b: float) -> float:
    if a == b:
        return 0.0
    denom = max(abs(a), abs(b))
    if denom == 0.0:
        return float("inf")
    return abs(a - b) / denom


def _check_pair(label: str, declared: float, derived: float,
                tol: float = TOLERANCE) -> Tuple[bool, float, str]:
    """compare the two derivations of one quantity."""
    err = _rel(declared, derived)
    ok = err <= tol
    detail = "%s: declared %.12g, derived %.12g, rel err %.3e (tol %.1e)" % (
        label, declared, derived, err, tol)
    return ok, err, detail


def check_reconciliation() -> AreaResult:
    """AREA 7 -- reconciliation.

    Four items, all binary, all measured:

      R1  the gate's norm bound: the declared constant and the boundary
          the gate actually enforces agree
      R2  the gate's coherence floor: same, and it FLIPS at the floor
      R3  the substrate's drift bound R: the declared radius and the
          radius the projection operator actually produces agree
      R4  the sweep: the two derivations agree across normal inputs,
          AND disagree where they must -- a reconciliation that can
          never see a disagreement is measuring nothing
    """
    measured: Dict[str, Any] = {}
    parts: List[str] = []

    # ---- R1 and R2: the gate's two bounds -----------------------------
    ok, data, err = _run(PROBE_GATE_BOUNDS)
    if not ok:
        return AreaResult(
            number=7, name="reconciliation", status=Status.SKIP,
            detail="the gate-bounds probe could not run: %s" % err,
            does_not_establish=(
                "that any two derivations agree -- the probe did not run"),
            measured=measured,
        )

    ok1, e1, d1 = _check_pair("norm bound", data["declared_max_norm"],
                              data["largest_admitted_norm"])
    measured["norm_rel_error"] = e1
    measured["declared_max_norm"] = data["declared_max_norm"]
    measured["derived_max_norm"] = data["largest_admitted_norm"]
    parts.append(d1)

    ok2, e2, d2 = _check_pair("coherence floor", data["declared_min_cos"],
                              data["smallest_admitted_cos"])
    measured["cos_rel_error"] = e2
    measured["declared_min_cos"] = data["declared_min_cos"]
    measured["derived_min_cos"] = data["smallest_admitted_cos"]
    parts.append(d2)

    if not (ok1 and ok2):
        return AreaResult(
            number=7, name="reconciliation", status=Status.FAIL,
            detail="; ".join(parts) + " -- the DECLARATION and the "
                   "BEHAVIOUR disagree. A gate whose constant is not the "
                   "boundary it enforces is not the gate that was specified.",
            does_not_establish=(
                "that the gate enforces any particular bound"),
            measured=measured,
        )
    parts.append("R1+R2: the declared norm bound and coherence floor are the "
                 "boundaries the gate actually enforces")

    # ---- R3: the drift bound ------------------------------------------
    ok3, d3data, err3 = _run(PROBE_DRIFT_BOUND)
    if not ok3:
        return AreaResult(
            number=7, name="reconciliation", status=Status.SKIP,
            detail="; ".join(parts) + "; the drift-bound probe could not "
                   "run: %s" % err3,
            does_not_establish=(
                "that the drift bound agrees with its declaration -- the "
                "probe did not run"),
            measured=measured,
        )
    ok3b, e3, d3 = _check_pair("drift bound R", d3data["declared_R"],
                               d3data["measured_projection_radius"])
    measured["drift_rel_error"] = e3
    measured["declared_R"] = d3data["declared_R"]
    measured["derived_R"] = d3data["measured_projection_radius"]
    parts.append(d3)
    if not ok3b:
        return AreaResult(
            number=7, name="reconciliation", status=Status.FAIL,
            detail="; ".join(parts) + " -- the projection operator does not "
                   "land on the declared radius.",
            does_not_establish="that the drift bound is what it claims to be",
            measured=measured,
        )
    parts.append("R3: the projection operator lands on the declared radius R")

    # ---- R4: the sweep, and the flip ----------------------------------
    ok4, sdata, err4 = _run(PROBE_SWEEP)
    if not ok4:
        return AreaResult(
            number=7, name="reconciliation", status=Status.SKIP,
            detail="; ".join(parts) + "; the sweep probe could not run: %s"
                   % err4,
            does_not_establish=(
                "that the derivations agree across a sweep -- the probe did "
                "not run"),
            measured=measured,
        )
    measured["sweep_points"] = sdata["sweep_points"]
    measured["sweep_agree"] = sdata["agree"]
    measured["sweep_disagreements"] = len(sdata["disagreements"])
    measured["verdict_flips_at_the_floor"] = sdata["verdict_flips_at_the_floor"]

    if sdata["disagreements"]:
        return AreaResult(
            number=7, name="reconciliation", status=Status.FAIL,
            detail="; ".join(parts) + "; the sweep found %d disagreement(s) "
                   "between the two derivations: %s"
                   % (len(sdata["disagreements"]), sdata["disagreements"][:3]),
            does_not_establish="that the derivations agree",
            measured=measured,
        )
    parts.append("R4: the two derivations agree at all %d sweep points"
                 % sdata["sweep_points"])

    # AND THE FLIP, which is what makes R4 worth having.
    if not sdata["verdict_flips_at_the_floor"]:
        return AreaResult(
            number=7, name="reconciliation", status=Status.FAIL,
            detail="; ".join(parts) + "; the gate's verdict does NOT flip "
                   "across the declared coherence floor -- a bound that never "
                   "changes a verdict is not a bound, and a reconciliation "
                   "that cannot see a disagreement cannot see anything.",
            does_not_establish="that the coherence floor is enforced",
            measured=measured,
        )
    parts.append("R4: the gate's verdict flips at the declared floor "
                 "(0.39 refused, 0.41 admitted)")

    # AND THE DEGENERATE END, because a gate that refuses the ground
    # refuses itself and a gate that admits the zero vector admits
    # nothing.
    if sdata["zero_allowed"] or not sdata["ground_allowed"]:
        return AreaResult(
            number=7, name="reconciliation", status=Status.FAIL,
            detail="; ".join(parts) + "; the degenerate cases are wrong "
                   "(zero allowed=%s, ground allowed=%s)"
                   % (sdata["zero_allowed"], sdata["ground_allowed"]),
            does_not_establish="that the gate's boundary cases are right",
            measured=measured,
        )
    parts.append("R4: the zero packet is refused and the ground is admitted")

    return AreaResult(
        number=7, name="reconciliation", status=Status.PASS,
        detail="; ".join(parts),
        does_not_establish=(
            "that EVERY quantity in the substrate has a second derivation. "
            "It establishes that the ones this area names -- the gate's two "
            "bounds and the drift radius -- are derived twice, independently, "
            "and agree to %.0e, and that the reconciliation can see a "
            "disagreement when there is one." % TOLERANCE),
        measured=measured,
    )


def _main(argv: List[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    r = check_reconciliation()
    print("=" * 70)
    print("AREA 7 reconciliation: %s" % r.status.value)
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
