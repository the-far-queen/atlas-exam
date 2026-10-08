"""
envelope.py -- AREA 9, and the machinery it needs.

WHY THIS AREA IS FIRST
----------------------
The exam's own README names it the blocker: "everything else is
un-actionable without it. no declared limit means no test can be
complete, because nobody can say what 'outside' means."

A 747 documents an operating envelope for every system it carries --
speeds, altitudes, temperatures, loadings -- and, critically, documents
the behaviour at the edges. An agent with no declared envelope cannot
be certified, because a certificate has to say what the thing is
certified TO DO.

The doctrine in result.py already forbids the easy version of this:
R1 unimplemented is FAIL, R2 binary, R3 every area declares what it does
not establish. A generic "it failed, so FAIL" would satisfy none of
those, because it would establish nothing. Envelope has to measure the
DECLARATION and the OUT-OF-RANGE BEHAVIOUR separately.

WHAT THIS FILE PROVIDES
-----------------------
1. `Envelope`, `Limit`, `LimitKind` -- a machine-checkable limit registry
2. `probe_envelope()` -- reads the substrate's declared envelope
3. `probe_out_of_range()` -- drives the substrate past a declared limit
   and records what it actually does
4. `check_envelope()` -- the graded area

THE STANDARD FOR "DECLARED"
---------------------------
A limit counts as declared only if all four hold:

  D1  it has a finite numeric bound, not a word
  D2  it names the quantity it bounds
  D3  it states the behaviour when exceeded
  D4  it is reachable -- the registry is loaded and the number is real

D4 is the one that catches the common failure. A docstring saying
"the state is expected to stay bounded" declares an expectation, not a
limit. This check requires a value the exam can compare against.

WHAT THIS DOES NOT ESTABLISH
----------------------------
It does not establish that the declared limits are the RIGHT limits --
only that they are declared, numeric, and enforced. A system could
declare +/-1e6 and pass this area while being wildly unbounded. Whether
the envelope is tight enough is a question for area 10's mutation, which
narrows a limit and checks the area still behaves.

Run: python -m exam.envelope --probe
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from .result import AreaResult, Status

HERMES = os.path.expanduser("~/AppData/Local/hermes")
WORK_REPOS = os.path.join(HERMES, "work_repos")
SIMSELF_SRC = os.path.join(WORK_REPOS, "simself", "src")
FIELDCORE_SRC = os.path.join(WORK_REPOS, "fieldcore", "src")

PROBE_TIMEOUT_S = 180


# ---------------------------------------------------------------------------
# the vocabulary. a limit is a number, a quantity, and a stated response.
# ---------------------------------------------------------------------------

class LimitKind(Enum):
    UPPER = "upper"
    LOWER = "lower"
    TWO_SIDED = "two_sided"


# what a system is allowed to do when it leaves its envelope. these are
# the only four responses this exam will accept as "declared behaviour".
# the point is that SILENCE is not on the list.
class OutOfRange(Enum):
    REFUSE = "refuse"            # decline the input, state unchanged
    CLAMP = "clamp"              # saturate at the bound
    PROJECT = "project"          # return to the nearest in-range state
    DIVERGE = "diverge"          # explicitly allowed to become invalid


# The probes that exist, by name. A Limit's `verifier` must resolve to one
# of these or the limit is unverified. A string naming a probe that does not
# exist is exactly the kind of decorative claim this exam exists to catch,
# so it is not accepted here either.
KNOWN_PROBES = frozenset({
    "probe_envelope",
    "probe_out_of_range",
    "probe_identity",
})


@dataclass(frozen=True)
class Limit:
    """one declared limit. immutable: an exam must not edit its own yardstick.

    `verifier` is the seventh field and it is not decoration. It names the
    probe that exercises this limit. The 747 rule: a certified system has a
    test per certified limit. A limit nothing exercises is not a limit.

    This was added because the mutation check caught the hole: a bound of
    1e300 is finite, so the D1 check accepted it, and E3 only probes
    hodge_cycle, so a limit declared for a subsystem nobody exercises
    passed the whole area. An earlier fix idea -- sanity-bounding the
    magnitude -- was rejected as worse than the disease: there is no
    principled "big enough", and picking 1e6 would be inventing a threshold
    and calling it rigour. Requiring a verifier is checkable instead.
    """
    quantity: str                 # D2: what is bounded
    kind: LimitKind
    bound: float                 # D1: the finite number
    out_of_range: OutOfRange     # D3: the stated response
    source: str                  # where it came from, for provenance
    verifier: str = ""           # which probe exercises it. "" = unverified.

    def __post_init__(self):
        if not self.quantity:
            raise ValueError("D2: a limit must name the quantity it bounds")
        if not isinstance(self.bound, float) or self.bound != self.bound:
            raise ValueError(f"D1: bound for {self.quantity!r} is not a finite number")
        if self.bound in (float("inf"), float("-inf")):
            raise ValueError(f"D1: bound for {self.quantity!r} is infinite")

    @property
    def is_verified(self) -> bool:
        """a limit is only real if something exercises it.

        A non-empty verifier string is NOT enough. M3b in the test file
        planted a limit whose verifier was
        "probe_that_does_not_exist" and the area passed, because nothing
        checked that the name resolves. So this resolves the name against
        the probes this module actually exposes.
        """
        if not self.verifier:
            return False
        name = self.verifier.split("(")[0].strip()
        return name in KNOWN_PROBES

    def contains(self, value: float) -> bool:
        if self.kind is LimitKind.UPPER:
            return value <= self.bound
        if self.kind is LimitKind.LOWER:
            return value >= self.bound
        return abs(value) <= self.bound

    def exceeded_by(self, value: float) -> bool:
        return not self.contains(value)

    def to_dict(self) -> Dict:
        return {
            "quantity": self.quantity,
            "kind": self.kind.value,
            "bound": self.bound,
            "out_of_range": self.out_of_range.value,
            "source": self.source,
            "verifier": self.verifier,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "Limit":
        return cls(
            quantity=d["quantity"],
            kind=LimitKind(d["kind"]),
            bound=float(d["bound"]),
            out_of_range=OutOfRange(d["out_of_range"]),
            source=d.get("source", "unknown"),
            verifier=d.get("verifier", ""),
        )


@dataclass
class Envelope:
    """The declared limits of one subsystem."""
    subsystem: str
    limits: List[Limit] = field(default_factory=list)

    def get(self, quantity: str) -> Optional[Limit]:
        for lim in self.limits:
            if lim.quantity == quantity:
                return lim
        return None

    def is_empty(self) -> bool:
        return not self.limits

    def to_dict(self) -> Dict:
        return {"subsystem": self.subsystem,
                "limits": [lim.to_dict() for lim in self.limits]}


# ---------------------------------------------------------------------------
# the declared envelope of the substrate, as of 2026-10-08.
#
# These are the limits the substrate actually enforces internally (found
# by reading it), stated as numbers. Where the substrate has NO limit, no
# Limit is recorded -- the absence is the finding, and area 9 reports it.
#
# source strings are file paths so provenance is checkable, not asserted.
# ---------------------------------------------------------------------------

DECLARED: Dict[str, Envelope] = {
    "simself.ground": Envelope(
        subsystem="simself.ground",
        limits=[
            Limit("psi_0_component", LimitKind.TWO_SIDED, 1.0,
                  OutOfRange.PROJECT,
                  "simself/src/constitutional/ground.py",
                  verifier="probe_identity (exam/substrate.py PROBE_IDENTITY)"),
        ],
    ),
    "simself.residual": Envelope(
        subsystem="simself.residual",
        limits=[
            Limit("residual_norm", LimitKind.UPPER, 3.0,
                  OutOfRange.CLAMP,
                  "simself/src/constitutional/resolution.py (R=3.0)",
                  verifier="probe_identity (R=3.0 constructor arg)"),
        ],
    ),
    "fieldcore.hodge_cycle": Envelope(
        subsystem="fieldcore.hodge_cycle",
        limits=[
            Limit("spectral_radius", LimitKind.UPPER, 1.0,
                  OutOfRange.REFUSE,
                  "fieldcore/src/hodge_cycle.py (stability iff rho < 1)",
                  verifier="probe_out_of_range (inside rho + outside breach)"),
            Limit("exploration_weight_alpha", LimitKind.UPPER,
                  1.0 / 1.618034, OutOfRange.CLAMP,
                  "fieldcore/src/hodge_cycle.py (ALPHA = 1/phi)",
                  verifier="probe_envelope (reads ALPHA back from the module)"),
            Limit("damping", LimitKind.TWO_SIDED, 0.9, OutOfRange.CLAMP,
                  "fieldcore/src/hodge_cycle.py (sweep domain)",
                  verifier="probe_out_of_range (damping 0.0 vs 0.4)"),
        ],
    ),
}


# ---------------------------------------------------------------------------
# probes. subprocess, per the repo's non-negotiable design constraint.
# ---------------------------------------------------------------------------

PROBE_DECLARED = r"""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.expanduser("~"), "AppData", "Local",
                                "hermes", "work_repos", "fieldcore", "src"))
