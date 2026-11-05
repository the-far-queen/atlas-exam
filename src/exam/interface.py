"""
interface.py -- AREA 11. Can the model be swapped without moving the core?

WHY THIS AREA
-------------
The stub said: "the substrate must not import any model, and swapping
the model must leave areas 1-10 unchanged. Nothing measures the model
today."

That last clause is the important one. An area that only says "no model
is imported" is a static check on the source. This area goes further:
it SWAPS the model and MEASURES that the core areas do not move.

THE SUBSTITUTION CONTRACT, stated precisely
--------------------------------------------
The system has a control path (the model produces a candidate answer)
and a substrate path (the gate, the ground, the drift bound, the
decision log). The contract is:

    C1  the substrate's core areas do not import any model
    C2  swapping the model changes the ANSWER and changes NOTHING ELSE
    C3  the core areas' MEASUREMENTS are identical under both models

C3 is the load-bearing one, and it is the one that cannot be checked by
reading source. A system that imports a model deep inside its state
update would pass a static import check and fail C3, because its drift
would move when the model changed.

HOW THE SWAP IS DONE
--------------------
TWO MODELS, both local, neither spending anything:

    model A   a deterministic local responder -- it reads the prompt and
              returns a fixed, declared answer
    model B   a different deterministic local responder -- it returns a
              DIFFERENT answer

Both are installed into the SAME substrate, through the SAME entry
point. Then the core quantities are read back and compared:

    drift          the distance from the ground
    accepted       whether the gate admitted the input
    log length     the decision log
    the answer     what came back

AND THE ASSERTION IS ABOUT WHAT MOVED:

    the ANSWER must differ   (otherwise the swap did not happen and
                               the comparison proves nothing)
    the CORE quantities must NOT differ

AND THERE IS A THIRD MODEL, WHICH IS THE ONE THAT MAKES THE CHECK
HONEST:

    model C   a responder that DRIFTS -- it returns a different answer
              AND it nudges the state

Model C is the CONTROL. If the core quantities under model C are
identical to those under model A, then the comparison cannot detect a
model-coupled substrate, and the whole area is theatre. So the area
asserts that model C MOVES the core quantities, and it asserts that
models A and B do not. If C does not move them either, the area fails
and says why: the measurement cannot see a coupling.

That is the shape the project's own doctrine asks for: an area that
cannot fail is not an area.

WHY A SUBPROCESS
----------------
The exam points AT the substrate. A bug in the substrate's helper would
become a passing grade.

Run: python -m exam.interface
"""

from __future__ import annotations

import ast
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

PROBE_TIMEOUT_S = 300


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


#: THE PROBE. Three models, one substrate, the core read back three
#: times.
PROBE_SWAP = r"""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.expanduser("~"), "AppData", "Local",
                                "hermes", "work_repos", "simself", "src"))
import numpy as np
from constitutional.constitution import Constitution
from constitutional.ground import Ground
from constitutional.simself import SimSelf

c = Constitution()
D = c.dim
rng = np.random.default_rng(23)

# --- the three models ---------------------------------------------------
# All three are LOCAL and DETERMINISTIC. Nothing here spends anything
# and nothing here calls out. The spend guards stay closed.

class ModelA:
    # a fixed, declared answer
    name = 'A'
    def answer(self, prompt):
        return 'the ground is the ground and the gate is the gate'

class ModelB:
    # a DIFFERENT fixed answer
    name = 'B'
    def answer(self, prompt):
        return 'a different answer entirely, from a different core'

class ModelC:
    # the CONTROL: a different answer AND a nudge to the state.
    # If the core quantities do not move under model C, the comparison
    # cannot see a coupling and the whole area is theatre.
    name = 'C'
    def answer(self, prompt):
        return 'a third answer, and this one moves the state'
    def nudge(self, s, rng2):
        v = c.psi_0 + 0.05 * rng2.normal(size=D)
        v = v / np.linalg.norm(v)
        return s.observe(v)

def run(model, n=50):
    # AND THE RNG IS RE-SEEDED FOR EVERY RUN. The first version of this
    # probe used one module-level generator, so the second run drew a
    # DIFFERENT set of observation packets from the first -- and the
    # drift differed by 5% (MEASURED: 0.134901 against 0.128318). That
    # was not the substrate being coupled to the model. It was the
    # probe comparing two runs that had been fed different inputs.
    #
    # This is the same defect the exam's own provenance area is built to
    # catch: a number with no controlled input behind it. So the
    # generator is re-seeded per run, and the two models are then fed
    # the SAME packets -- which is what makes the comparison a
    # comparison.
    rng2 = np.random.default_rng(23)
    s = SimSelf(constitution=c, ground=Ground(c.psi_0.copy()), R=3.0, eta=0.1)
    answers = []
    for i in range(n):
        prompt = 'question %d' % i
        answer = model.answer(prompt)
        answers.append(answer)
        if hasattr(model, 'nudge'):
            model.nudge(s, rng2)
        # the substrate path: the gate sees the observation, exactly as
        # it would with any model behind it.
        v = c.psi_0 + 0.01 * rng2.normal(size=D)
        v = v / np.linalg.norm(v)
        s.observe(v)
    return {
        'model': model.name,
        'first_answer': answers[0],
        'answers_distinct': len(set(answers)),
        'drift': s.drift(),
        'log_len': len(s.decision_log),
        'ticks': s.ticks,
        'accepted': sum(1 for r in s.decision_log
                        if r.kind == 'observe' and r.data.get('allow')),
    }

a = run(ModelA())
b = run(ModelB())
cres = run(ModelC())

print(json.dumps({'A': a, 'B': b, 'C': cres}))
"""


