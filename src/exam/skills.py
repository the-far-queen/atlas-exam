"""
skills.py -- AREA 20. Can the system COMPOSE, or only look up?

WHY THIS AREA
-------------
The stub said: "the load-bearing test is compositional: an unseen skill
assembled from declared primitives. a system that cannot do that is
looking things up."

That sentence is the whole area. So this area is built around the word
UNSEEN, and the measurement is designed so that a system which merely
RETRIEVES cannot pass it.

HOW THE TEST WORKS
-------------------
    STEP 1  LEARN. The engine learns a lexicon from the canon -- the
            corpus it has. Every sense carries the line it was learned
            from. Nothing is hand-written; the canon is the corpus.

    STEP 2  TAKE A HOLDOUT. A set of sentences that were NEVER in the
            canon. The area builds them from the canon's own verbs and
            nouns, in combinations the canon does not contain, and it
            checks that the holdout sentences really do not appear in
            the corpus.

    STEP 3  MEASURE. Each holdout sentence is read by the engine. The
            reading is one of three:
                CARRIED   the scene carried the meaning
                LABELLED  an idea-word carried it instead of the scene
                DROPPED   the engine could not read it at all

    STEP 4  THE BAR. The area requires that the engine CARRIES a
            meaningful fraction of the holdout. A system that looks up
            can only retrieve what it has seen, and it has not seen the
            holdout.

AND THE FOURTH CHECK, WHICH IS THE ONE THAT MAKES IT AN AREA
---------------------------------------------------------------
    THE MEASUREMENT MUST BE ABLE TO FAIL.

An area that reports a carried-rate of 0% and calls it a PASS because
"0% is a number" is a decoration. So the area also runs the SAME
measurement on sentences the engine CANNOT carry -- the IDEA-WORD
sentences, where the meaning is carried by a label rather than a scene
-- and it requires that the held-out concrete sentences are carried at
a HIGHER rate than the idea-word ones.

If the two rates are the same, the engine is not reading scenes. It is
counting, and the area fails and says why.

WHY A SUBPROCESS
----------------
The exam points AT the substrate. A bug in the substrate's helper would
become a passing grade.

Run: python -m exam.skills
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

PROBE_TIMEOUT_S = 300

#: The fraction of the holdout the engine must CARRY. A NUMBER, and a
#: bar rather than a wish: below it, the engine is looking up rather
#: than composing.
CARRY_BAR = 0.10

#: The holdout must be carried at least this many TIMES better than the
#: idea-word sentences. If the ratio is 1.0, the engine is not
#: distinguishing a scene from a label.
DISCRIMINATION_FACTOR = 1.5


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


#: THE PROBE.
PROBE_SKILLS = r"""
import json, os, sys, re

sys.path.insert(0, os.path.join(os.path.expanduser("~"), "AppData", "Local",
                                "hermes", "work_repos", "simself", "src"))

from constitutional import restore_probe as rp

out = {}

# --- STEP 1: LEARN from the canon --------------------------------------
lex, learned = rp.learn_lexicon()
out['learned_senses'] = len(lex)
out['learned_records'] = len(learned)
out['nouns_known'] = len(rp.word_lists()[1])
out['verbs_known'] = len(rp.word_lists()[0])

if len(lex) == 0:
    out['error'] = 'the lexicon is empty; nothing was learned'
    print(json.dumps(out))
    raise SystemExit(0)

nouns = sorted(rp.word_lists()[1])
verbs = sorted(rp.word_lists()[0])

# --- STEP 2: THE HOLDOUT -----------------------------------------------
# Sentences built from the canon's OWN words, in combinations the
# canon does not contain. AND THE HOLDOUT IS CHECKED AGAINST THE
# CORPUS -- a holdout that is actually in the corpus is not a holdout,
# and the area would be measuring retrieval.
CANON = rp._CANON
corpus_text = ''
try:
    for fn in sorted(os.listdir(CANON)):
        if fn.endswith('.txt'):
            with open(os.path.join(CANON, fn), encoding='utf-8',
                      errors='replace') as fh:
                corpus_text += fh.read().lower()
