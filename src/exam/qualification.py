"""
qualification.py — the gate that decides what SimSelf is allowed to keep.

THE FRAMING CORRECTION (Bobby, 2026-10-09)
------------------------------------------------
The atlas exam is **not external**. It is not an outside auditor and not
a third party's opinion. **It is the qualification gate inside the
learning loop** — the step between "SimSelf proposed it" and "the system
is now different."

    SimSelf PROPOSES
        -> M1 (Controller) audits          [outside core]
            -> ATLAS EXAM qualifies         <-- THIS MODULE
                -> M0 (Governor) commits or vetoes   [in core, 1-bit]

Nothing reaches the Sacred Library without passing here. That is not a
policy; it is the shape of the call graph, and this module is the middle
of it.

WHAT IT GUARDS AGAINST
----------------------
Eleven measured failures across six frontier-model transcripts. Every one
has the same shape: **a mechanism that is locally correct and has no
memory of its own history.** A Hodge harmonic with spectral radius 7.0. A
sacred axis moved 0.09 by one thousand legal nudges. A resistance term
that shrank every attack below the threshold meant to catch it. A stress
test whose refusal rate was reported for a run that crashed on line 1.

This module is the thing that would have caught all eleven.

THE 95% BOUND, and why it is not 100%
---------------------------------------
Bobby: *"sacred library ensures low falsity continuously not set to perfect
choose 95% so compute is bounded."*

**A gate that must be perfect is a gate that never opens.** 100% fidelity
means one surviving defect blocks all learning forever; the system is safe
and inert. 0% means everything passes and the gate is theatre. 95% is the
working point: bounded compute, bounded contamination, bounded damage, and
the system still evolves.

Three consequences, all deliberate:

1. **Bounded compute.** A proposal is accepted when it clears the bound,
   not when it clears perfection, so a cycle's cost is predictable.
2. **Bounded contamination.** The Library keeps a falsity ledger. A gate
   admitting false material is a *measured rate*, not an unknown, and a
   measured rate can be budgeted for.
3. **Bounded damage.** Because every admitted entry is traceable to the
   check that admitted it, a later discovery of falsity identifies exactly
   which entries to demote.

**95% is a policy constant, not a constant of nature.** It is declared
here, named, and changeable in one place. A threshold nobody can see is a
threshold nobody can argue with.

WHAT IT DOES NOT ESTABLISH
--------------------------
It does not establish that anything admitted is TRUE. It establishes that
something was checked and the check's result is on the record. A badly
designed check passes anything; this module forces the check to EXIST, and
`atlas-exam`'s area 10 exists to catch the case where the check is theatre.

Nor does it stop a caller that ignores its return value. Every gate is
advisory to a process that chooses not to obey it. That is why M0 is
deterministic Python rather than a model: the last word should not be
exercised by something that can be talked into changing it.

Run: python src/qualification.py --selftest
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Sequence


# ---------------------------------------------------------------------------
# the bound. one constant, one place.
# ---------------------------------------------------------------------------

#: target admission rate. See the module docstring for why this is 95 and
#: not 100: a gate that must be perfect is a gate that never opens.
ADMISSION_TARGET = 0.95

#: refuse below this. below 80% the gate is not doing its job and the
#: correct response is to fix the checks, not to lower the floor.
ADMISSION_FLOOR = 0.80

#: refuse above this. above 99% the checks have stopped discriminating --
#: the same signature as a metric that always agrees.
ADMISSION_CEILING = 0.99


class Disposition(str, Enum):
    ADMIT = "admit"
    REJECT = "reject"
    DEFER = "defer"          # not decided; costs compute, changes nothing


# ---------------------------------------------------------------------------
# the proposal
# ---------------------------------------------------------------------------

@dataclass
class Proposal:
    """One candidate change to the substrate or the Library."""
    text: str
    source: str = "simself"          # who proposed it
    module: str = ""
    check: Optional[Callable[[], bool]] = None   # what would refute it
    provenance: str = ""


@dataclass
class Admission:
    """The record. A Library is a record, not a state."""
    proposal: Proposal
    disposition: Disposition
    reason: str
    falsity_cost: float = 0.0        # 1/admission_rate, the budget this consumed

    def to_dict(self) -> Dict:
        return {"text": self.proposal.text, "source": self.proposal.source,
                "module": self.proposal.module,
                "disposition": self.disposition.value, "reason": self.reason,
                "falsity_cost": round(self.falsity_cost, 4)}


@dataclass
class FalsityLedger:
    """Running admission rate and what it cost.

    The ledger is the reason a 95% target is safe rather than complacent.
    Contamination is not prevented; it is MEASURED, and every admitted
    entry carries the check that admitted it so a later discovery of
    falsity identifies exactly what to demote.
    """
    admissions: List[Admission] = field(default_factory=list)
    rejected: List[Admission] = field(default_factory=list)
    deferred: List[Admission] = field(default_factory=list)

    @property
    def rate(self) -> float:
        decided = len(self.admissions) + len(self.rejected)
        return (len(self.admissions) / decided) if decided else 1.0

    def audit(self) -> Dict:
        decided = len(self.admissions) + len(self.rejected)
        return {
            "admitted": len(self.admissions),
            "rejected": len(self.rejected),
            "deferred": len(self.deferred),
            "decided": decided,
            "admission_rate": round(self.rate, 4),
            "target": ADMISSION_TARGET,
            "at_target": abs(self.rate - ADMISSION_TARGET) <= 0.01,
            "below_floor": bool(decided and self.rate < ADMISSION_FLOOR),
            "above_ceiling": bool(decided and self.rate > ADMISSION_CEILING),
        }

    def admitted_texts(self) -> List[str]:
        return [a.proposal.text for a in self.admissions]


# ---------------------------------------------------------------------------
# the gate
# ---------------------------------------------------------------------------

class QualificationGate:
    """The middle step: propose -> audit -> QUALIFY -> commit.

    Sits between M1 and M0 by design. M1 is outside the core and can
    be wrong; M0 is inside and deterministic. The gate is neither, and
    that is the point: the check that guards the constitutional ground
    must not itself be inside the thing it guards.
    """

    def __init__(self, target: float = ADMISSION_TARGET,
                 floor: float = ADMISSION_FLOOR,
                 ceiling: float = ADMISSION_CEILING):
        if not 0.0 < target < 1.0:
            raise ValueError(f"target must be in (0,1), got {target}")
        if not 0.0 <= floor <= target <= ceiling <= 1.0:
            raise ValueError(
                f"require 0 <= floor({floor}) <= target({target}) "
                f"<= ceiling({ceiling}) <= 1")
        self.target = target
        self.floor = floor
        self.ceiling = ceiling
        self.ledger = FalsityLedger()
        self.history: List[Dict] = []

    def qualify(self, p: Proposal) -> Admission:
        """One proposal, one decision, on the record.

        R1 — UNTESTED IS NOT ADMITTED. A proposal with no check is
        DEFERRED, never accepted, because "no reason to refuse" is not
        "a reason to accept". The difference is the whole doctrine.
        """
        if p.check is None:
            a = Admission(p, Disposition.DEFER,
                          "no falsifier supplied; untested is not admitted")
            self.ledger.deferred.append(a)
            return a

        try:
            holds = bool(p.check())
        except Exception as exc:
            # a check that crashes has not refuted; it has failed to test.
            a = Admission(p, Disposition.DEFER,
                          f"falsifier raised {type(exc).__name__}; "
                          "a crash is not a refutation")
            self.ledger.deferred.append(a)
            return a

        rate = self.ledger.rate
        if holds:
            cost = (1.0 / rate) if rate > 0 else float("inf")
            a = Admission(p, Disposition.ADMIT, "check ran and held", cost)
            self.ledger.admissions.append(a)
        else:
            a = Admission(p, Disposition.REJECT, "check ran and the claim did not hold")
            self.ledger.rejected.append(a)

        self.history.append(self.ledger.audit())
        return a

    def qualify_many(self, proposals: Sequence[Proposal]) -> List[Admission]:
        return [self.qualify(p) for p in proposals]

    def health(self) -> Dict:
        """Is the gate discriminating, or has it become theatre?

        Below floor: the checks are too strict or the substrate is broken.
        Above ceiling: the checks no longer distinguish, which is the
        signature of a metric that always agrees.
        """
        a = self.ledger.audit()
        verdict, note = "HEALTHY", "admission rate at target"
        if a["decided"] and a["admission_rate"] < self.floor:
            verdict = "REJECT_TOO_MUCH"
            note = "below floor; fix the checks before lowering the floor"
        elif a["decided"] and a["admission_rate"] > self.ceiling:
            verdict = "ACCEPTING_TOO_MUCH"
            note = ("above ceiling; a gate that admits almost everything "
                    "has stopped discriminating")
        return {**a, "verdict": verdict, "note": note}


# ---------------------------------------------------------------------------
# the eleven, as a demonstration
# ---------------------------------------------------------------------------

class TemporalController:
    """A faithful stand-in for the real class's DEFINED surface only.

    deepseek4 L4772-4779 assigns `self.policy` to `_heuristic_policy`,
    `_rl_policy` or `_supervised_policy`. The method it actually defines is
    `_heuristic_decision`. So all three attributes are missing and
    construction raises for every mode. Reproduced here so the gate's
    eleventh check is the real defect rather than a stub.
    """
    def _heuristic_decision(self):      # the one method that IS defined
        return "heuristic"


def corpus_eleven() -> List[Proposal]:
    """The eleven measured corpus failures, as proposals the gate REFUTES.

    This is the mutation corpus: every claim below is false, every
    check runs, and every one is rejected. If any were admitted, the gate
    is not discriminating.
    """
    P = Proposal

    return [
        P("Hodge harm is bounded",
          check=lambda: abs(4 - 2 * complex(-1, 0) - 1 / complex(-1, 0)) < 1.0,
          source="deepseek1"),
        P("sacred axes cannot be moved by repetition",
          check=lambda: abs(1000 * 0.0009 * 0.1) < 1e-9, source="deepseek4"),
        P("resistance prevents large changes being accepted",
          check=lambda: not (0.0250 < 0.1), source="deepseek3"),
        P("MMM scores coherent interpretations above random",
          check=lambda: 0.08 > 0.60, source="deepseek3"),
        P("MMM scores a liar below a true statement",
          check=lambda: 1.0 < 1.0, source="deepseek3"),
        P("the claimed CRC32 digests verify",
          check=lambda: "d4e9f2a1" == "fc7416b6", source="deepseek2"),
        P("MVCC gives truth a non-zero evidence multiplier",
          check=lambda: (1.0 - abs(1.0)) > 0.0, source="deepseek2"),
        P("the probability weights support their output",
          check=lambda: sum([5, 10, 15, 0, 10, -25, -20]) > 0, source="deepseek5"),
        P("the stress test executes",
          check=lambda: hasattr(object(), "__getitem__"), source="deepseek4"),
        P("the velocity multipliers compose to 4.5x",
          check=lambda: abs(3 * 4 * 7 - 4.5) < 1e-9, source="deepseek6"),
        P("TemporalController can be instantiated",
          # reproduces deepseek4's actual defect: the three policy methods
          # the constructor assigns are never defined, so construction
          # raises for EVERY mode including the else branch.
          check=lambda: all(hasattr(TemporalController, m) for m in
                            ("_heuristic_policy", "_rl_policy",
                             "_supervised_policy")),
          source="deepseek4"),
    ]


def selftest() -> None:
    print("=" * 70)
    print("1. THE GATE IS INSIDE THE LOOP, NOT OUTSIDE IT")
    print("=" * 70)
    print("    SimSelf PROPOSES -> M1 audits -> ATLAS EXAM -> M0 commits")
    print("  the gate is the middle step. nothing reaches the Library")
    print("  without passing here, and it is deliberately not inside M0 --")
    print("  the check that guards the ground must not be guarded by it.")
    g = QualificationGate()
    print(f"  target {g.target}  floor {g.floor}  ceiling {g.ceiling}")

    print()
    print("=" * 70)
    print("2. THE ELEVEN corpus failures, run through the gate")
    print("=" * 70)
    g2 = QualificationGate()
    for p in corpus_eleven():
        a = g2.qualify(p)
        mark = "REJECT" if a.disposition is Disposition.REJECT else "!! " + a.disposition.value
        print(f"  {mark:7s} {p.text[:52]:54s} {p.source}")
    h = g2.health()
    print()
    print(f"  {h['admitted']} admitted, {h['rejected']} rejected, "
          f"{h['deferred']} deferred  rate {h['admission_rate']}")
    assert h["admitted"] == 0, "a gate that admits a known-false claim is broken"

    print()
    print("=" * 70)
    print("3. UNTESTED IS NOT ADMITTED (R1)")
    print("=" * 70)
    g3 = QualificationGate()
    a = g3.qualify(Proposal("nobody ever checked this", check=None))
    print(f"  no falsifier -> {a.disposition.value}: {a.reason}")
    assert a.disposition is Disposition.DEFER

    print()
    print("=" * 70)
    print("4. A CRASHING CHECK IS NOT A REFUTATION")
    print("=" * 70)
    def boom():
        raise RuntimeError("substrate missing")
    g4 = QualificationGate()
    a = g4.qualify(Proposal("x", check=boom))
    print(f"  raising check -> {a.disposition.value}: {a.reason}")
    assert a.disposition is Disposition.DEFER, \
        "reporting a crash as rejection would be as dishonest as admitting it"

    print()
    print("=" * 70)
    print("5. 95%, NOT 100% -- and the ledger is why that is safe")
    print("=" * 70)
    g5 = QualificationGate()
    truthy = [Proposal(f"holds {i}", check=lambda i=i: True) for i in range(19)]
    falsy = [Proposal(f"fails {i}", check=lambda i=i: False) for i in range(1)]
    g5.qualify_many(truthy + falsy)
    h5 = g5.health()
    print(f"  19 true + 1 false -> rate {h5['admission_rate']}")
    print(f"  at target: {h5['at_target']}   verdict: {h5['verdict']}")
    print(f"  {h5['note']}")
    print()
    print("  19 of 20 admitted. A 100% gate would have refused all 20 and")
    print("  the system would be safe and inert forever. 95% bounds compute,")
    print("  bounds contamination, and bounds damage -- because every admitted")
    print("  entry carries the check that admitted it.")
    assert h5["admitted"] == 19

    print()
    print("=" * 70)
    print("6. the gate detects a gate that stopped discriminating")
    print("=" * 70)
    g6 = QualificationGate()
    g6.qualify_many([Proposal("x", check=lambda: True) for _ in range(20)])
    h6 = g6.health()
    print(f"  20/20 admitted -> rate {h6['admission_rate']}  verdict {h6['verdict']}")
    print(f"  {h6['note']}")
    assert h6["verdict"] == "ACCEPTING_TOO_MUCH", \
        "a gate that admits everything has stopped working"

    print()
    print("=" * 70)
    print("7. WHAT IT DOES NOT ESTABLISH")
    print("=" * 70)
    print("  admitted is not TRUE. it means a check ran and held.")
    print("  a badly designed check passes anything -- this forces the check")
    print("  to EXIST, it does not make it good. atlas-exam area 10 exists")
    print("  to catch the case where the check is theatre.")
    print()
    print("  and the gate is advisory to a process that chooses to ignore it.")
    print("  that is why M0 is deterministic python: the last word should")
    print("  not be exercised by something that can be talked into it.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.parse_args()
    selftest()