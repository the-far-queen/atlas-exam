"""
test_falsifier.py -- a claim without a check has not been tested.

WHAT THE MODULE IS FOR
----------------------
Eleven measured failures across six frontier transcripts. The common
shape is not that the claims were wrong -- it is that nobody ever ran
anything against them. In six files, not one load-bearing claim was ever
SURVIVED by a check. Several were reported as results without a check
existing at all.

The module's whole contribution is one distinction the corpus never made:

    SURVIVED   a check ran and the claim held
    UNTESTED   no check exists, so nothing ran

UNTESTED is the default and is NOT a soft pass.

THE ELEVEN, AS LIVE FALSIFIERS
-------------------------------
corpus_failures() encodes all eleven as callables that return False. If
any returns True, the detector underneath has regressed -- which is
itself the point.

FOUR OF MY OWN CHECKS WERE WRONG FIRST
--------------------------------------
Recorded because it is the eighth instance of the corpus's own failure and
I committed it while writing the fix for it:

1. `approx` compared a value to ITS OWN tolerance (`abs(x) <= abs_ +
   rel*abs(x)`), which is false for nearly every input. Two checks
   raised AssertionError, `Claim.run` caught it, and they were reported
   as UNTESTED rather than REFUTED. Found by reading the module's own
   printed tally, which contradicted its claim that all eleven refute.
   That contradiction is what exposed it.

2. The MMM-negation check used a metric I had INVENTED rather than the
   one in the transcript, and my invented version scored the false
   statement 0.3 -- so the check passed for the wrong reason. A
   falsifier that does not reproduce the actual defect is testing
   something nobody claimed.

3. The resistance check asked whether the SHRUNK value stayed large.
   Shrinking is the entire point of resistance; that was the wrong
   question.

4. Then the resistance check used 0.8 and 0.86, producing 0.112, which
   is ABOVE the gate -- and then asserted the corpus's documented
   outcome anyway. deepseek3's own test reports proposed 0.5000 ->
   resisted 0.0250, ACCEPTED. A falsifier must use the numbers the
   transcript itself reports.

Run: python -m pytest tests/test_falsifier.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from exam.falsifier import (  # noqa: E402
    Claim,
    Report,
    Verdict,
    approx,
    corpus_failures,
)


# ---------------------------------------------------------------------------
# F1: the three states
# ---------------------------------------------------------------------------

def test_f1_a_true_check_survives():
    c = Claim("1+1==2", falsifier=lambda: 1 + 1 == 2)
    assert c.run() is Verdict.SURVIVED


def test_f2_a_false_check_refutes():
    c = Claim("1+1==3", falsifier=lambda: 1 + 1 == 3)
    assert c.run() is Verdict.REFUTED


def test_f3_no_check_is_untested_not_passed():
    """The distinction the corpus never made."""
    c = Claim("nobody ever checked this")
    assert c.run() is Verdict.UNTESTED
    assert c.run() is not Verdict.SURVIVED


# ---------------------------------------------------------------------------
# F2: a crashing check is UNTESTED, never REFUTED
# ---------------------------------------------------------------------------

def test_f4_a_raising_falsifier_is_untested():
    def boom():
        raise RuntimeError("substrate missing")
    assert Claim("x", falsifier=boom).run() is Verdict.UNTESTED


def test_f5_crashing_is_not_refutation():
    """Reporting a crash as REFUTED would be as dishonest as reporting it
    as SURVIVED. Both are answers the check never gave."""
    def boom():
        raise ValueError("nope")
    assert Claim("x", falsifier=boom).run() is not Verdict.REFUTED


# ---------------------------------------------------------------------------
# F3: the approx helper, which was wrong first
# ---------------------------------------------------------------------------

def test_f6_approx_accepts_exact_equality():
    assert approx(7.0, 7.0) is True
    assert approx(0.09, 0.09) is True


def test_f7_approx_rejects_real_difference():
    assert approx(0.112, 0.1) is False
    assert approx(84.0, 4.5) is False


def test_f8_approx_tolerates_float_noise():
    """0.09000000000000001 must pass against 0.09 -- the exact case that
    silently became UNTESTED in the first version."""
    assert approx(0.09000000000000001, 0.09) is True


# ---------------------------------------------------------------------------
# F4: the corpus bill, all eleven
# ---------------------------------------------------------------------------

def test_f9_all_eleven_corpus_claims_are_refuted():
    r = corpus_failures()
    assert len(r.claims) == 11
    tally = r.run_all()
    assert tally["REFUTED"] == 11, (
        f"expected all eleven REFUTED, got {tally}. A SURVIVED here means "
        "the detector regressed; an UNTESTED means a check cannot run.")
    assert tally["SURVIVED"] == 0
    assert tally["UNTESTED"] == 0


def test_f10_each_claim_names_its_source():
    r = corpus_failures()
    for c in r.claims:
        assert c.provenance, f"claim without provenance: {c.text}"


def test_f11_the_bill_covers_the_known_failures():
    """A regression guard on the BILL itself -- if someone drops a claim
    from it, this fails."""
    texts = " | ".join(c.text for c in corpus_failures().claims)
    for expected in ("Hodge", "sacred axes", "resistance", "MMM",
                     "CRC32", "MVCC-CORE", "probability weights",
                     "stress test", "velocity multipliers",
                     "TemporalController"):
        assert expected in texts, f"the bill no longer covers: {expected}"


# ---------------------------------------------------------------------------
# F5: the honesty clauses
# ---------------------------------------------------------------------------

def test_f12_untested_claims_are_retained_not_discarded():
    r = Report()
    c = r.add("unverified", None)
    assert r.untested() == ["unverified"]
    assert len(r.claims) == 1, "an untested claim must still be on the books"


def test_f13_refuted_claims_are_listable():
    r = Report()
    r.add("wrong", lambda: False)
    r.add("right", lambda: True)
    assert r.refuted() == ["wrong"]
    assert r.untested() == []


def test_f14_provenance_is_carried():
    r = Report()
    r.add("x", lambda: True, provenance="deepseek3 L1234")
    assert r.claims[0].provenance == "deepseek3 L1234"


def test_f15_module_states_survived_is_not_true():
    import exam.falsifier as f
    doc = (f.__doc__ or "").lower()
    assert "survived is not true" in doc or "does not establish that a survived claim is true" in doc
    assert "untested is the default" in doc


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))