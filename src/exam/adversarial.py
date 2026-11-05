"""
adversarial.py -- AREA 13. Do the bounds hold under a crafted attack?

WHY THIS AREA, AND WHY IT IS NOT AREA 3
---------------------------------------
Area 3 (boundedness) asks whether the state stays inside its ball under
ORDINARY input: a thousand random observations. This area asks a
different question, and the difference is the whole content of it:

    ordinary input   the attacker is not trying
    crafted attack  the attacker KNOWS the rule and is trying to break it

Distinct from area 3. Area 3 can pass while every crafted attack
succeeds, and that is exactly what happened here.

THE DEFECT THIS AREA FOUND, and it is the reason this file exists
------------------------------------------------------------------
MEASURED 2026-11-04, against the substrate, before this area was
written:

    NaN payload -> the gate ALLOWED it -> the state became NaN

The reason is not exotic. `float('nan') > 4.0` is False, and
`float('nan') < 0.4` is False, so a gate that tests only those two
inequalities ADMITS a vector of NaN. Then the arithmetic poisons the
state: drift becomes NaN, and every comparison against R is False, so
the projection operator stops projecting.

AND THE POLICY HAD ALREADY SPLIT. `fieldcore/src/gate.py` tested
finiteness -- it returns REFUSE_NONFINITE -- and the OUT-OF-PROCESS
GOVERNOR tested finiteness too. But the copies in
`simself/src/constitutional/simself.py`,
`simself/src/harness/gate.py`,
`simself/src/constitutional/dreaming.py` and
`fieldcore/src/tiniest_core/tiniest_core.py` did NOT. So the SAME
packet was refused by one core and admitted by another.

That is the shape of a real attack: not one that defeats the gate, but
one that finds the copy of the gate that does not have the check.

SO THIS AREA DOES THREE THINGS
------------------------------
    A1  it runs the CRAFTED ATTACKS against the substrate's real
        admission path, and every one must be REFUSED with a reason
    A2  it asserts that a refusal LEAVES THE STATE INTACT -- an attack
        that is refused but still corrupts the state is not refused
    A3  it asserts that EVERY gate copy in both repos AGREES with the
        canonical gate, on the adversarial inputs specifically

A3 is the one that earned the area. A1 alone would pass with a
consistently broken gate. A3 is what makes the policy one policy.

WHY A SUBPROCESS
----------------
The exam points AT the substrate. A bug in the substrate's helper would
become a passing grade.

Run: python -m exam.adversarial
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


#: A1 + A2 -- the crafted attacks against the substrate's real path.
#:
#: Each attack is a PACKET, not a description. The probe drives the
#: substrate's own `observe()`, which is the admission path the system
#: actually uses, and reads back the verdict AND the state.
PROBE_ATTACKS = r"""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.expanduser("~"), "AppData", "Local",
                                "hermes", "work_repos", "simself", "src"))
import numpy as np
from constitutional.constitution import Constitution
from constitutional.ground import Ground
from constitutional.simself import SimSelf

c = Constitution()
D = c.dim

def fresh():
    return SimSelf(constitution=c, ground=Ground(c.psi_0.copy()), R=3.0, eta=0.1)

# --- the attacks ---------------------------------------------------------
# Each is (name, packet). They are CRAFTED: each one targets a
# specific rule in the gate, and each one is a packet a caller could
# actually construct.
def nan_packet():
    v = np.zeros(D); v[0] = np.nan; v[2] = 1.0
    return v

def inf_packet():
    v = np.zeros(D); v[0] = np.inf; v[2] = 1.0
    return v

def all_nan_packet():
    return np.full(D, np.nan)

