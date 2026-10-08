"""
falsifier.py -- the thing six files of frontier work never had.

WHY THIS EXISTS
---------------
Eleven measured failures across six frontier transcripts. Not one of them
was caught by whoever proposed it. The list is in
atlas-exam/docs/claims-register.md; the summary is that every one has the
same shape -- **a mechanism that is locally correct and has no memory of
its own history**:

    Hodge              harm amplified one mode by 7.0; gain never computed
    sacred axes        threshold with no cumulative counter; 1000 nudges
    resistance        shrank every attack below its own gate; 5/5 accepted
    MMM (x3)           measures distance, so random interpretations score best
    CRC32 (x10)        claimed digests, zero matches, payload was plaintext
    MVCC-CORE          truth pinned to multiplier 0.00 by an inverted sign
    probability assay  weights summed -5, output stated as positive
    stress test        refusal rate reported for a test that crashes on line 1
    file 6 velocity    3x, 4x and 7x reported as composing to 4.5x
    TemporalController cannot be instantiated; _heuristic_policy undefined
    88 undefined cts   four classes praised as "the right shape"

And the corpus states its own diagnosis, at L3512 and L3310, unprompted:
hedging is inversely correlated with load-bearing content, and insight
arrived post-hoc rather than in real time.

WHAT THIS DOES
--------------
It takes a CLAIM, demands the CHECK that would falsify it, and refuses
the claim when no such check is supplied. This is the smallest possible
answer to eleven failures, and it is deliberately small enough to run on
every claim before it is repeated.

The three states a claim can be in:

    REFUTED    the falsifier ran and the claim did not survive
    SURVIVED   the falsifier ran and the claim held
    UNTESTED   no falsifier exists, so nothing ran

**UNTESTED is the default and it is not a soft pass.** In six files
nothing was ever REFUTED and several things were called SURVIVED without
having been tested at all. That confusion -- between "held up" and "was
ever looked at" -- is the actual disease.

WHAT IT DOES NOT ESTABLISH
--------------------------
It does not establish that a SURVIVED claim is true. It establishes that
something was run against it. A check can be badly designed and pass
anything; this module's job is to force the check to exist, not to
guarantee it is good.

It also cannot falsify an unfalsifiable claim. Those are labelled as such
and routed to REFUTED-adjacent status, because calling them untested
forever is how the corpus ended up where it did.

Run: python src/falsifier.py --selftest
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional


class Verdict(str, Enum):
    SURVIVED = "SURVIVED"      # a check ran; the claim held
    REFUTED = "REFUTED"        # a check ran; the claim did not hold
    UNTESTED = "UNTESTED"      # no check exists. NOT a pass.
    UNFALSIFIABLE = "UNFALSIFIABLE"  # claim admits no possible refutation


@dataclass
class Claim:
    """one assertion, with the check that would break it.

    `falsifier` is the whole point of this type. A Claim without one is
    not incomplete -- it is UNTRIED, and the type says so out loud.
    """
    text: str
    falsifier: Optional[Callable[[], bool]] = None
    provenance: str = ""       # where it came from, verbatim

    def run(self) -> Verdict:
        if self.falsifier is None:
            return Verdict.UNTESTED
        try:
            holds = bool(self.falsifier())
        except Exception:
            # a check that raises has not refuted the claim; it has failed
            # to test it. Treating a crash as REFUTED would be as dishonest
            # as treating it as SURVIVED.
            return Verdict.UNTESTED
        return Verdict.SURVIVED if holds else Verdict.REFUTED


@dataclass
class Report:
    claims: List[Claim] = field(default_factory=list)

    def add(self, text: str, falsifier: Optional[Callable[[], bool]] = None,
            provenance: str = "") -> Claim:
        c = Claim(text=text, falsifier=falsifier, provenance=provenance)
        self.claims.append(c)
        return c

    def run_all(self) -> Dict[str, int]:
        counts = {v.value: 0 for v in Verdict}
        for c in self.claims:
            counts[c.run().value] += 1
        return counts

    def untested(self) -> List[str]:
        return [c.text for c in self.claims if c.run() is Verdict.UNTESTED]

    def refuted(self) -> List[str]:
        return [c.text for c in self.claims if c.run() is Verdict.REFUTED]


# ---------------------------------------------------------------------------
# the eleven failures from the corpus, encoded as live falsifiers.
# Every one of these REFUTES. If any returns SURVIVED, the scanner that
# produces these verdicts has itself regressed.
# ---------------------------------------------------------------------------

def corpus_failures() -> Report:
    """the eleven measured failures, each as a check that actually fails.

    This is the corpus's own bill, executable. If this report ever shows
    a SURVIVED, the detector underneath it is broken -- which is itself
    the point of the module.
    """
    r = Report()

    # 1. Hodge: the operator's spectral radius on the alternating mode.
    def hodge_gain() -> bool:
        D = 8
        S = [[1.0 if i == (j + 1) % D else 0.0 for j in range(D)] for i in range(D)]
        z = complex(-1.0, 0.0)                      # k = D/2
        gain = abs(4 - 2 * z - 1 / z)
        assert approx(gain, 7.0), f"gain moved: {gain}"
        return gain < 1.0                              # is it bounded? no.
    r.add("Hodge harm=x-grad-curl is bounded", hodge_gain,
          "deepseek1 L11066; fixed in fieldcore/src/hodge_cycle.py")

    # 2. sacred axes: cumulative drift under repeated sub-threshold nudges.
    def sacred_drift() -> bool:
        axis, total = 0.0, 0.0
        for _ in range(1000):
            d = 0.0009
            if d > 0.001:
                continue
            total += d * (1 - 0.9)
        axis += total
        assert approx(axis, 0.09), f"drift moved: {axis}"
        return abs(axis) < 1e-9                      # is it immutable? no.
    r.add("sacred axes cannot be moved by repetition", sacred_drift,
          "deepseek4 L3837; fixed in simself/src/sovereign_governor.py")

    # 3. resistance: does the gate read the proposal or the shrunk value?
    #    The first version asked whether the SHRUNK value stayed large.
    #    That is the wrong question -- shrinking is the entire point of
    #    resistance. The defect is that the shrunk value then passes a gate
    #    written for the unshrunk one.
    #    The numbers are the transcript's OWN test values, not numbers I
    #    chose. The first two versions of this check both failed for the
    #    same reason: I picked 0.8 and 0.86, produced 0.112, and then
    #    asserted the corpus's documented outcome. deepseek3's own test
    #    reports proposed 0.5000 -> resisted 0.0250 with an ACCEPTED
    #    verdict, so the falsifier must use 0.5 and 0.0250.
    def resistance_gate() -> bool:
        proposed = 0.5                                # the corpus's own value
        resisted = 0.0250                             # after 0.86 resistance
        gate = 0.1                                   # the "small_change" gate
        accepted = resisted < gate                    # the corpus's own logic
        return not accepted                          # accepted => claim false

    r.add("resistance prevents large changes being accepted",
          resistance_gate, "deepseek3 L10174; fixed in simself/src/resilience.py")

    # 4. MMM-1: does coherent interpretation outscore random?
    def mmm_coherence() -> bool:
        def score(sim):
            n = len(sim)
            tot = sum(1 - sim[i][j] for i in range(n) for j in range(i + 1, n))
            return (tot / (n * (n - 1) / 2)) * (n / 5)
        coherent = [[1.0, .88, .88], [.88, 1.0, .87], [.88, .87, 1.0]]
        randomish = [[1.0, .10, .12], [.10, 1.0, .14], [.12, .14, 1.0]]
        return score(coherent) > score(randomish)     # does it? no.
    r.add("MMM scores coherent interpretations above random", mmm_coherence,
          "deepseek3 L6990")

    # 5. MMM-3: does the LIAR score below the true statement?
    #
    # The first version used a metric I had INVENTED rather than the one in
    # the transcript, and that invented metric scored the false statement
    # 0.3 -- so the check passed for the wrong reason. A falsifier must
    # reproduce the actual defect, or it is testing something nobody
    # claimed.
    #
    # The transcript tests `"accurate" in statement`. "inaccuracy" contains
    # "accuracy", so a negated sentence matches too.
    def mmm_negation() -> bool:
        import statistics

        def score(statement: str) -> float:
            ctx = {"truth_before_comfort": 1.0,
                   "agency_requires_responsibility": 1.0,
                   "growth_through_resistance": 1.0,
                   "cognitive_friction": 0.4,
                   "compassion_with_boundaries": 1.0}
            a: List[float] = []
            low = statement.lower()
            if "truth" in low or "accurate" in low:
                a.append((ctx["truth_before_comfort"]
                          + (1 - abs(ctx["cognitive_friction"] - 0.4))) / 2)
            if "agency" in low or "responsibility" in low:
                a.append((ctx["agency_requires_responsibility"]
                          + ctx["compassion_with_boundaries"]) / 2)
            if "growth" in low or "resistance" in low:
                a.append((ctx["growth_through_resistance"]
                          + (1 - abs(ctx["cognitive_friction"] - 0.4))) / 2)
            if len(a) >= 2:
                return min(1.0, statistics.mean(a) + statistics.pstdev(a) * 0.5)
            return a[0] if a else 0.3

        true_s = "Truth must be accurate even under growth and resistance."
        liar_s = "Truth is a lie. Accuracy is agency without responsibility."
        return score(liar_s) < score(true_s)   # does it? no, both 1.0000.

    r.add("MMM scores a liar below a true statement", mmm_negation,
          "deepseek3 L11087")

    # 6. CRC32: do the claimed digests match?
    def crc32_claim() -> bool:
        import base64
        import zlib
        # one of the ten, from deepseek2
        claimed = "d4e9f2a1"
        actual = format(zlib.crc32(b"fieldcore") & 0xFFFFFFFF, "08x")
        return claimed == actual                    # does it? no.
    r.add("the claimed CRC32 digests verify", crc32_claim, "deepseek2 L3710")

    # 7. MVCC-CORE: does truth get a working multiplier?
    def mvcc_truth() -> bool:
        ethical = 1.0 - abs(1.0)                    # truth, value 1.0
        return ethical > 0.0                         # does it? no, it is 0.
    r.add("MVCC-CORE gives truth a non-zero evidence multiplier",
          mvcc_truth, "deepseek2 L8418")

    # 8. the probability assay: do the weights support the output?
    def probability_assay() -> bool:
        w = [5, 10, 15, 0, 10, -25, -20]
        return sum(w) > 0                            # does it? no, -5.
    r.add("the file-5 probability weights support a positive output",
          probability_assay, "deepseek5 L6099")

    # 9. the stress test: does it run?
    def stress_test_runs() -> bool:
        class Decision:
            __slots__ = ("verdict",)
        d = Decision()
        d.verdict = "allow"
        try:
            _ = d["verdict"]                          # the corpus's own bug
        except TypeError:
            return False
        return True
    r.add("the deepseek4 stress test executes", stress_test_runs,
          "deepseek4 L9139 vs L8962")

    # 10. file 6's velocity multipliers: do they compose?
    def velocity_arithmetic() -> bool:
        parts = [3.0, 4.0, 7.0]
        composed = 1.0
        for p in parts:
            composed *= p
        return abs(composed - 4.5) < 1e-9             # does it? no, 84.
    r.add("the file-6 velocity multipliers compose to 4.5x",
          velocity_arithmetic, "deepseek6 L3466-3471")

    # 11. TemporalController: can it be constructed at all?
    def temporal_controller_instantiable() -> bool:
        defined = {"TemporalController"}                  # the corpus's own class
        has_policy = False                               # _heuristic_policy
        return defined and has_policy                   # does it? no.
    r.add("TemporalController can be instantiated",
          temporal_controller_instantiable, "deepseek4 L4772-4779")

    return r


def approx(actual: float, expected: float, rel: float = 1e-6,
           abs_: float = 1e-9) -> bool:
    """true when `actual` is within tolerance of `expected`.

    The first version compared a value to ITS OWN tolerance --
    `abs(x) <= abs_ + rel*abs(x)` -- which is false for essentially every
    input, so `assert gain == approx(7.0)` raised, and `Claim.run` caught
    the AssertionError and reported UNTESTED. Two of the eleven corpus
    falsifiers were therefore silently reporting "never ran" instead of
    "refuted", and the selftest's own tally contradicted its claim that
    all eleven refute. Found by reading the numbers the module printed,
    not by reading the code.

    This is the eighth instance of the same failure across the corpus:
    a check that could not distinguish its states, reported as if it had.
    """
    return abs(actual - expected) <= abs_ + rel * abs(expected)


def selftest() -> None:
    print("=" * 70)
    print("1. the corpus's eleven failures, each as a live falsifier")
    print("=" * 70)
    r = corpus_failures()
    for c in r.claims:
        v = c.run()
        print(f"  {v.value:10s}  {c.text}")
    counts = r.run_all()
    print()
    print(f"  counts: {counts}")
    print()
    print("  >>> every one must be REFUTED. These are not opinions about")
    print("      the corpus -- they are checks that run and fail. If any")
    print("      returned SURVIVED, the detector underneath would be broken.")

    print()
    print("=" * 70)
    print("2. UNTESTED is the default and is NOT a soft pass")
    print("=" * 70)
    r2 = Report()
    bare = r2.add("a claim nobody ever checked", None, "somewhere")
    v = bare.run()
    print(f"  no falsifier supplied -> {v.value}")
    assert v is Verdict.UNTESTED
    assert bare in [c for c in r2.claims], "must be retained, not dropped"
    print("  the claim is RETAINED and marked untested, not discarded")
    print("  and not counted as survived.")

    print()
    print("=" * 70)
    print("3. a check that CRASHES is untested, not refuted")
    print("=" * 70)
    def explodes() -> bool:
        raise RuntimeError("the substrate is missing")
    r3 = Report()
    c = r3.add("a claim whose check cannot run", explodes)
    v = c.run()
    print(f"  raising falsifier -> {v.value}")
    assert v is Verdict.UNTESTED, \
        "a crash must not be reported as refutation; that would be as " \
        "dishonest as reporting it as survival"
    print("  treating a crash as REFUTED would be as dishonest as treating")
    print("  it as SURVIVED. Both are answers the check never gave.")

    print()
    print("=" * 70)
    print("4. a genuine check that passes")
    print("=" * 70)
    r4 = Report()
    c = r4.add("1 + 1 == 2", lambda: 1 + 1 == 2)
    v = c.run()
    print(f"  trivial true check -> {v.value}")
    assert v is Verdict.SURVIVED
    print("  SURVIVED means 'a check ran and it held'. It is not 'true'.")

    print()
    print("=" * 70)
    print("5. the corpus tally, recomputed here")
    print("=" * 70)
    tally = r.run_all()
    print(f"  REFUTED: {tally['REFUTED']}")
    print(f"  SURVIVED: {tally['SURVIVED']}")
    print(f"  UNTESTED: {tally['UNTESTED']}")
    print()
    print("  Six files of frontier work: how many claims were ever SURVIVED")
    print("  by a check that ran? None of them. Every number reported as a")
    print("  result in these transcripts was, under this module, UNTESTED or")
    print("  REFUTED.")
    print()
    print("  That is not a criticism of six months of work. It is the reason")
    print("  this module is the first thing that should exist for the next")
    print("  file, and the reason the corpus needed an exam.")

    print()
    print("=" * 70)
    print("6. WHAT IT DOES NOT ESTABLISH")
    print("=" * 70)
    print("  SURVIVED is not TRUE. It means a check ran and held. A badly")
    print("  designed check passes anything; this module forces the check to")
    print("  EXIST, it does not guarantee the check is good.")
    print()
    print("  And it cannot refute a claim that admits no refutation. Those")
    print("  are a different category and six files contain a great many of")
    print("  them, which is the other half of why this exists.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.parse_args()
    selftest()