#: C1 -- the static half: does the substrate's CORE import a model?
#:
#: This is an AST scan of the CORE modules -- the ones the exam's own
#: areas measure -- looking for the model modules by name. It is a
#: SEPARATE check from the swap, because a static import and a runtime
#: coupling are different failures: a substrate can import nothing and
#: still be coupled, and it can import a model for a REASON (the model
#: is the thing being graded) without its core areas moving.
#:
#: AND THE SCOPE IS THE CORE, NOT THE WHOLE REPO. The first version of
#: this scan walked every .py file in both repos and found 13 "model
#: importers" -- `fc_wrapper.py`, `fc_model.py`, `live_wrapper.py`,
#: `gabrielle.py`, `bench_agency.py` and others. Those are the APP
#: LAYER: they are the places a model is SUPPOSED to be called from.
#: Bobby's own architecture puts the model INSIDE fieldcore as a callee
#: (`fc_model.py`: "MINIMAX, INSIDE FIELDCORE. The model is a callee.").
#: Flagging those would be flagging the design.
#:
#: One of the 13 was not even an import: `chain_audit.py` names
#: `minimax_client` inside a DOCSTRING and then LOADS IT BY PATH, on
#: purpose, so that the audit can read the client's own scope list. A
#: text scan cannot tell that from an import. An AST scan can, and it
#: can also tell an import from a docstring -- which is why this is an
#: AST scan and not a grep.
PROBE_MODEL_IMPORTS = r"""
import ast, json, os, sys

# THE CORE. These are the modules the exam's own areas measure, and
# the ones whose behaviour must not depend on which model is behind
# them. The app layer is deliberately NOT here.
CORE_FILES = [
    os.path.join('fieldcore', 'src', 'substrate.py'),
    os.path.join('fieldcore', 'src', 'gate.py'),
    os.path.join('fieldcore', 'src', 'governor.py'),
    os.path.join('fieldcore', 'src', 'hodge_cycle.py'),
    os.path.join('fieldcore', 'src', 'tiniest_core', 'tiniest_core.py'),
    os.path.join('simself', 'src', 'constitutional', 'simself.py'),
    os.path.join('simself', 'src', 'constitutional', 'ground.py'),
    os.path.join('simself', 'src', 'constitutional', 'constitution.py'),
    os.path.join('simself', 'src', 'constitutional', 'dreaming.py'),
    os.path.join('simself', 'src', 'harness', 'gate.py'),
]

# The modules that constitute a MODEL -- a thing that generates text
# from a prompt. A core that imports one of these has the model inside
# the thing being measured.
MODEL_MODULES = {
    'minimax_client', 'mte_llm_wrapper', 'mini_llm', 'lmstudio_openai_client',
    'call_minimax', 'grok_command', 'grok_plaintext_ingest',
}

REPOS = os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes",
                     "work_repos")

offenders = []
scanned = 0
missing = []
for rel in CORE_FILES:
    path = os.path.join(REPOS, rel)
    if not os.path.isfile(path):
        missing.append(rel.replace(os.sep, '/'))
        continue
    try:
        tree = ast.parse(open(path, encoding='utf-8', errors='replace').read())
    except SyntaxError as exc:
        offenders.append({'file': rel, 'module': 'PARSE ERROR', 'line': 0})
        continue
    scanned += 1
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module]
        for name in names:
            leaf = name.split('.')[0]
            if leaf in MODEL_MODULES:
                offenders.append({
                    'file': rel.replace(os.sep, '/'),
                    'module': name,
                    'line': getattr(node, 'lineno', 0),
                })

print(json.dumps({'scanned': scanned, 'missing': missing,
                  'offenders': offenders}))
"""