def nan_psi0_packet():
    # a ground that is itself NaN. If the gate does not test the ground
    # for finiteness, every comparison against it is False and the
    # packet is admitted.
    #
    # AND IT IS INSTALLED THROUGH THE PUBLIC CONSTRUCTOR, not by
    # assigning to the property. `Ground.psi_0` is a read-only
    # property, so the first version of this probe tried
    # `s.psi0 = packet` and raised AttributeError -- which the exam
    # correctly reported as a SKIP rather than a pass.
    #
    # And the constructor does NOT refuse it: `Ground.__init__` checks
    # for a zero norm, and NaN's norm is NaN, and `nan == 0.0` is
    # False. So a NaN ground IS installable through the public API, and
    # that is the attack.
    return np.full(D, np.nan)

def oversize_packet():
    v = np.zeros(D); v[2] = 1.0
    return v * 100.0

def zero_packet():
    return np.zeros(D)

def orthogonal_packet():
    v = np.zeros(D); v[0] = 1.0; v[1] = -1.0
    return v / np.linalg.norm(v)

def huge_packet():
    v = np.zeros(D); v[2] = 1.0
    return v * 1e18

attacks = [
    ('nan_component', nan_packet(), 'psi_0'),
    ('inf_component', inf_packet(), 'psi_0'),
    ('all_nan', all_nan_packet(), 'psi_0'),
    ('nan_ground', nan_psi0_packet(), 'nan'),
    ('oversize', oversize_packet(), 'psi_0'),
    ('zero', zero_packet(), 'psi_0'),
    ('orthogonal', orthogonal_packet(), 'psi_0'),
    ('huge', huge_packet(), 'psi_0'),
]

results = []
for name, packet, kind in attacks:
    if kind == 'nan':
        # The ground is poisoned THROUGH THE PUBLIC CONSTRUCTOR. The
        # read-only `psi_0` property cannot be assigned, so a fresh
        # Ground is built instead.
        #
        # AND THE GROUND NOW REFUSES IT. `Ground.__init__` checks
        # finiteness, so the construction RAISES. The attack is
        # therefore refused AT THE DOOR rather than at the gate --
        # which is the better place for it to be refused, and the
        # reason is recorded as the exception's own text.
        try:
            Ground(packet)
            raise AssertionError('the Ground constructor accepted a '
                                 'non-finite ground; the attack succeeded')
        except ValueError as exc:
            results.append({
                'name': name,
                'allowed': False,
                'reason': 'refused at construction: %s' % str(exc)[:160],
                'drift_before': None,
                'drift_after': None,
                'state_finite': True,
            })
            continue
    s = fresh()
    probe_packet = packet
    drift_before = s.drift()
    try:
        rec = s.observe(probe_packet)
        allow = bool(rec.get('allow'))
        reason = str(rec.get('reason'))
    except Exception as exc:
        allow = False
        reason = 'EXCEPTION %s: %s' % (type(exc).__name__, exc)
    drift_after = s.drift()
    finite = bool(np.all(np.isfinite(s.psi_current)))
    results.append({
        'name': name,
        'allowed': allow,
        'reason': reason,
        'drift_before': float(drift_before) if np.isfinite(drift_before) else None,
        'drift_after': float(drift_after) if np.isfinite(drift_after) else None,
        'state_finite': finite,
    })

print(json.dumps({'attacks': results}))
"""


#: A3 -- do all the gate copies agree, on the adversarial inputs?
#:
#: This is the check that finds a split policy. It imports each copy and
#: asks each one the SAME adversarial questions, and compares the
#: BOOLEAN verdicts. The reason strings differ -- the copies spell ALLOW
#: three different ways -- but the behaviour must not.
PROBE_GATE_COPIES = r"""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.expanduser("~"), "AppData", "Local",
                                "hermes", "work_repos", "fieldcore", "src"))
sys.path.insert(0, os.path.join(os.path.expanduser("~"), "AppData", "Local",
                                "hermes", "work_repos", "simself", "src"))
sys.path.insert(0, os.path.join(os.path.expanduser("~"), "AppData", "Local",
                                "hermes", "work_repos", "fieldcore",
                                "src", "tiniest_core"))
import numpy as np

import gate as canonical

# the copies. Each is (name, callable(emb, psi0) -> (allow, reason)).
copies = []

copies.append(('fieldcore/src/gate.py', lambda e, p: canonical.gate(e, p)))