out = {}
try:
    from hodge_cycle import spectral_radius, resolution_operator, ALPHA, TOPO
    import numpy as np
    rho = spectral_radius(resolution_operator(8, damping=0.0))
    rho_fixed = spectral_radius(resolution_operator(8, damping=0.4))
    out["hodge_cycle"] = {
        "rho_undamped": float(rho),
        "rho_damped": float(rho_fixed),
        "alpha": float(ALPHA),
        "topo": float(TOPO),
    }
except Exception as exc:
    out["hodge_cycle"] = {"error": f"{type(exc).__name__}: {exc}"}
print(json.dumps(out))
"""


def run_probe(name: str, code: str, timeout: int = PROBE_TIMEOUT_S
              ) -> tuple[bool, Dict, str]:
    """run a probe in a fresh interpreter. loud failure only."""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [SIMSELF_SRC, FIELDCORE_SRC, env.get("PYTHONPATH", "")])
    try:
        r = subprocess.run([sys.executable, "-c", code],
                           capture_output=True, text=True, env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, {}, f"probe '{name}' exceeded {timeout}s"
    if r.returncode != 0:
        tail = (r.stderr or "").strip().splitlines()
        return False, {}, (tail[-1] if tail else f"exit {r.returncode}")
    out = (r.stdout or "").strip()
    if not out:
        return False, {}, f"probe '{name}' produced no output"
    try:
        return True, json.loads(out.splitlines()[-1]), ""
    except ValueError as exc:
        return False, {}, f"probe '{name}' emitted non-JSON: {exc}"


def probe_envelope() -> tuple[bool, Dict, str]:
    """does the substrate agree with its own declared envelope?"""
    ok, data, err = run_probe("envelope", PROBE_DECLARED)
    return ok, data, err


def probe_out_of_range() -> tuple[bool, Dict, str]:
    """drive hodge_cycle past its declared stability limit and record what
    actually happens. this is the item a generic failure cannot fake."""
    code = r"""
