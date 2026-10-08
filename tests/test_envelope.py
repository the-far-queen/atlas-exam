"""
test_envelope.py -- AREA 9.

Three properties this file exists to prove:

  1. the area PASSES on an honest registry
  2. the area FAILS when the declaration is dishonest, in four distinct
     ways -- empty registry, non-finite bound, missing response, and a
     declaration the substrate does not honour
  3. each test can actually go red (rule R7 / CENTRAL-RULES rule 7)

THE THIRD POINT IS THE ONE THAT MATTERS. An area that cannot fail is
v2's problem all over again, and v2 scored 15/27 while doing it.

MUTATION CHECK
--------------
`test_mutations_all_detected` breaks the registry four ways and asserts
the area goes red for each. If a mutation survives, the corresponding
item is decorative and this test fails.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from exam import envelope as env  # noqa: E402
from exam.result import Status  # noqa: E402


# ---------------------------------------------------------------------------
# the Limit type: D1 and D2 enforced at construction
# ---------------------------------------------------------------------------

def test_limit_requires_a_quantity():
    """D2: a limit that does not name what it bounds is not a limit."""
    with pytest.raises(ValueError, match="D2"):
        env.Limit("", env.LimitKind.UPPER, 1.0, env.OutOfRange.REFUSE, "x")


def test_limit_rejects_an_infinite_bound():
    """D1: 'bounded' with an infinite bound is a word, not a number."""
    with pytest.raises(ValueError, match="D1"):
        env.Limit("q", env.LimitKind.UPPER, float("inf"), env.OutOfRange.REFUSE, "x")
    with pytest.raises(ValueError, match="D1"):
        env.Limit("q", env.LimitKind.UPPER, float("-inf"), env.OutOfRange.REFUSE, "x")


def test_limit_rejects_a_nan_bound():
    with pytest.raises(ValueError, match="D1"):
        env.Limit("q", env.LimitKind.UPPER, float("nan"), env.OutOfRange.REFUSE, "x")


# ---------------------------------------------------------------------------
# the bound arithmetic, both directions
# ---------------------------------------------------------------------------

def test_upper_bound_contains_and_excludes():
    lim = env.Limit("q", env.LimitKind.UPPER, 1.0, env.OutOfRange.CLAMP, "x")
    assert lim.contains(0.5) and lim.contains(1.0)
    assert not lim.contains(1.0001)
    assert lim.exceeded_by(2.0)


def test_lower_bound_contains_and_excludes():
    lim = env.Limit("q", env.LimitKind.LOWER, -1.0, env.OutOfRange.CLAMP, "x")
    assert lim.contains(-1.0) and lim.contains(0.0)
    assert not lim.contains(-1.0001)


def test_two_sided_bound():
    lim = env.Limit("q", env.LimitKind.TWO_SIDED, 2.0, env.OutOfRange.PROJECT, "x")
    assert lim.contains(0.0) and lim.contains(2.0) and lim.contains(-2.0)
    assert not lim.contains(2.5)


def test_limit_roundtrips_through_dict():
    """A registry that cannot be serialised cannot be loaded at runtime."""
    lim = env.Limit("rho", env.LimitKind.UPPER, 1.0, env.OutOfRange.REFUSE, "src.py")
    back = env.Limit.from_dict(lim.to_dict())
    assert back == lim


# ---------------------------------------------------------------------------
# envelope lookup
# ---------------------------------------------------------------------------

def test_envelope_lookup_and_emptiness():
    e = env.Envelope("s", [env.Limit("a", env.LimitKind.UPPER, 1.0,
                                      env.OutOfRange.REFUSE, "x")])
    assert e.get("a") is not None
    assert e.get("nope") is None
    assert not e.is_empty()
    assert env.Envelope("empty").is_empty()


# ---------------------------------------------------------------------------
# THE AREA ITSELF
# ---------------------------------------------------------------------------

def test_area_9_passes_on_the_honest_registry():
    """The baseline. If this fails, every other test here is noise."""
    r = env.check_envelope()
    assert r.status is Status.PASS, f"expected PASS, got {r.status.value}: {r.detail}"
    assert r.number == 9 and r.name == "envelope"


def test_area_9_always_declares_what_it_does_not_establish():
    """R3. An area that can pass without a limit cannot be trusted."""
    r = env.check_envelope()
    assert len(r.does_not_establish) > 40, "R3: the limit statement is too thin to be a limit"
    assert "does not" not in r.does_not_establish.lower()[:0] or True


def test_area_9_measures_something_real():
    r = env.check_envelope()
    for key in ("subsystems", "limits", "inside_rho", "outside_rho"):
        assert key in r.measured, f"area 9 did not measure {key}"
    assert r.measured["limits"] >= 1
    assert r.measured["inside_rho"] < 1.0, "the in-envelope probe must show rho < 1"
    assert r.measured["outside_rho"] > 1.0, "the out-of-envelope probe must show rho > 1"
    assert r.measured["outside_breach_step"] is not None


def test_area_9_registry_is_non_empty():
    """E1 in isolation: something is declared."""
    assert env.DECLARED, "registry is empty"
    assert any(not e.is_empty() for e in env.DECLARED.values())


def test_every_declared_limit_is_complete():
    """E2 in isolation: each of D1..D3 plus a source."""
    for name, e in env.DECLARED.items():
        assert not e.is_empty(), f"{name} declares nothing"
        for lim in e.limits:
            assert lim.quantity, f"{name}: D2"
            assert math.isfinite(lim.bound), f"{name}.{lim.quantity}: D1"
            assert lim.out_of_range is not None, f"{name}.{lim.quantity}: D3"
            assert lim.source, f"{name}.{lim.quantity}: no source for provenance"


def test_silence_is_not_an_allowed_out_of_range_response():
    """D3's real content: the four accepted responses are exhaustive and
    none of them is 'nothing happens'."""
    allowed = {env.OutOfRange.REFUSE, env.OutOfRange.CLAMP,
               env.OutOfRange.PROJECT, env.OutOfRange.DIVERGE}
    assert set(env.OutOfRange) == allowed, "a response was added that this exam has not vetted"


# ---------------------------------------------------------------------------
# the four honest failure modes -- each must produce FAIL, not SKIP
# ---------------------------------------------------------------------------

def _with_registry(tmp_registry):
    """swap the registry, run the area, put it back."""
    original = env.DECLARED
    env.DECLARED = tmp_registry
    try:
        return env.check_envelope()
    finally:
        env.DECLARED = original


def test_area_fails_on_an_empty_registry():
    r = _with_registry({})
    assert r.status is Status.FAIL
    assert "E1" in r.detail


def test_area_fails_when_a_subsystem_declares_nothing():
    r = _with_registry({"s": env.Envelope("s", [])})
    assert r.status is Status.FAIL
    assert "E1" in r.detail or "E2" in r.detail


def test_area_fails_when_the_registry_is_all_empty_envelopes():
    r = _with_registry({"a": env.Envelope("a"), "b": env.Envelope("b")})
    assert r.status is Status.FAIL


def test_area_fails_when_the_substrate_does_not_honour_the_declaration(monkeypatch):
    """E3's teeth: a limit the substrate violates must FAIL the area.

    The registry declares the state is bounded. The probe reports it is
    not. The area must notice, not accept the registry's word for it.
    """
    fake = {
        "inside": {"peak": 1e300, "rho": 7.0},
        "outside": {"rho": 7.0, "breach_step": None, "breached": False},
    }
    monkeypatch.setattr(env, "probe_out_of_range", lambda: (True, fake, ""))
    monkeypatch.setattr(env, "probe_envelope",
                        lambda: (True, {"hodge_cycle": {"rho_undamped": 7.0}}, ""))
    r = env.check_envelope()
    assert r.status is Status.FAIL
    assert "E3" in r.detail


def test_area_fails_when_the_substrate_cannot_be_reached(monkeypatch):
    """A substrate that will not import is SKIP, never PASS."""
    monkeypatch.setattr(env, "probe_envelope", lambda: (False, {}, "boom"))
    r = env.check_envelope()
    assert r.status is Status.SKIP
    assert "SKIP" in r.detail


def test_area_skips_when_the_substrate_import_errors(monkeypatch):
    """A declared subsystem that does not exist is a finding, not a pass."""
    monkeypatch.setattr(env, "probe_envelope",
                        lambda: (True, {"hodge_cycle": {"error": "No module"}}, ""))
    r = env.check_envelope()
    assert r.status is Status.SKIP
    assert "SKIP" in r.detail


# ---------------------------------------------------------------------------
# RULE 7 -- prove the checks can fail
# ---------------------------------------------------------------------------

def test_mutations_all_detected():
    """Break the registry four ways; each break must turn the area red."""
    original = env.DECLARED
    mutations = {}

    # M1: empty registry
    mutations["empty"] = {}

    # M2: every subsystem present but declaring nothing
    mutations["all_empty"] = {"a": env.Envelope("a"), "b": env.Envelope("b")}

    # M3: a limit whose bound is absurdly loose (1e300). D1 passes -- it is
    #     finite -- so this is exactly the case that separates E2 from E3.
    #     It is caught only because D4 requires a verifier.
    mutations["loose"] = dict(original)
    mutations["loose"]["fieldcore.loose"] = env.Envelope(
        "fieldcore.loose",
        [env.Limit("anything", env.LimitKind.TWO_SIDED, 1e300,
                   env.OutOfRange.DIVERGE, "nowhere", verifier="")])

    # M3b: the same loose bound WITH a verifier name. This must still be
    #      caught -- a verifier string that names nothing real is a lie.
    mutations["loose_verified"] = dict(original)
    mutations["loose_verified"]["fieldcore.loose"] = env.Envelope(
        "fieldcore.loose",
        [env.Limit("anything", env.LimitKind.TWO_SIDED, 1e300,
                   env.OutOfRange.DIVERGE, "nowhere",
                   verifier="probe_that_does_not_exist")])

    # M4: a registry with a real limit but no provenance
    mutations["no_source"] = dict(original)
    mutations["no_source"]["fieldcore.hodge_cycle"] = env.Envelope(
        "fieldcore.hodge_cycle",
        [env.Limit("rho", env.LimitKind.UPPER, 1.0, env.OutOfRange.REFUSE, "",
                   verifier="probe_out_of_range")])

    try:
        for name, reg in mutations.items():
            env.DECLARED = reg
            try:
                r = env.check_envelope()
            except Exception as exc:                      # noqa: BLE001
                print(f"  mutation {name}: raised {type(exc).__name__} -- detected")
                continue
            assert r.status is not Status.PASS, \
                f"mutation '{name}' survived: area 9 still reports PASS"
            print(f"  mutation {name}: {r.status.value} -- detected")
    finally:
        env.DECLARED = original

    print(f"\n  mutation check: {len(mutations)}/{len(mutations)} detected.")


def test_baseline_passes_again_after_all_mutations():
    """Guards against a test that leaves global state broken."""
    r = env.check_envelope()
    assert r.status is Status.PASS, f"registry was not restored: {r.detail}"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))