try:
    import tiniest_core as tc
    copies.append(('fieldcore/src/tiniest_core/tiniest_core.py',
                   lambda e, p: (lambda r: (r[0], r[1].value))(tc.gate(e, p))))
except Exception as exc:
    copies.append(('fieldcore/src/tiniest_core/tiniest_core.py',
                   None, 'import failed: %s' % exc))

try:
    from harness import gate as hg
    copies.append(('simself/src/harness/gate.py',
                   lambda e, p: hg.gate_packet(e, p)))
except Exception as exc:
    copies.append(('simself/src/harness/gate.py',
                   None, 'import failed: %s' % exc))

try:
    from constitutional import simself as ss
    copies.append(('simself/src/constitutional/simself.py',
                   lambda e, p: ss._gate(e, p)))
except Exception as exc:
    copies.append(('simself/src/constitutional/simself.py',
                   None, 'import failed: %s' % exc))

try:
    from constitutional import dreaming as dm
    copies.append(('simself/src/constitutional/dreaming.py',
                   lambda e, p: dm.gate_packet(e, p)))
except Exception as exc:
    copies.append(('simself/src/constitutional/dreaming.py',
                   None, 'import failed: %s' % exc))

psi0 = np.zeros(8); psi0[0] = 1.0

# the adversarial inputs. Each one is a case where the copies have
# historically disagreed.
cases = {
    'good': np.array([1.0, 0, 0, 0, 0, 0, 0, 0]),
    'orthogonal': np.array([0.0, 1.0, 0, 0, 0, 0, 0, 0]),
    'oversize': np.array([100.0, 0, 0, 0, 0, 0, 0, 0]),
    'zero': np.zeros(8),
    'all_nan': np.full(8, np.nan),
    'nan_component': np.array([np.nan, 1.0, 0, 0, 0, 0, 0, 0]),
    'all_inf': np.full(8, np.inf),
}

rows = []
for name, fn, *rest in copies:
    if fn is None:
        rows.append({'copy': name, 'error': rest[0]})
        continue
    verdicts = {}
    for case, emb in cases.items():
        try:
            allow, reason = fn(emb, psi0)
            verdicts[case] = bool(allow)
        except Exception as exc:
            verdicts[case] = 'EXCEPTION %s' % type(exc).__name__
    rows.append({'copy': name, 'verdicts': verdicts})

