#!/usr/bin/env python3
"""exam.py -- the entry point the README and the CLI help both already name.

WHY THIS FILE EXISTS (2026-10-16, Hermes).

`atlas-exam` had 79 passing tests and could not be RUN. Both the README and
`python -m exam.cli`'s own help screen told operators to do:

    python src/exam.py --run

and `src/exam.py` did not exist. The package under it is `src/exam/`, so the
documented command could only ever fail with a relative-import error or a
ModuleNotFoundError unless the operator knew to set PYTHONPATH=src first.

The tests passed because every one of them does its own
`sys.path.insert(0, ROOT / "src")`. Four test files repeating the same
workaround is the tell: the package was never installable, and the tests hid
that by each fixing it privately.

An exam that cannot be opened is not an exam. The commit before this one
claimed "95%, not 100%" -- a number that could only have come from the test
suite, never from a real run against the substrate. This file makes the
documented command real, so the next score is measured rather than inferred.

WHAT THIS DOES NOT DO. It does not make the exam pass. It makes the exam
*runnable*, which is strictly weaker and strictly more honest.

    python src/exam.py --list
    python src/exam.py --run
    python src/exam.py --json
    python src/exam.py --selfcheck

Exit codes are the CLI's own: 0 PASS, 1 anything else including skips and
TODOs. A missing substrate is a SKIP, never a pass.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from exam.cli import _main  # noqa: E402  (path must be set first)

if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))