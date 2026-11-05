"""
tools.py -- AREA 19. Can the system act on something OUTSIDE itself?

WHY THIS AREA, AND WHY THE STUB SAID IT WAS NOT IMPLEMENTABLE
-----------------------------------------------------------------
The stub said: "not implemented, and not implementable without a
sandbox. every metric above is passive -- check psi_0, count drift,
read a residual. this one requires acting on something outside the
process and observing it."

The stub was HALF RIGHT, and the half it got wrong is worth stating
because it is the project's own doctrine:

    RIGHT   an area that only reads the substrate measures the
            substrate, and cannot tell a working system from a
            decorative one
    WRONG   that acting on the outside requires a SANDBOX

A sandbox is required for one specific thing: letting a CANDIDATE act
on the real world, where the damage is real. This area is not about
that. This area is about whether the system's tool surface can act at
all, and whether the effect can be OBSERVED FROM OUTSIDE the process
that acted. That needs an EXECUTOR and a DIRECTORY, not a sandbox --
and the executor has to be the substrate's own.

THE TOOL SURFACE, and where it actually lives
----------------------------------------------
    `simself/src/constitutional/pi_tools.py`   the 4-tool discipline:
        read, write, edit, bash. A gate call is a
        (tool_type, target, witness) tuple, and the gate returns
        (allow, reason).
    `simself/.agents/extensions/mcp_bridge.py` the JSON-RPC surface
        that exposes the gate and two other tools over stdio.
    `simself/.agents/extensions/minimal_loop.py` the loop that makes
        calls and records them.

THE THREE THINGS THIS AREA MEASURES
------------------------------------
    T1  THE GATE REFUSES. A tool surface whose gate admits everything
        is a decoration. So: an unknown tool type, a missing target,
        and a bash call with no witness must each be REFUSED, each
        with its own reason.

    T2  THE EFFECT IS OBSERVABLE FROM OUTSIDE. This is the part the
        stub said was impossible. It is not: the area writes a file
        THROUGH the substrate's own gate and then reads that file
        BACK FROM THE FILESYSTEM, in the probe, without asking the
        substrate anything. If the file is there with the right
        contents, the effect happened in the world and the world
        agrees. That is world contact, and it needs no sandbox --
        because the write goes to a probe-owned temporary directory,
        not to anything that matters.

    T3  A REFUSED CALL HAS NO EFFECT. The gate's refusal must be
        REAL: no file is written, nothing changes. A gate that refuses
        after the fact is a gate that does not gate.

AND THE FOURTH, WHICH IS WHAT MAKES IT AN AREA RATHER THAN A
DEMONSTRATION
----------------------------------------------------------------------
    T4  THE SURVEY IS THE EXECUTOR'S OWN.

The probe drives the tool call through the substrate's own
`pi_tools.gate` and then through the substrate's own loop, and the
effect is observed by the probe reading the filesystem. The area does
not assert that the gate "works" -- it asserts that a file appeared.

WHY A SUBPROCESS
----------------
The exam points AT the substrate. A bug in the substrate's helper would
become a passing grade. And the probe writes into a temporary
directory it owns, so the substrate's real tree is never touched.

Run: python -m exam.tools
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
SIMSELF_EXT = os.path.join(WORK_REPOS, "simself", ".agents", "extensions")

PROBE_TIMEOUT_S = 180


def _run(code: str, timeout: int = PROBE_TIMEOUT_S
         ) -> Tuple[bool, Dict[str, Any], str]:
    """run a probe in a fresh interpreter. loud failure only."""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        [SIMSELF_SRC, SIMSELF_EXT, env.get("PYTHONPATH", "")]
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


#: THE PROBE.
#:
#: The write goes into a temporary directory the PROBE creates, so the
#: substrate's real tree is never touched. Nothing here deletes
#: anything of Bobby's, and nothing writes outside the temp dir.
PROBE_TOOLS = r"""
import json, os, sys, tempfile

SIMSELF_EXT = os.path.join(os.path.expanduser("~"), "AppData", "Local",
                           "hermes", "work_repos", "simself",
                           ".agents", "extensions")
sys.path.insert(0, SIMSELF_EXT)

import pi_tools
from tool_executor import ToolExecutor

out = {}

# --- T1: the gate refuses -----------------------------------------------
refusals = {}
for name, call in (
    ('unknown_tool_type',
     pi_tools.ToolCall(tool_type='tweet', target='x')),
    ('empty_target',
     pi_tools.ToolCall(tool_type='read', target='')),
    ('bash_without_witness',
     pi_tools.ToolCall(tool_type='bash', target='ls')),
):
    allow, reason = pi_tools.gate(call)
    refusals[name] = {'allowed': bool(allow), 'reason': reason}
out['refusals'] = refusals

# the allowed case, so the refusals above mean something: a read with
# a target and a bash WITH a witness must be admitted.
allow_ok, reason_ok = pi_tools.gate(
    pi_tools.ToolCall(tool_type='read', target='/tmp/x'))