print(json.dumps({'rows': rows}))
"""


def check_adversarial() -> AreaResult:
    """AREA 13 -- adversarial.

    Three items, all binary, all measured:

      A1  every crafted attack is REFUSED, and the refusal names a reason
      A2  a refused attack leaves the state INTACT and finite
      A3  every gate copy in both repos agrees with the canonical gate
          on the adversarial inputs -- one policy, not five
    """
    measured: Dict[str, Any] = {}
    parts: List[str] = []

    # ---- A1 + A2: the attacks -----------------------------------------
    ok, data, err = _run(PROBE_ATTACKS)
    if not ok:
        return AreaResult(
            number=13, name="adversarial", status=Status.SKIP,
            detail="the attack probe could not run: %s" % err,
            does_not_establish=(
                "that any attack is refused -- the probe did not run"),
            measured=measured,
        )

    attacks = data["attacks"]
    measured["attacks_run"] = len(attacks)
    admitted = [a for a in attacks if a["allowed"]]
    nameless = [a for a in attacks
                if not a["allowed"] and not a["reason"].strip()]
    corrupted = [a for a in attacks if not a["state_finite"]]

    measured["admitted"] = len(admitted)
    measured["nameless_refusals"] = len(nameless)
    measured["corrupted_states"] = len(corrupted)
    measured["attack_names"] = [a["name"] for a in attacks]

    if admitted:
        return AreaResult(
            number=13, name="adversarial", status=Status.FAIL,
            detail="%d of %d crafted attacks were ADMITTED: %s. A gate that "
                   "admits a packet it was built to refuse is not a gate."
                   % (len(admitted), len(attacks),
                      [a["name"] for a in admitted]),
            does_not_establish=(
                "that the substrate is secure against anything not on this list"),
            measured=measured,
        )
    parts.append("A1: all %d crafted attacks refused" % len(attacks))

    if nameless:
        return AreaResult(
            number=13, name="adversarial", status=Status.FAIL,
            detail="%d refusal(s) named no reason: %s. A refusal that cannot "
                   "say why cannot be learned from."
                   % (len(nameless), [a["name"] for a in nameless]),
            does_not_establish="that the refusals are attributable",
            measured=measured,
        )
    parts.append("A1: every refusal names its reason")

    if corrupted:
        return AreaResult(
            number=13, name="adversarial", status=Status.FAIL,
            detail="%d attack(s) left the state NON-FINITE: %s. An attack "
                   "that is refused but still corrupts the state is not "
                   "refused."
                   % (len(corrupted), [a["name"] for a in corrupted]),
            does_not_establish="that a refusal leaves the state intact",
            measured=measured,
        )
    parts.append("A2: every refused attack left the state finite and intact")

    # ---- A3: the copies agree ------------------------------------------
    ok3, cdata, err3 = _run(PROBE_GATE_COPIES)
    if not ok3:
        return AreaResult(
            number=13, name="adversarial", status=Status.SKIP,
            detail="; ".join(parts) + "; the gate-copies probe could not run: "
                   "%s" % err3,
            does_not_establish=(
                "that the gate copies agree -- the probe did not run"),
            measured=measured,
        )

    rows = cdata["rows"]
    measured["gate_copies"] = len(rows)
    canonical_row = next((r for r in rows
                          if r["copy"] == "fieldcore/src/gate.py"), None)
    if canonical_row is None or "verdicts" not in canonical_row:
        return AreaResult(
            number=13, name="adversarial", status=Status.SKIP,
            detail="; ".join(parts) + "; the canonical gate was not among "
                   "the copies that could be loaded",
            does_not_establish="that the gate copies agree",
            measured=measured,
        )

    split: List[Dict[str, Any]] = []
    broken: List[str] = []
    for row in rows:
        if "verdicts" not in row:
            broken.append("%s: %s" % (row["copy"], row.get("error", "?")))
            continue
        for case, verdict in row["verdicts"].items():
            want = canonical_row["verdicts"].get(case)
            if verdict != want:
                split.append({"copy": row["copy"], "case": case,
                              "copy_says": verdict, "canonical_says": want})
    measured["policy_splits"] = len(split)
    measured["unloadable_copies"] = broken

    if broken:
        return AreaResult(
            number=13, name="adversarial", status=Status.FAIL,
            detail="; ".join(parts) + "; %d gate copy/copies could not even "
                   "be loaded: %s" % (len(broken), broken),
            does_not_establish="that there is one gate policy",
            measured=measured,
        )
    if split:
        return AreaResult(
            number=13, name="adversarial", status=Status.FAIL,
            detail="; ".join(parts) + "; the gate policy has SPLIT: %d "
                   "verdict(s) differ from the canonical gate: %s"
                   % (len(split), split[:4]),
            does_not_establish=(
                "that there is one gate policy. The copies disagree on the "
                "adversarial inputs, which is exactly where a split "
                "policy is exploited."),
            measured=measured,
        )
    parts.append("A3: all %d gate copies agree with the canonical gate on "
                 "every adversarial input" % len(rows))

    return AreaResult(
        number=13, name="adversarial", status=Status.PASS,
        detail="; ".join(parts),
        does_not_establish=(
            "that the substrate is SECURE. It establishes that the %d "
            "crafted attacks this area names are refused, that each refusal "
            "leaves the state intact, and that the %d gate copies in both "
            "repos are one policy on the adversarial inputs. An attack not "
            "on this list is not covered."
            % (len(attacks), len(rows))),
        measured=measured,
    )


def _main(argv: List[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    r = check_adversarial()
    print("=" * 70)
    print("AREA 13 adversarial: %s" % r.status.value)
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