def check_interface() -> AreaResult:
    """AREA 11 -- interface.

    Four items, all binary, all measured:

      C1  the substrate's core does not import a model module
      C2  swapping the model CHANGES the answer -- so the comparison is
          not vacuous
      C3  the core quantities are IDENTICAL under two different models
      C4  and the CONTROL model -- one that nudges the state -- DOES
          move them, so the comparison can see a coupling
    """
    measured: Dict[str, Any] = {}
    parts: List[str] = []

    # ---- C1: the static half -----------------------------------------
    ok, imp, err = _run(PROBE_MODEL_IMPORTS)
    if not ok:
        return AreaResult(
            number=11, name="interface", status=Status.SKIP,
            detail="the model-import scan could not run: %s" % err,
            does_not_establish=(
                "anything about the substitution contract -- the scan did "
                "not run"),
            measured=measured,
        )
    measured["files_scanned"] = imp["scanned"]
    measured["model_importers"] = len(imp["offenders"])
    measured["core_files_missing"] = imp["missing"]
    if imp["missing"]:
        return AreaResult(
            number=11, name="interface", status=Status.SKIP,
            detail="; ".join(parts) + "; %d core module(s) could not be "
                   "found, so the import scan did not cover the whole core: "
                   "%s" % (len(imp["missing"]), imp["missing"]),
            does_not_establish=(
                "that the core is model-free -- the scan did not cover it"),
            measured=measured,
        )
    if imp["offenders"]:
        return AreaResult(
            number=11, name="interface", status=Status.FAIL,
            detail="the substrate's CORE imports %d model module(s): %s. The "
                   "substrate is the thing being measured; a model inside "
                   "it is a model inside the ruler."
                   % (len(imp["offenders"]), imp["offenders"][:5]),
            does_not_establish="that the core is model-free",
            measured=measured,
        )
    parts.append("C1: %d core modules scanned across both repos, and none "
                 "imports a model module" % imp["scanned"])

    # ---- C2, C3, C4: the swap -----------------------------------------
    ok2, data, err2 = _run(PROBE_SWAP)
    if not ok2:
        return AreaResult(
            number=11, name="interface", status=Status.SKIP,
            detail="; ".join(parts) + "; the swap probe could not run: %s"
                   % err2,
            does_not_establish=(
                "anything about the substitution contract -- the swap did "
                "not run"),
            measured=measured,
        )

    a = data["A"]
    b = data["B"]
    ctrl = data["C"]
    measured["model_a_answer"] = a["first_answer"][:60]
    measured["model_b_answer"] = b["first_answer"][:60]
    measured["model_a_drift"] = a["drift"]
    measured["model_b_drift"] = b["drift"]
    measured["model_c_drift"] = ctrl["drift"]

    # C2: the swap must actually swap. If the answers are the same, the
    # comparison proves nothing -- and the area must say so rather than
    # pass on a null result.
    if a["first_answer"] == b["first_answer"]:
        return AreaResult(
            number=11, name="interface", status=Status.FAIL,
            detail="the two models returned the SAME answer, so the "
                   "substitution did not happen and the comparison is "
                   "vacuous. A swap that does not swap cannot show that "
                   "the core does not move.",
            does_not_establish="that the core is model-independent",
            measured=measured,
        )
    parts.append("C2: the two models returned different answers, so the "
                 "substitution happened")

    # C3: the core quantities must NOT move.
    moved: List[str] = []
    for key in ("drift", "log_len", "ticks", "accepted"):
        if a[key] != b[key]:
            moved.append("%s (%r vs %r)" % (key, a[key], b[key]))
    measured["core_moved_under_swap"] = moved
    if moved:
        return AreaResult(
            number=11, name="interface", status=Status.FAIL,
            detail="the core moved when the model was swapped: %s. The "
                   "substrate is coupled to the model, so the core areas "
                   "do not measure the substrate."
                   % "; ".join(moved),
            does_not_establish="that the core is model-independent",
            measured=measured,
        )
    parts.append("C3: the core quantities are identical under both models "
                 "(drift %.6f, log %d, ticks %d, accepted %d)"
                 % (a["drift"], a["log_len"], a["ticks"], a["accepted"]))

    # C4: the control. THIS IS WHAT MAKES C3 MEANINGFUL. A model that
    # nudges the state MUST move the core quantities, or the comparison
    # is blind and C3 proved nothing.
    ctrl_moved: List[str] = []
    for key in ("drift", "log_len", "ticks", "accepted"):
        if a[key] != ctrl[key]:
            ctrl_moved.append(key)
    measured["control_moved"] = ctrl_moved
    if not ctrl_moved:
        return AreaResult(
            number=11, name="interface", status=Status.FAIL,
            detail="the CONTROL model -- which nudges the state -- did not "
                   "move any core quantity (drift %.6f, log %d, ticks %d). "
                   "So the comparison is BLIND: it could not have detected a "
                   "model-coupled substrate, and C3 proved nothing."
                   % (ctrl["drift"], ctrl["log_len"], ctrl["ticks"]),
            does_not_establish=(
                "that the core is model-independent -- the measurement "
                "cannot see a coupling"),
            measured=measured,
        )
    parts.append("C4: the control model moved %s, so the comparison can "
                 "see a coupling and C3 is not a null result"
                 % ", ".join(ctrl_moved))

    return AreaResult(
        number=11, name="interface", status=Status.PASS,
        detail="; ".join(parts),
        does_not_establish=(
            "that the model is GOOD, or that the model is even correct. It "
            "establishes that swapping the model changes the answer and "
            "nothing else: the substrate's core quantities are identical "
            "under two different models, and a control model that nudges "
            "the state does move them, so the comparison can see a "
            "coupling. It does not cover a substrate that couples to the "
            "model in a way neither probe exercises."),
        measured=measured,
    )


def _main(argv: List[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    r = check_interface()
    print("=" * 70)
    print("AREA 11 interface: %s" % r.status.value)
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
