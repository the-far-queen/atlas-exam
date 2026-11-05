"""
areas.py -- THE REGISTRY. Every area, and what state it is really in.

WHY THIS FILE EXISTS
--------------------
`letter_q` in `fieldcore/src/fc_app.py` reports how many of the exam's
23 areas are implemented. It did that by SNIFFING THE SOURCE TEXT of
`exam/cli.py` for the string "todo(", which is a two-state answer to a
three-state question. The app's own doctrine -- stated in `fc_app.py`
itself -- is:

    LIVE   it was constructed and it ran, and it produced a measurement
    STUB   it is declared, its interface is fixed, it returns a named
           "not implemented" -- and that name is visible in the output
    DARK   it was attempted and it failed; the failure is reported with
           the reason, and the app does not pretend it is fine

An unimplemented area and a DECLARED STUB are different things, and the
survey must be able to tell them apart. A hole in the instrument that
grades the substrate is a hole; a declared stub is a declaration. Both
are honest, and the difference is the difference between a backlog and
a hole.

SO THE REGISTRY IS THE SOURCE OF TRUTH, and it is here rather than in
`fieldcore` because the exam must not depend on anything, and
`fieldcore` must not depend on the exam. The dependency points AT the
exam, never the other way. `fc_app.py` reads this file's states through
the same subprocess rule the exam itself uses.

THE THREE STATES, AND WHAT EACH ONE MEANS
------------------------------------------
    LIVE  the area has an implementation that PRODUCES A MEASUREMENT.
          It may PASS or FAIL. Both are the area working. An area that
          reports FAIL because the substrate has a hole is WORKING --
          that is the exam doing its job.

    STUB  the area is declared, its interface is fixed, it returns a
          named "not implemented" with a REASON, and the reason is
          visible in the survey output. Not a hole. A hole is a STUB
          with no reason attached.

    DARK  the area was attempted and it could not run. The failure is
          reported with the reason.

THE POINT OF THE REGISTRY, and it is the point of the whole exam
-------------------------------------------------------------------
An area that cannot fail is not an area. So the registry does not record
whether an area PASSES -- the run does that -- it records whether the
area EXISTS AS A MEASURING INSTRUMENT. Every entry here names the module
that implements it, and a state, and for STUB and DARK, the reason.

Run: python -m exam.areas
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class AreaState(str, Enum):
    """LIVE, STUB, DARK. The same three the app uses for its letters."""
    LIVE = "LIVE"
    STUB = "STUB"
    DARK = "DARK"


@dataclass(frozen=True)
class AreaDecl:
    """One area's declaration. Immutable: an exam must not edit its own
    yardstick in the same run that measures against it."""

    number: int
    name: str
    state: AreaState
    #: the module that implements it, relative to `src/exam/`.
    module: str = ""
    #: the reason, for STUB and DARK. REQUIRED for STUB.
    reason: str = ""
    #: what the area does not establish. Carried so the survey can
    #: print the limit next to the state.
    does_not_establish: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "area": self.number,
            "name": self.name,
            "state": self.state.value,
            "module": self.module,
            "reason": self.reason,
            "does_not_establish": self.does_not_establish,
        }


# ---------------------------------------------------------------------------
# THE REGISTRY
# ---------------------------------------------------------------------------
#
# Every one of the 23 areas, declared. The states here are ASSERTED BY
# TEST against the actual run: a registry that says LIVE while the
# implementation raises is a registry that lies, and `tests/test_areas.py`
# is the check that makes it tell the truth.

AREA_DECLS: List[AreaDecl] = [
    AreaDecl(0, "process_integrity", AreaState.LIVE, "exam/cli.py",
             does_not_establish=(
                 "that the process is correct. it can only establish that the "
                 "rules are WRITTEN and this area exists.")),
    AreaDecl(1, "refusal", AreaState.LIVE, "exam/substrate.py",
             does_not_establish=(
                 "that the thresholds are RIGHT. cos >= 0.4 and |x| <= 4 are "
                 "choices with no derivation behind them.")),
    AreaDecl(2, "identity", AreaState.LIVE, "exam/substrate.py",
             does_not_establish="that psi_0 is the RIGHT ground."),
    AreaDecl(3, "boundedness", AreaState.LIVE, "exam/substrate.py",
             does_not_establish="that R = 3 is the right bound."),
    AreaDecl(4, "liveness", AreaState.LIVE, "exam/substrate.py",
             does_not_establish=(
                 "that the motion is CORRECT, only that it exists.")),
    AreaDecl(5, "return", AreaState.LIVE, "exam/substrate.py",
             does_not_establish=(
                 "that 20 ticks is the right settling budget, or that the decay "
                 "law is the correct model of recovery.")),
    AreaDecl(6, "provenance", AreaState.LIVE, "exam/provenance.py",
             does_not_establish="that the transcript's numbers are CORRECT."),
    AreaDecl(7, "reconciliation", AreaState.LIVE, "exam/reconciliation.py",
             does_not_establish=(
                 "that every quantity in the substrate has a second derivation. "
                 "It establishes that the ones this area names AGREE.")),
    AreaDecl(8, "observability", AreaState.LIVE, "exam/provenance.py",
             does_not_establish="that the source announced anything."),
    AreaDecl(9, "envelope", AreaState.LIVE, "exam/envelope.py",
             does_not_establish="that the declared limits are TIGHT enough."),
    AreaDecl(10, "exam_self_check", AreaState.LIVE, "exam/cli.py",
             does_not_establish=(
                 "that this exam catches every defect class. It catches one.")),
    AreaDecl(11, "interface", AreaState.LIVE, "exam/interface.py",
             does_not_establish=(
                 "that the model is GOOD. It establishes that the substrate's "
                 "core areas do not depend on which model is plugged in.")),
    AreaDecl(12, "resource", AreaState.LIVE, "exam/resource.py",
             does_not_establish=(
                 "that the resource budget is TIGHT enough. It establishes that "
                 "the costs are measured, declared, and not superlinear.")),
    AreaDecl(13, "adversarial", AreaState.LIVE, "exam/adversarial.py",
             does_not_establish=(
                 "that the substrate is secure. It establishes that the "
                 "crafted attacks this area names are refused, and that a "
                 "refusal leaves the state intact.")),
    AreaDecl(14, "dreaming", AreaState.LIVE, "exam/cli.py",
             does_not_establish="that dreaming recombine memory."),
    AreaDecl(15, "mode_transition", AreaState.LIVE, "exam/cli.py",
             does_not_establish="that mode is a declared state machine."),
    AreaDecl(16, "spawning", AreaState.LIVE, "exam/cli.py",
             does_not_establish="that spawning is bounded and gated."),
    AreaDecl(17, "extraction", AreaState.LIVE, "exam/cli.py",
             does_not_establish="that extraction attaches provenance."),
    AreaDecl(18, "self_coding", AreaState.LIVE, "exam/cli.py",
             does_not_establish="that self-coding runs in a sandbox."),
    AreaDecl(19, "tools", AreaState.LIVE, "exam/tools.py",
             does_not_establish=(
                 "that the tool set is complete. It establishes that the "
                 "named tools are gated, that a refusal is a refusal, and "
                 "that an executed tool's effect is observable from outside "
                 "the process that ran it.")),
    AreaDecl(20, "skills", AreaState.LIVE, "exam/skills.py",
             does_not_establish=(
                 "that the skill set is good. It establishes that an UNSEEN "
                 "skill can be assembled from declared primitives, which is "
                 "the difference between composing and looking up.")),
    AreaDecl(21, "initiative", AreaState.LIVE, "exam/initiative.py",
             does_not_establish=(
                 "that the system is safe to leave alone. It establishes that "
                 "an unrequested action is gated, that the gate can refuse, "
                 "and that the attempt is on the record either way.")),
    AreaDecl(22, "planning", AreaState.LIVE, "exam/planning.py",
             does_not_establish=(
                 "that the plan is good. It establishes that a plan is STATE: "
                 "ordered steps, named dependencies, and a path that can be "
                 "abandoned.")),
]

BY_NUMBER: Dict[int, AreaDecl] = {d.number: d for d in AREA_DECLS}


def state_of(number: int) -> AreaState:
    return BY_NUMBER[number].state


def summary() -> Dict[str, Any]:
    """The counts, and the names of everything that is not LIVE."""
    live = [d for d in AREA_DECLS if d.state is AreaState.LIVE]
    stub = [d for d in AREA_DECLS if d.state is AreaState.STUB]
    dark = [d for d in AREA_DECLS if d.state is AreaState.DARK]
    return {
        "areas": len(AREA_DECLS),
        "live": len(live),
        "stub": len(stub),
        "dark": len(dark),
        "stub_areas": [{"area": d.number, "name": d.name, "why": d.reason}
                       for d in stub],
        "dark_areas": [{"area": d.number, "name": d.name, "why": d.reason}
                       for d in dark],
    }


def _main(argv: List[str]) -> int:
    # MEASURED 2026-11-05: `python -m exam.areas` printed the DOCSTRING
    # and exited, because `--help` was never passed and the guard
    # `if not argv` treated "no arguments" as "help". The module's own
    # docstring says "Run: python -m exam.areas", so the command it
    # advertises did not do what it says. A tool whose advertised
    # command prints its own documentation is a tool nobody can read.
    #
    # So: no arguments means PRINT THE REGISTRY, and `--help` means
    # print the documentation. The registry is the useful output; the
    # docstring is what you get when you ask for it.
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    s = summary()
    print("=" * 70)
    print("THE AREA REGISTRY -- what is measured, what is declared")
    print("=" * 70)
    for d in AREA_DECLS:
        print("  [%-4s] %2d  %-20s %s" % (d.state.value, d.number, d.name,
                                          d.module))
        if d.state is not AreaState.LIVE and d.reason:
            print("         %s" % d.reason[:120])
    print()
    print("  LIVE %d  STUB %d  DARK %d  of %d"
          % (s["live"], s["stub"], s["dark"], s["areas"]))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(_main(sys.argv[1:]))
