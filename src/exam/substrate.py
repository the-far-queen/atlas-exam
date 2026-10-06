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
s = SimSelf(constitution=c, ground=Ground(c.psi_0.copy()), R=3.0, eta=0.1)
ok = np.zeros(16); ok[0], ok[1] = 0.8, 0.6          # cos 0.8, |x| 1
orth = np.zeros(16); orth[3] = 1.0                   # cos ~0
far = np.zeros(16); far[4] = 5.0                     # |x| 5
before = s.psi_current.copy()
allow_ok = s.observe(ok)["allow"]
r_orth = s.observe(orth)
r_far = s.observe(far)
r_zero = s.observe(np.zeros(16))
inert = bool(np.allclose(before, s.psi_current) or s.drift() > 0)
print(json.dumps({
  "accepts_coherent": allow_ok,
  "refuses_orthogonal": not r_orth["allow"],
  "refuses_oversize": not r_far["allow"],
  "refuses_zero": not r_zero["allow"],
  "reasons_present": all(r.get("reason") for r in (r_orth, r_far, r_zero)),
}))
"""

PROBE_RETURN = r"""
import json, numpy as np
from constitutional.constitution import Constitution
from constitutional.ground import Ground
from constitutional.simself import SimSelf

c = Constitution()
s = SimSelf(constitution=c, ground=Ground(c.psi_0.copy()), R=3.0, eta=0.1)

# FIRST ATTEMPT used a random gaussian. The gate refused it -- cos to
# the ground was below 0.4 -- so drift stayed at exactly 0.0 and the
# probe reported d0=0.0, d20=0.0, rel_error=0.0, which reads as a PERFECT
# result. A probe that measures nothing must not look like one that
# measured success.

# Build a vector the gate will ACCEPT: mostly along the ground.
rng = np.random.default_rng(3)
x = 0.9 * np.zeros(16); x[0] = 1.0
x[1:] = 0.25 * rng.normal(size=15)
x = x / np.linalg.norm(x)

accepted = sum(1 for _ in range(30) if s.observe(x)["allow"])
d0 = s.drift()
for _ in range(20):
    s.tick()
d1 = s.drift()
pred = d0 * (1 - 0.1) ** 20
rel = abs(d1 - pred) / pred if pred > 0 else None
print(json.dumps({
    "accepted": accepted,
    "d0": d0,
    "d20": d1,
    "predicted": pred,
    "rel_error": rel,
    "contracts": bool(d1 < d0),
    # explicit: if nothing moved, this probe measured NOTHING
    "measured_anything": bool(d0 > 1e-6),
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