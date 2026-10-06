"""
result.py — the result type, and the scoring rules.

FOUR RULES, EACH FROM A SPECIFIC FAILURE
----------------------------------------

R1  UNIMPLEMENTED IS FAIL.
     v2 scored 15/27 while most of its items were literals. If the
     score can rise without work being done, something lies. An area
     with no implementation has failed, not been excused.

R2  BINARY. NO PARTIAL CREDIT.
     v2's 0.5 scores hid that half the exam was decorative. A metric
     that half-works has failed.

R3  EVERY AREA DECLARES WHAT IT DOES NOT ESTABLISH.
     A pass must never be readable as a general claim.

R4  NO AGGREGATE ABOVE THE FLOOR OF ITS PARTS.
     Per-area reporting only. A single total is how a self-scoring
     exam reported 0.778 and looked respectable.

ALSO, and this is not negotiable:

    A MISSING SUBSTRATE IS A SKIP, NEVER A PASS.
    The exam is pointed at fieldcore and simself. If either is absent,
    the area is SKIPPED -- which counts as FAIL in the roll-up, because
    an exam that passes because it could not run is worse than useless.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class Status(Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"        # could not run. counts as FAIL in the roll-up.
    TODO = "TODO"        # not implemented. counts as FAIL.

    @property
    def counts_as_pass(self) -> bool:
        return self is Status.PASS


@dataclass
class AreaResult:
    """One area's verdict, with everything needed to trust it."""

    number: int
    name: str
    status: Status
    detail: str
    does_not_establish: str
    measured: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "area": self.number,
            "name": self.name,
            "status": self.status.value,
            "detail": self.detail,
            "does_not_establish": self.does_not_establish,
            "measured": self.measured,
        }


@dataclass
class ExamReport:
    results: List[AreaResult]

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status.counts_as_pass)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def skipped(self) -> List[int]:
        return [r.number for r in self.results if r.status is Status.SKIP]

    @property
    def todo(self) -> List[int]:
        return [r.number for r in self.results if r.status is Status.TODO]

    def passing_areas(self) -> List[int]:
        return [r.number for r in self.results if r.status.counts_as_pass]

    def verdict(self) -> str:
        """PASS only if every area passes.

        No partial overall verdict. R1: a TODO or a SKIP is not a pass.
        """
        if self.passed == self.total and self.total > 0:
            return "PASS"
        if not self.results:
            return "NOT RUN"
        return "FAIL"

    def to_dict(self) -> Dict:
        return {
            "verdict": self.verdict(),
            "passed": self.passed,
            "total": self.total,
            "passing_areas": self.passing_areas(),
            "skipped_areas": self.skipped,
            "not_implemented_areas": self.todo,
            "results": [r.to_dict() for r in self.results],
        }


def make(number: int, name: str, ok: bool, detail: str,
         does_not_establish: str, measured: Optional[Dict] = None
         ) -> AreaResult:
    return AreaResult(
        number=number, name=name,
        status=Status.PASS if ok else Status.FAIL,
        detail=detail,
        does_not_establish=does_not_establish,
        measured=measured or {},
    )


def skip(number: int, name: str, reason: str,
         does_not_establish: str = "anything -- it did not run") -> AreaResult:
    return AreaResult(number=number, name=name, status=Status.SKIP,
                      detail=reason, does_not_establish=does_not_establish)


def todo(number: int, name: str, why: str,
         does_not_establish: str = "anything -- it is not written"
         ) -> AreaResult:
    return AreaResult(number=number, name=name, status=Status.TODO,
                      detail=why, does_not_establish=does_not_establish)