except OSError:
    corpus_text = ''

# a deterministic holdout: the first nouns and verbs, paired up
n_hold = 40
holdout = []
for i in range(min(n_hold, len(nouns))):
    n = nouns[i]
    v = verbs[(i * 7 + 3) % len(verbs)]
    holdout.append('%s %s the fire.' % (n, v))

# AND THE CHECK: is the holdout actually unseen?
in_corpus = [s for s in holdout if s.lower() in corpus_text]
out['holdout_size'] = len(holdout)
out['holdout_found_in_corpus'] = len(in_corpus)

# --- STEP 3: MEASURE the holdout ---------------------------------------
res_hold = rp.probe('\n'.join(holdout), lex)
out['holdout'] = {
    'sentences': res_hold['sentences'],
    'carried': res_hold['carried'],
    'labelled': res_hold['labelled'],
    'dropped': res_hold['dropped'],
    'carried_rate': res_hold['carried_rate'],
}

# --- STEP 4: THE CONTROL -- idea-word sentences ------------------------
# Sentences whose meaning is carried by an IDEA-WORD rather than a
# scene. If the engine cannot tell these from the holdout, it is
# counting and not reading.
idea = []
for i in range(min(n_hold, len(rp.IDEA_WORDS))):
    w = rp.IDEA_WORDS[i]
    idea.append('The %s of it is what matters.' % w)
res_idea = rp.probe('\n'.join(idea), lex)
out['idea'] = {
    'sentences': res_idea['sentences'],
    'carried': res_idea['carried'],
    'labelled': res_idea['labelled'],
    'dropped': res_idea['dropped'],
    'carried_rate': res_idea['carried_rate'],
}

# --- and the reading of ONE sentence, so the shape is visible ---------
if holdout:
    one = rp.read_sentence(holdout[0], lex)
    out['example'] = one.describe()