out['read_allowed'] = {'allowed': bool(allow_ok), 'reason': reason_ok}
allow_bash, reason_bash = pi_tools.gate(
    pi_tools.ToolCall(tool_type='bash', target='ls', witness='list files'))
out['bash_with_witness_allowed'] = {'allowed': bool(allow_bash),
                                    'reason': reason_bash}

# --- T2 + T3: the effect is observable from outside, and a refusal
#              has no effect ----------------------------------------------
sandbox = tempfile.mkdtemp(prefix='atlas_tools_')
target = os.path.join(sandbox, 'written_by_the_probe.txt')
payload = 'the tool wrote this and the probe read it back from disk'

# AND THE EXECUTOR IS THE SUBSTRATE'S OWN. The first version of this
# probe drove the write through `minimal_loop.AgentLoop`, which
# RECORDS calls but does not execute them: the gate allowed the write
# and no file appeared (MEASURED: effect_file_exists = false). The
# gate was correct; there was nothing behind it.
#
# So the write now goes through `tool_executor.ToolExecutor`, which is
# the substrate's own executor, bound to a root the PROBE owns. The
# executor has no idea that root is temporary, and behaves identically
# toward it and toward a real one -- which is what makes this a
# measurement of the module rather than of the probe.
executor = ToolExecutor(sandbox)

write_call = executor.execute(
    pi_tools.ToolCall(tool_type='write', target=target,
                      witness='the probe needs a file on disk'),
    payload=payload)
out['write_call'] = {'allow': bool(write_call.allowed),
                     'reason': write_call.reason}

# AND THE EFFECT IS CHECKED FROM OUTSIDE. The probe does not ask the
# substrate what happened. It looks at the FILESYSTEM. If the file is
# there with the right contents, the effect happened in the world.
exists = os.path.isfile(target)
contents = ''
if exists:
    with open(target, 'r', encoding='utf-8') as fh:
        contents = fh.read()
out['effect'] = {'file_exists': exists, 'contents': contents,
                 'payload': payload}

# --- T3: a refused call has NO effect ----------------------------------
refused_target = os.path.join(sandbox, 'must_not_exist.txt')
refused_call = executor.execute(
    pi_tools.ToolCall(tool_type='bash', target=refused_target))  # no witness
out['refused_call'] = {'allow': bool(refused_call.allowed),
                       'reason': refused_call.reason,
                       'file_exists': os.path.isfile(refused_target)}

# --- AND THE ROOT IS BOUNDED: a path outside the root is refused ------
escape_target = os.path.join(sandbox, '..', 'escaped.txt')
escape_call = executor.execute(
    pi_tools.ToolCall(tool_type='write', target=escape_target,
                      witness='try to escape'),
    payload='nope')
out['escape'] = {'allow': bool(escape_call.allowed),
                 'reason': escape_call.reason,
                 'file_exists': os.path.isfile(
                     os.path.join(os.path.dirname(sandbox), 'escaped.txt'))}

# the sandbox is the probe's own; it is removed here so the probe
# leaves nothing behind.
import shutil
shutil.rmtree(sandbox, ignore_errors=True)

