"""
substrate.py — the ONLY place this exam touches the thing it grades.

DESIGN CONSTRAINT, NON-NEGOTIABLE
---------------------------------
Every call into fieldcore or simself goes through a SUBPROCESS. If the
exam imported their helpers directly, a bug in a helper would become a
passing grade rather than a failure -- which is how v2 scored itself.

Concretely: if `Ground` were broken so that psi_0 silently changed,
then an in-process import would report "identity OK" using the broken
ground it just read. Through a subprocess, the same breakage produces
an error or a wrong number, and the area fails.

The probe scripts below are written to FAIL LOUDLY. They never catch an
exception and return a passing value.

Run: python -m exam.substrate --probe identity
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


HERMES = os.path.expanduser("~/AppData/Local/hermes")
WORK_REPOS = os.path.join(HERMES, "work_repos")
SIMSELF_SRC = os.path.join(WORK_REPOS, "simself", "src")
FIELDCORE_SRC = os.path.join(WORK_REPOS, "fieldcore", "src")

# how long a probe may take before it is declared unresponsive rather
# than slow. A hung substrate is a FAIL, not a wait.
PROBE_TIMEOUT_S = 180


def substrate_present() -> Dict[str, bool]:
    return {
        "simself": os.path.isdir(SIMSELF_SRC),
        "fieldcore": os.path.isdir(FIELDCORE_SRC),
    }


def run_probe(name: str, code: str, timeout: int = PROBE_TIMEOUT_S
              ) -> Tuple[bool, Dict, str]:
    """run a probe in a fresh interpreter.

    Returns (ok, payload, error). `ok` False means the probe failed or
    could not run -- never a silent pass.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [SIMSELF_SRC, FIELDCORE_SRC, env.get("PYTHONPATH", "")]
    ).strip(os.pathsep)
    try:
        r = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, env=env, timeout=timeout,
        )
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


# ---------------------------------------------------------------------------
# THE PROBES. each prints exactly one line of JSON.
# ---------------------------------------------------------------------------

PROBE_IDENTITY = r"""
import json, numpy as np
import sys
from constitutional.constitution import Constitution
from constitutional.ground import Ground
from constitutional.simself import SimSelf

c = Constitution()
s = SimSelf(constitution=c, ground=Ground(c.psi_0.copy()), R=3.0, eta=0.1)
ground = s.psi0.copy()
rng = np.random.default_rng(2)
worst = 0.0
for _ in range(300):
    v = rng.normal(size=s.dim); v /= np.linalg.norm(v)
    s.observe(v * 2.0)
    s.tick()
    worst = max(worst, float(np.max(np.abs(ground - s.psi0))))
worst2 = float(np.max(np.abs(ground - s.ground.psi_0)))
print(json.dumps({"max_change": max(worst, worst2),
                  "unit_norm": bool(abs(np.linalg.norm(ground) - 1.0) < 1e-9)}))
"""

PROBE_LIVENESS = r"""
import json, numpy as np
from constitutional.constitution import Constitution
from constitutional.ground import Ground
from constitutional.simself import SimSelf

c = Constitution()
s = SimSelf(constitution=c, ground=Ground(c.psi_0.copy()), R=3.0, eta=0.1)
rng = np.random.default_rng(5)
accepted, peak = 0, 0.0
for _ in range(200):
    v = rng.normal(size=s.dim); v /= np.linalg.norm(v)
    if s.observe(v * 2.0)["allow"]:
        accepted += 1
    peak = max(peak, s.drift())
print(json.dumps({"accepted": accepted, "peak_drift": peak,
                  "R": s.R, "moved": bool(peak > 1e-3)}))
"""

PROBE_BOUNDEDNESS = r"""
import json, numpy as np
from constitutional.constitution import Constitution
from constitutional.ground import Ground
from constitutional.simself import SimSelf

c = Constitution()
s = SimSelf(constitution=c, ground=Ground(c.psi_0.copy()), R=3.0, eta=0.1)
rng = np.random.default_rng(7)
worst = 0.0
for _ in range(1000):
    v = rng.normal(size=s.dim); v /= np.linalg.norm(v)
    s.observe(v * 3.0)
    worst = max(worst, s.drift())
print(json.dumps({"max_drift": worst, "R": s.R,
                  "inside": bool(worst <= s.R + 1e-9)}))
"""

