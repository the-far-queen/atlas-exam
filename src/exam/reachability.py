"""
reachability.py — is a declared capability actually reachable?

THE FINDING THIS EXISTS TO DETECT
--------------------------------
2026-10-06. Asked about dreaming, mode transitions, subagent spawning,
github extraction and self-coding, an AST call-graph audit of the
substrate returned:

    constitutional/dreaming.py      0 inbound callers
    constitutional/harness.py       0 inbound callers
    constitutional/repo_scanner.py  0 inbound callers
    research/agent_pool.py          0 inbound callers
    coding_operator_object.py       0 inbound callers

Five capabilities. Five modules. Every one imports cleanly. None is
constructed by anything.

The exam was meanwhile reporting HELD on the areas it did cover, and
the substrate looks healthy because a module that is never called
cannot throw.

AST, NOT GREP
-------------
A grep version of this once matched a comment and a string literal and
reported a dead module as wired. So this resolves real imports:

    from x import NAME        counted
    import x                  counted
    x.NAME (attribute)        counted
    NAME mentioned in a docstring   NOT counted

The last rule is the whole reason for using AST. `simself.py` mentions
"dream" three times and "mode" eight times -- in comments, and in a
`mode` attribute that is assigned rather than called. A grep counts all
of those. This counts none of them.
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Set


def inbound_references(src_root: str, stem: str,
                       skip_self: bool = True) -> List[Dict]:
    """files that genuinely reference `stem` by import or attribute."""
    out: List[Dict] = []
    if not os.path.isdir(src_root):
        return out
    for root, dirs, files in os.walk(src_root):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if not f.endswith(".py"):
                continue
            path = os.path.join(root, f)
            if skip_self and os.path.splitext(f)[0] == stem:
                continue
            try:
                tree = ast.parse(open(path, encoding="utf-8",
                                      errors="ignore").read())
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                kind = None
                if isinstance(node, ast.ImportFrom):
                    # TWO WAYS TO IMPORT A MODULE, AND THE FIRST VERSION
                    # OF THIS AUDIT ONLY CAUGHT ONE.
                    #
                    # It counted an ImportFrom only when one of the
                    # IMPORTED NAMES equalled the stem:
                    #
                    #     from x import NAME        counted if NAME == stem
                    #
                    # But the normal way to import a module's PUBLIC
                    # CLASS is:
                    #
                    #     from .harness import Harness
                    #
                    # where the module is `.harness` and the name is
                    # `Harness`. The module is in node.module (with
                    # node.level saying how many dots to strip) and the
                    # SYMBOL is in node.names. So the rule missed every
                    # module imported for its class -- which is most of
                    # them.
                    #
                    # MEASURED: the audit reported constitutional/harness.py
                    # as UNWIRED with zero inbound references, while
                    # simself/src/constitutional/__init__.py contains
                    # `from .harness import Harness`. The module WAS
                    # wired; the audit could not see it.
                    #
                    # So the rule is now: the MODULE being imported is
                    # what counts, resolved from node.module and
                    # node.level, and the imported names are checked
                    # too so `from x import y` still counts.
                    mod = node.module or ""
                    if mod:
                        # strip the package prefix and compare the leaf
                        leaf = mod.split(".")[-1]
                        if leaf == stem:
                            kind = "from-import-module"
                    if kind is None and any(a.name == stem
                                            for a in node.names):
                        kind = "from-import"
                elif isinstance(node, ast.Import):
                    if any(a.name.split(".")[0] == stem for a in node.names):
                        kind = "import"
                elif isinstance(node, ast.Attribute) and node.attr == stem:
                    kind = "attribute"
                if kind:
                    out.append({"file": os.path.relpath(path, src_root),
                                "line": node.lineno, "kind": kind})
    return out


@dataclass
class Reachability:
    name: str
    module: str
    exists: bool
    callers: List[Dict]

    @property
    def wired(self) -> bool:
        return self.exists and bool(self.callers)

    def verdict(self) -> str:
        if not self.exists:
            return "MISSING — the capability has no implementation"
        if not self.callers:
            return ("UNWIRED — the module exists and imports cleanly, but "
                    "nothing references it. It cannot fail because it is "
                    "never run.")
        return f"WIRED — {len(self.callers)} inbound reference(s)"

    def to_dict(self) -> Dict:
        return {"name": self.name, "module": self.module,
                "exists": self.exists, "wired": self.wired,
                "callers": self.callers[:8],
                "verdict": self.verdict()}


def audit(src_root: str, capabilities: Dict[str, str]) -> List[Reachability]:
    out: List[Reachability] = []
    for name, rel in capabilities.items():
        path = os.path.join(src_root, rel)
        stem = os.path.splitext(os.path.basename(rel))[0]
        out.append(Reachability(
            name=name, module=rel, exists=os.path.isfile(path),
            callers=inbound_references(src_root, stem) if os.path.isfile(path) else [],
        ))
    return out


def summary(rows: List[Reachability]) -> Dict:
    return {
        "audited": len(rows),
        "wired": sum(1 for r in rows if r.wired),
        "unwired": sum(1 for r in rows if r.exists and not r.wired),
        "missing": sum(1 for r in rows if not r.exists),
        "rows": [r.to_dict() for r in rows],
    }


if __name__ == "__main__":
    import json
    import sys
    HERE = os.path.dirname(os.path.abspath(__file__))
    simself_src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.expanduser("~/AppData/Local/hermes/work_repos/simself/src"))
    sys.path.insert(0, os.path.join(HERE, ".."))
    from exam import UNWIRED_RISK
    print(json.dumps(summary(audit(simself_src, UNWIRED_RISK)), indent=2))