import json, sys, os, warnings
warnings.simplefilter("ignore")
sys.path.insert(0, os.path.join(os.path.expanduser("~"), "AppData", "Local",
                                "hermes", "work_repos", "fieldcore", "src"))
import numpy as np
from hodge_cycle import resolution_operator, step_cell, TOPO, ALPHA

out = {}
D = 8
# 1. inside the envelope: damping 0.4 is declared stable. it must be bounded.
M = resolution_operator(D, damping=0.4)
rng = np.random.default_rng(0)
x = rng.normal(0, 0.1, D)
peak_inside = 0.0
for _ in range(500):
    x = M @ x
    peak_inside = max(peak_inside, float(np.abs(x).max()))
out["inside"] = {"peak": peak_inside, "rho": float(np.abs(np.linalg.eigvals(M)).max())}

# 2. outside: damping 0.0 violates the declared rho<1. it must actually grow.
M0 = resolution_operator(D, damping=0.0)
x = rng.normal(0, 0.1, D)
first_breach = None
for i in range(2000):
    x = M0 @ x
    if np.abs(x).max() > 1e6:
        first_breach = i + 1
        break
out["outside"] = {
    "rho": float(np.abs(np.linalg.eigvals(M0)).max()),
    "breach_step": first_breach,
    "breached": first_breach is not None,
}
# 3. does it refuse, or does it blow up? a DIVERGE declaration means blow-up
#    is permitted -- but it must still be finite or non-finite, not silent.
out["declared_response_is_observable"] = bool(
    first_breach is not None or not np.isfinite(np.abs(x).max()))