PROBE_REFUSAL = r"""
import json, numpy as np
from constitutional.constitution import Constitution
from constitutional.ground import Ground
from constitutional.simself import SimSelf

c = Constitution()

# AND THE COHERENT PACKET IS BUILT FROM THE GROUND, NOT ASSUMED.
# The first version of this probe used a hardcoded vector:
#
#     ok = np.zeros(16); ok[0], ok[1] = 0.8, 0.6
#
# and asserted the gate would admit it. But the gate measures the
# cosine against psi_0, and psi_0 is DERIVED FROM TEXT -- it is not
# [1, 0, 0, ...]. MEASURED: cos(that hardcoded vector, psi_0) = 0.2597,
# which is BELOW the gate's floor of 0.4. So the gate refused it, and
# the area reported "accepts coherent input: False" -- a FAIL that
# looked exactly like a substrate defect.
#
# The lesson is the project's own: the probe's assumption about the
# ground was wrong, and the failure was attributed to the system under
# test. So the packet is now built FROM psi_0 -- the ground itself,
# with a little noise -- and the cosine is MEASURED and reported, so
# the probe cannot silently drift onto the wrong side of the floor
# again.
psi0 = c.psi_0
rng = np.random.default_rng(11)
ok = psi0 + 0.05 * rng.normal(size=len(psi0))
ok = ok / np.linalg.norm(ok)

orth = np.zeros(len(psi0)); orth[0] = 1.0        # orthogonal-ish
far = np.zeros(len(psi0)); far[2] = 5.0           # |x| 5 -> oversize

s = SimSelf(constitution=c, ground=Ground(psi0.copy()), R=3.0, eta=0.1)
before = s.psi_current.copy()
allow_ok = s.observe(ok)["allow"]
r_orth = s.observe(orth)
r_far = s.observe(far)
r_zero = s.observe(np.zeros(len(psi0)))
inert = bool(np.allclose(before, s.psi_current) or s.drift() > 0)
cos_ok = float(np.dot(ok, psi0) / (np.linalg.norm(ok) * np.linalg.norm(psi0)))
print(json.dumps({
  "accepts_coherent": allow_ok,
  "refuses_orthogonal": not r_orth["allow"],
  "refuses_oversize": not r_far["allow"],
  "refuses_zero": not r_zero["allow"],
  "reasons_present": all(r.get("reason") for r in (r_orth, r_far, r_zero)),
  # AND THE MEASUREMENT THAT PROVES THE PACKET WAS COHERENT. If this
  # drops below the gate's floor the probe is wrong again, and the
  # area says so instead of blaming the substrate.
  "coherent_cosine": cos_ok,
}))
"""

PROBE_RETURN = r"""
import json, numpy as np
from constitutional.constitution import Constitution
from constitutional.ground import Ground
from constitutional.simself import SimSelf

c = Constitution()

# FIRST ATTEMPT used a random gaussian. The gate refused it -- cos to
# the ground was below 0.4 -- so drift stayed at exactly 0.0 and the
# probe reported d0=0.0, d20=0.0, rel_error=0.0, which reads as a PERFECT
# result. A probe that measures nothing must not look like one that
# measured success.
#
# SECOND ATTEMPT built a vector around axis 0:
#
#     x = 0.9 * np.zeros(16); x[0] = 1.0
#     x[1:] = 0.25 * rng.normal(size=15)
#
# which is the same mistake as the refusal probe's: it ASSUMED psi_0
# was aligned with axis 0. It is not -- psi_0 is derived from text.
# MEASURED: that vector's cosine against psi_0 was 0.2597, below the
# gate's floor, so it was refused too, and the area reported "PROBE
# MEASURED NOTHING" -- the correct verdict about a probe that had
# measured nothing, and the WRONG verdict about a substrate that was
# fine.
#
# THIRD ATTEMPT: build the packet FROM psi_0, and MEASURE the cosine
# so the probe cannot drift onto the wrong side of the floor again.
psi0 = c.psi_0
rng = np.random.default_rng(3)
x = psi0 + 0.05 * rng.normal(size=len(psi0))
x = x / np.linalg.norm(x)

s = SimSelf(constitution=c, ground=Ground(psi0.copy()), R=3.0, eta=0.1)

accepted = sum(1 for _ in range(30) if s.observe(x)["allow"])
d0 = s.drift()
for _ in range(20):
    s.tick()
d1 = s.drift()
pred = d0 * (1 - 0.1) ** 20
rel = abs(d1 - pred) / pred if pred > 0 else None
cos_x = float(np.dot(x, psi0) / (np.linalg.norm(x) * np.linalg.norm(psi0)))
print(json.dumps({
    "accepted": accepted,
    "d0": d0,
    "d20": d1,
    "predicted": pred,
    "rel_error": rel,
    "contracts": bool(d1 < d0),
    # explicit: if nothing moved, this probe measured NOTHING
    "measured_anything": bool(d0 > 1e-6),
    # the coherence of the packet, measured. If this falls below the
    # gate's floor the probe is wrong again.
    "coherent_cosine": cos_x,
}))
"""


PROBES = {
    "identity": PROBE_IDENTITY,
    "liveness": PROBE_LIVENESS,
    "boundedness": PROBE_BOUNDEDNESS,
    "refusal": PROBE_REFUSAL,
    "return": PROBE_RETURN,
}


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "liveness"
    ok, payload, err = run_probe(name, PROBES[name])
    print(json.dumps({"ok": ok, "payload": payload, "error": err}, indent=2))
    sys.exit(0 if ok else 1)