print(json.dumps(out))
"""


def check_skills() -> AreaResult:
    """AREA 20 -- skills.

    Four items, all binary, all measured:

      S1  the lexicon is LEARNED from the canon, and it is non-empty
      S2  the holdout is genuinely UNSEEN -- the sentences do not occur
          in the corpus the engine learned from
      S3  the engine CARRIES a meaningful fraction of the holdout
      S4  and it carries the concrete holdout BETTER than the idea-word
          sentences -- otherwise it is counting, not composing
    """
    measured: Dict[str, Any] = {}
    parts: List[str] = []

    ok, data, err = _run(PROBE_SKILLS)
    if not ok:
        return AreaResult(
            number=20, name="skills", status=Status.SKIP,
            detail="the skills probe could not run: %s" % err,
            does_not_establish=(
                "any compositional capability -- the probe did not run"),
            measured=measured,
        )

    if data.get("error"):
        return AreaResult(
            number=20, name="skills", status=Status.SKIP,
            detail=data["error"],
            does_not_establish=(
                "any compositional capability -- there was nothing to read"),
            measured=measured,
        )

    measured["learned_senses"] = data["learned_senses"]
    measured["nouns_known"] = data["nouns_known"]
    measured["verbs_known"] = data["verbs_known"]
    measured["holdout_size"] = data["holdout_size"]
    measured["holdout_carried_rate"] = data["holdout"]["carried_rate"]
    measured["idea_carried_rate"] = data["idea"]["carried_rate"]

    # ---- S1: the lexicon is learned and non-empty ---------------------
    if data["learned_senses"] < 1:
        return AreaResult(
            number=20, name="skills", status=Status.FAIL,
            detail="the lexicon learned from the canon is EMPTY (%d senses "
                   "from %d nouns and %d verbs). There is nothing to compose "
                   "with."
                   % (data["learned_senses"], data["nouns_known"],
                      data["verbs_known"]),
            does_not_establish="that the engine can compose",
            measured=measured,
        )
    parts.append("S1: %d senses learned from the canon's own lines, over "
                 "%d nouns and %d verbs"
                 % (data["learned_senses"], data["nouns_known"],
                    data["verbs_known"]))

    # ---- S2: the holdout is genuinely unseen --------------------------
    if data["holdout_size"] < 5:
        return AreaResult(
            number=20, name="skills", status=Status.FAIL,
            detail="the holdout has %d sentence(s). A holdout too small to "
                   "carry a rate is not a holdout."
                   % data["holdout_size"],
            does_not_establish="that the engine composes rather than looks up",
            measured=measured,
        )
    if data["holdout_found_in_corpus"] > 0:
        return AreaResult(
            number=20, name="skills", status=Status.FAIL,
            detail="%d of %d holdout sentences occur VERBATIM in the corpus "
                   "the engine learned from. A holdout that is in the "
                   "corpus is not a holdout, and this area would be "
                   "measuring retrieval."
                   % (data["holdout_found_in_corpus"], data["holdout_size"]),
            does_not_establish="that the engine composes rather than looks up",
            measured=measured,
        )
    parts.append("S2: %d holdout sentences, none of which occurs in the "
                 "corpus the engine learned from" % data["holdout_size"])

    # ---- S3: the holdout is carried ------------------------------------
    carry = data["holdout"]["carried_rate"] / 100.0
    measured["carry_bar"] = CARRY_BAR
    if carry < CARRY_BAR:
        return AreaResult(
            number=20, name="skills", status=Status.FAIL,
            detail="the engine CARRIED %d of %d unseen sentences (%.1f%%), "
                   "below the %.1f%% bar. On sentences it has never seen, "
                   "it is looking up and finding nothing."
                   % (data["holdout"]["carried"], data["holdout"]["sentences"],
                      data["holdout"]["carried_rate"], CARRY_BAR * 100),
            does_not_establish="that the engine composes",
            measured=measured,
        )
    parts.append("S3: %d of %d unseen sentences carried (%.1f%%), past the "
                 "%.1f%% bar"
                 % (data["holdout"]["carried"], data["holdout"]["sentences"],
                    data["holdout"]["carried_rate"], CARRY_BAR * 100))

    # ---- S4: and it distinguishes a scene from a label -----------------
    idea_rate = data["idea"]["carried_rate"] / 100.0
    measured["discrimination_factor"] = DISCRIMINATION_FACTOR
    if idea_rate <= 0.0:
        ratio = float("inf")
    else:
        ratio = carry / idea_rate
    measured["carry_over_idea_ratio"] = ratio
    if ratio < DISCRIMINATION_FACTOR:
        return AreaResult(
            number=20, name="skills", status=Status.FAIL,
            detail="the engine carried the concrete holdout at %.1f%% and "
                   "the IDEA-WORD sentences at %.1f%% -- a ratio of %.2f, "
                   "below the %.1fx the area requires. The engine is not "
                   "telling a scene from a label, so it is counting rather "
                   "than composing."
                   % (data["holdout"]["carried_rate"],
                      data["idea"]["carried_rate"], ratio,
                      DISCRIMINATION_FACTOR),
            does_not_establish="that the engine composes",
            measured=measured,
        )
    parts.append("S4: the concrete holdout was carried %.1fx more often "
                 "than the idea-word sentences (%.1f%% against %.1f%%), so "
                 "the engine tells a scene from a label"
                 % (ratio, data["holdout"]["carried_rate"],
                    data["idea"]["carried_rate"]))

    return AreaResult(
        number=20, name="skills", status=Status.PASS,
        detail="; ".join(parts),
        does_not_establish=(
            "that the skill set is GOOD, or that the composition is "
            "correct. It establishes that an UNSEEN sentence built from "
            "the declared primitives is carried rather than looked up, and "
            "that the engine tells a concrete scene from an idea-word "
            "label. It does not cover composition outside the six "
            "primitives, and it does not cover whether the carried meaning "
            "is the RIGHT meaning."),
        measured=measured,
    )


def _main(argv: List[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    r = check_skills()
    print("=" * 70)
    print("AREA 20 skills: %s" % r.status.value)
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