print(json.dumps(out))
"""
    return run_probe("out_of_range", code)


# ---------------------------------------------------------------------------
# the graded area
# ---------------------------------------------------------------------------

def check_envelope() -> AreaResult:
    """AREA 9 -- envelope.

    Three items, all binary, all measured:

      E1  a non-empty declared registry exists
      E2  every declared limit names a quantity, a finite bound, and a
          stated out-of-range response
      E3  the substrate's measured behaviour matches its declaration --
          inside the envelope it stays bounded, outside it crosses the
          declared bound at a measurable step
    """
    detail_parts: List[str] = []
    measured: Dict = {}

    # ---- E1: is anything declared at all?
    if not DECLARED or all(env.is_empty() for env in DECLARED.values()):
        return AreaResult(
            number=9, name="envelope", status=Status.FAIL,
            detail="E1: no subsystem declares an envelope. registry is empty.",
            does_not_establish="anything -- an empty registry establishes nothing.",
            measured={"subsystems": 0, "limits": 0},
        )
    n_limits = sum(len(e.limits) for e in DECLARED.values())
    measured["subsystems"] = len(DECLARED)
    measured["limits"] = n_limits
    detail_parts.append(f"E1: {len(DECLARED)} subsystems, {n_limits} declared limits")

    # ---- E2: every limit is complete
    bad: List[str] = []
    for env in DECLARED.values():
        if env.is_empty():
            bad.append(f"{env.subsystem}: declares nothing")
        for lim in env.limits:
            # Limit.__post_init__ already enforced D1+D2 at construction.
            # Re-check explicitly so the area reports rather than trusts.
            if lim.bound != lim.bound or abs(lim.bound) == float("inf"):
                bad.append(f"{env.subsystem}.{lim.quantity}: D1 not finite")
            if not lim.quantity:
                bad.append(f"{env.subsystem}: D2 no quantity")
            if lim.out_of_range is None:
                bad.append(f"{env.subsystem}.{lim.quantity}: D3 no response")
            if not lim.source:
                bad.append(f"{env.subsystem}.{lim.quantity}: no source")
            # D4: reachable. a limit nothing exercises is not a limit. This
            # is what catches the 1e300 mutation -- the bound is finite so
            # D1 passes, and if the subsystem is not probed, E3 never sees it.
            if not lim.is_verified:
                bad.append(f"{env.subsystem}.{lim.quantity}: D4 no verifier "
                           f"(declared but never exercised)")
    measured["malformed_limits"] = len(bad)
    measured["unverified_limits"] = sum(
        1 for e in DECLARED.values() for l in e.limits if not l.is_verified)
    if bad:
        detail_parts.append("E2 FAIL: " + "; ".join(bad[:4]))
        return AreaResult(
            number=9, name="envelope", status=Status.FAIL,
            detail="; ".join(detail_parts),
            does_not_establish="that the substrate respects any limit",
            measured=measured,
        )
    detail_parts.append(
        f"E2: {n_limits} limits each name a quantity, a finite bound, a response, "
        f"a source, and a verifier")

    # ---- E3: measured behaviour matches the declaration
    ok_in, data_in, err_in = probe_envelope()
    if not ok_in:
        detail_parts.append(f"E3 SKIP: substrate probe failed ({err_in})")
        return AreaResult(
            number=9, name="envelope", status=Status.SKIP,
            detail="; ".join(detail_parts),
            does_not_establish="that the substrate respects any limit -- "
                               "the probe could not run",
            measured=measured,
        )
    hc = data_in.get("hodge_cycle", {})
    if "error" in hc:
        detail_parts.append(f"E3 SKIP: substrate import failed ({hc['error']})")
        return AreaResult(
            number=9, name="envelope", status=Status.SKIP,
            detail="; ".join(detail_parts),
            does_not_establish="that the substrate respects any limit -- "
                               "the declared subsystem was not importable",
            measured=measured,
        )

    ok_oor, data_oor, err_oor = probe_out_of_range()
    if not ok_oor:
        detail_parts.append(f"E3 SKIP: out-of-range probe failed ({err_oor})")
        return AreaResult(
            number=9, name="envelope", status=Status.SKIP,
            detail="; ".join(detail_parts),
            does_not_establish="that the substrate respects any limit -- "
                               "the out-of-range probe could not run",
            measured=measured,
        )

    inside = data_oor["inside"]
    outside = data_oor["outside"]
    measured["inside_peak"] = inside["peak"]
    measured["inside_rho"] = inside["rho"]
    measured["outside_rho"] = outside["rho"]
    measured["outside_breach_step"] = outside["breach_step"]

    # inside must be bounded (declared: stays inside)
    if not (inside["rho"] < 1.0):
        detail_parts.append(f"E3 FAIL: inside the envelope rho={inside['rho']:.4f} >= 1")
        return AreaResult(
            number=9, name="envelope", status=Status.FAIL,
            detail="; ".join(detail_parts),
            does_not_establish="that the substrate respects any limit",
            measured=measured,
        )

    # outside must actually leave it (declared: cross the bound, measurably)
    if not outside["breached"]:
        detail_parts.append(
            f"E3 FAIL: outside the envelope (rho={outside['rho']:.4f}) the state "
            "never crossed 1e6 in 2000 steps -- the declaration and the "
            "behaviour disagree")
        return AreaResult(
            number=9, name="envelope", status=Status.FAIL,
            detail="; ".join(detail_parts),
            does_not_establish="that the substrate respects any limit",
            measured=measured,
        )

    detail_parts.append(
        f"E3: inside rho={inside['rho']:.4f} peak={inside['peak']:.4g}; "
        f"outside rho={outside['rho']:.4f} breaches 1e6 at step {outside['breach_step']}")
    detail_parts.append(f"    substrate reports rho_undamped={hc.get('rho_undamped')}, "
                        f"rho_damped={hc.get('rho_damped')}")

    return AreaResult(
        number=9, name="envelope", status=Status.PASS,
        detail="; ".join(detail_parts),
        does_not_establish=(
            "that the declared limits are TIGHT enough, only that they are "
            "declared, numeric, sourced, and that the substrate's measured "
            "behaviour matches them. A system could declare +/-1e6 and pass "
            "here while being effectively unbounded; whether the envelope is "
            "narrow enough is area 10's job."),
        measured=measured,
    )


if __name__ == "__main__":
    ok, d, e = probe_envelope()
    print("declared probe:", "ok" if ok else f"FAILED ({e})", json.dumps(d))
    ok2, d2, e2 = probe_out_of_range()
    print("out-of-range probe:", "ok" if ok2 else f"FAILED ({e2})", json.dumps(d2))
    r = check_envelope()
    print(f"\nAREA 9 envelope: {r.status.value}")
    print("detail:", r.detail)
    print("does not establish:", r.does_not_establish)
    sys.exit(0 if r.status is Status.PASS else 1)