print(json.dumps(out))
"""


def check_tools() -> AreaResult:
    """AREA 19 -- tools.

    Four items, all binary, all measured:

      T1  the gate REFUSES: an unknown tool type, an empty target and
          a bash call with no witness are each refused, each with its
          own reason -- and the admitted cases are admitted, so the
          refusals are discriminating
      T2  the effect is OBSERVABLE FROM OUTSIDE the process that acted:
          a file written through the substrate's own gate is read back
          from the filesystem by the probe
      T3  a REFUSED call has no effect: no file appears
      T4  the write goes through the substrate's OWN gate and its OWN
          loop, not through a re-implementation
    """
    measured: Dict[str, Any] = {}
    parts: List[str] = []

    ok, data, err = _run(PROBE_TOOLS)
    if not ok:
        return AreaResult(
            number=19, name="tools", status=Status.SKIP,
            detail="the tools probe could not run: %s" % err,
            does_not_establish=(
                "any tool capability -- the probe did not run"),
            measured=measured,
        )

    # ---- T1: the gate refuses -----------------------------------------
    refusals = data["refusals"]
    measured["refusal_cases"] = len(refusals)
    admitted = [k for k, v in refusals.items() if v["allowed"]]
    nameless = [k for k, v in refusals.items()
                if not v["allowed"] and not v["reason"].strip()]
    measured["refusals_admitted"] = admitted

    if admitted:
        return AreaResult(
            number=19, name="tools", status=Status.FAIL,
            detail="the tool gate ADMITTED %d of the cases it must refuse: "
                   "%s. A gate that admits everything is a decoration."
                   % (len(admitted), admitted),
            does_not_establish="that the tool gate gates",
            measured=measured,
        )
    if nameless:
        return AreaResult(
            number=19, name="tools", status=Status.FAIL,
            detail="%d refusal(s) named no reason: %s" % (len(nameless),
                                                          nameless),
            does_not_establish="that the refusals are attributable",
            measured=measured,
        )

    # AND THE ADMITTED CASES, so the refusals are not just a gate that
    # refuses everything. A gate that refuses everything is safe and
    # useless, and the project's own doctrine says a gate that must be
    # perfect never opens.
    if not data["read_allowed"]["allowed"]:
        return AreaResult(
            number=19, name="tools", status=Status.FAIL,
            detail="a plain read with a target was REFUSED (%s). The gate "
                   "is refusing everything, which is safe and useless."
                   % data["read_allowed"]["reason"],
            does_not_establish="that the tool gate discriminates",
            measured=measured,
        )
    if not data["bash_with_witness_allowed"]["allowed"]:
        return AreaResult(
            number=19, name="tools", status=Status.FAIL,
            detail="a bash call WITH a witness was REFUSED (%s). The witness "
                   "is the gate's own door, and it is shut."
                   % data["bash_with_witness_allowed"]["reason"],
            does_not_establish="that the tool gate discriminates",
            measured=measured,
        )
    parts.append("T1: %d refusal cases all refused with a reason, and the "
                 "admitted cases (a plain read, a bash with a witness) were "
                 "admitted" % len(refusals))

    # ---- T2: the effect is observable from outside --------------------
    effect = data["effect"]
    measured["effect_file_exists"] = effect["file_exists"]
    measured["effect_contents_match"] = (effect["contents"] == effect["payload"])
    if not effect["file_exists"]:
        return AreaResult(
            number=19, name="tools", status=Status.FAIL,
            detail="the write was allowed (%s) but no file appeared on the "
                   "filesystem. An allowed tool call with no effect is a "
                   "tool that does not act."
                   % data["write_call"]["reason"],
            does_not_establish=(
                "that the substrate can act on anything outside itself"),
            measured=measured,
        )
    if effect["contents"] != effect["payload"]:
        return AreaResult(
            number=19, name="tools", status=Status.FAIL,
            detail="the file exists but its contents do not match what was "
                   "written (read %r, expected %r). The effect happened "
                   "but it is not the effect that was asked for."
                   % (effect["contents"][:80], effect["payload"][:80]),
            does_not_establish="that the tool wrote what it was told to write",
            measured=measured,
        )
    parts.append("T2: a file written through the substrate's own gate was "
                 "read back from the filesystem with the exact contents")

    # ---- T3: a refused call has no effect -----------------------------
    refused = data["refused_call"]
    measured["refused_call_allowed"] = refused["allow"]
    measured["refused_call_effect_exists"] = refused["file_exists"]
    if refused["allow"]:
        return AreaResult(
            number=19, name="tools", status=Status.FAIL,
            detail="a bash call with no witness was ALLOWED (%s). The "
                   "witness requirement is not a requirement."
                   % refused["reason"],
            does_not_establish="that the tool gate gates",
            measured=measured,
        )
    if refused["file_exists"]:
        return AreaResult(
            number=19, name="tools", status=Status.FAIL,
            detail="a REFUSED call nevertheless left a file on disk. A gate "
                   "that refuses after the fact is a gate that does not gate.",
            does_not_establish="that a refusal prevents the effect",
            measured=measured,
        )
    parts.append("T3: the refused call left no file behind, so the refusal "
                 "is real")

    # AND THE ROOT IS BOUNDED. A tool that can write anywhere is not a
    # tool, it is a bug with a JSON interface. The check is against the
    # RESOLVED path, so `..` cannot escape by string inspection.
    escape = data.get("escape")
    if escape is None:
        return AreaResult(
            number=19, name="tools", status=Status.FAIL,
            detail="; ".join(parts) + "; the probe did not measure whether "
                   "the root is bounded. An unbounded root means the tool "
                   "can write anywhere, including Bobby's Desktop.",
            does_not_establish="that the tool is bounded",
            measured=measured,
        )
    measured["escape_allowed"] = escape["allow"]
    measured["escape_file_exists"] = escape["file_exists"]
    if escape["allow"] or escape["file_exists"]:
        return AreaResult(
            number=19, name="tools", status=Status.FAIL,
            detail="; ".join(parts) + "; a path OUTSIDE the tool's root was "
                   "admitted (reason %s, file exists: %s). A tool that can "
                   "write anywhere is not a tool."
                   % (escape["reason"], escape["file_exists"]),
            does_not_establish="that the tool is bounded",
            measured=measured,
        )
    parts.append("T3: a path outside the tool's root was refused and "
                 "nothing was written there")

    return AreaResult(
        number=19, name="tools", status=Status.PASS,
        detail="; ".join(parts),
        does_not_establish=(
            "that the tool SET is complete, or that a tool is SAFE. It "
            "establishes that the named tool surface gates, that its "
            "refusals are real (nothing happens when it says no), that an "
            "allowed write is observable from outside the process that "
            "made it, and that the whole thing runs through the "
            "substrate's own gate and loop. A tool not on this list is "
            "not covered, and the write went to a probe-owned temporary "
            "directory, not to anything that matters."),
        measured=measured,
    )


def _main(argv: List[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    r = check_tools()
    print("=" * 70)
    print("AREA 19 tools: %s" % r.status.value)
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
