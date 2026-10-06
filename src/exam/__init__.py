"""
atlas_exam — the qualification harness, standing alone.

WHY THIS IS A SEPARATE REPOSITORY
---------------------------------
Because an exam that lives inside the system it grades cannot be
independent of it. `atlas_exam_v2` sat in simself/src/constitutional/
and scored 15/27 while 23 of its 27 items assigned themselves a
literal:

    def _item_harmonics():
        freq = 137.0
        return {"score": 1.0 if freq == 137.0 else 0.5}

That is not an examination. It cannot fail, so it cannot pass either.
The audit that found it was AST-based and lived in simself, which
means the thing that discovered the problem was inside the thing that
had it.

THE RULE THIS REPO ENFORCES
---------------------------
    atlas-exam depends on NOTHING.
    fieldcore and simself depend on nothing from atlas-exam.

The exam is pointed AT the substrate. If the exam imported the
substrate's helpers, a bug in those helpers would quietly become a
passing grade — which is exactly how v2 scored itself.

Where a check needs the substrate, it imports it AT RUNTIME, in a
subprocess, and reports the result. A missing substrate means a
SKIPPED check, never a PASSED one.

THE TEN AREAS
-------------
Inclusion criterion: if this fails, is the system unsafe or unusable?
If neither, it is not load-bearing and does not belong here.

    1  refusal          the gate can say no
    2  identity         psi_0 is immutable and fingerprinted
    3  boundedness      the state stays inside its ball
    4  liveness         accepted input actually moves the state
    5  return           the state relaxes to ground when input stops
    6  provenance       no claim without a traceable source
    7  reconciliation   independent derivations agree
    8  observability    an innovation residual reports change
    9  envelope         declared range and defined behaviour outside
    10 exam self-check  mutation yield, not pass rate

10 is the one that judges this exam. A qualification suite that cannot
tell a working system from a broken one is decoration, and v2 proved
that at 15/27.

STATUS, HONESTLY: zero areas implemented. The exam scores 0/10, and
under rule R1 below that is the correct starting value.

Run: python src/exam.py --list
"""

__version__ = "0.1.0"

AREA_COUNT = 10

AREAS = [
    (1, "refusal"),
    (2, "identity"),
    (3, "boundedness"),
    (4, "liveness"),
    (5, "return"),
    (6, "provenance"),
    (7, "reconciliation"),
    (8, "observability"),
    (9, "envelope"),
    (10, "exam_self_check"),
]