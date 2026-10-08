# atlas-exam

**The load-bearing artifact.** `fieldcore` and `simself` are
implementations that must satisfy this exam. They do not depend on it.

    atlas-exam  ──points at──>  fieldcore, simself
    fieldcore, simself  ──knows nothing about──>  atlas-exam

That direction is the architecture. When the substrate is replaced — a
new model, a new geometry, a different runtime — the exam does not
change. That is what makes "let models evolve" safe rather than merely
possible.

## why it is a separate repo

Because an exam that lives inside the system it grades cannot be
independent of it. `atlas_exam_v2` sat in `simself/src/constitutional/`
and scored **15/27** while 23 of its 27 items assigned themselves a
literal:

```python
def _item_harmonics():
    freq = 137.0
    return {"score": 1.0 if freq == 137.0 else 0.5}
```

It cannot fail, so it cannot pass either. The audit that found this was
also inside simself — the thing that discovered the problem lived in the
thing that had it.

## independence is enforced

Every call into the substrate runs in a **subprocess**. If the exam
imported a substrate helper, a bug in that helper would become a
passing grade. `tests/test_exam.py` parses the AST of every exam module
and fails if anything imports `constitutional` or `fieldcore`.

## scoring

| rule | why |
|---|---|
| unimplemented is **FAIL** | v2 scored 15/27 while self-scoring |
| binary, no partial credit | v2's 0.5 scores hid decorative items |
| every area declares its limit | a pass must never read as a general claim |
| a missing substrate is **SKIP**, never PASS | an exam that passes because it could not run is worse than none |
| overall verdict is PASS only if all 10 pass | no aggregate above the floor of its parts |

The number to track is **mutation yield** — defects found over defects
planted — not pass rate. Bobby: *"absolutely do not shoot for above 95%;
wasted compute, errors are normal."*

## AREA 0 — PROCESS INTEGRITY

The first area, and it is not a property of the substrate. It grades
the process that produces every other verdict.

It exists because on 2026-10-06 I made five consecutive attempts at a
PID loop — change the plant, change the gains, change the plant again,
add a filter — without once asking whether my own arithmetic was
wrong. A five-line trace would have shown the derivative term spiking
on the first run.

The same session, three times, I reported a surprising result as a
finding when it was my own bug:

| reported | actually |
|---|---|
| "the filter does not help PID" | my filtered derivative was wrong |
| "bandpass keeps 0% of energy" | record too short to resolve the band |
| "one bump escapes 100%" | the detector was mislabelling basins |

Full rules: [`CENTRAL-RULES.md`](CENTRAL-RULES.md) — also in the hermes
root and SOUL.md's sole note, which loads every session.

**The rule:** *diagnose before adjusting.* Run it as-is and read the
output **before** changing a parameter. Substituting a plausible next
attempt for a check on the current one is the shape of every mistake.

Area 0 can only establish that the rules are **written** and that the
area **exists**. Whether I followed them is not measurable from inside
the run that followed them — that limit is stated in the area itself.

## the areas

Decomposed against the Boeing 747 as a certifier, in
[`docs/ten-areas-vs-747.md`](docs/ten-areas-vs-747.md).

| # | area | now |
|---|---|---|
| 1 | refusal — can it say no | **HELD** |
| 2 | identity — is the ground real | **HELD** |
| 3 | boundedness — does it stay inside | **HELD** |
| 4 | liveness — does it move | **HELD** |
| 5 | return — does it recover | **HELD** |
| 6 | provenance — can every claim be traced | TODO |
| 7 | reconciliation — do derivations agree | TODO |
| 8 | observability — is change announced | TODO |
| 9 | envelope — what is declared | **HELD** |
| 10 | self-check — can the exam tell working from broken | **HELD** |

**AREA 9 — envelope (implemented 2026-10-08)**

The blocker, per the old README. Now measured, with five declared limits
across three subsystems and four accepted out-of-range responses
(REFUSE / CLAMP / PROJECT / DIVERGE — silence is not on the list).

A limit counts only if all four hold:

- **D1** a finite numeric bound, not a word
- **D2** the quantity it bounds
- **D3** the stated behaviour when exceeded
- **D4** a verifier that resolves to a real, runnable probe

D4 is the 747 rule: a certified system has a test per certified limit.
It was added because the mutation check found the hole — a limit of 1e300
is finite, so D1 passed, and E3 only probes hodge_cycle, so a limit
declared for an unprobed subsystem sailed through. A *second* mutation then
found that a verifier merely *naming* a probe was accepted, so the name is
now resolved against `KNOWN_PROBES`.

Measured, by subprocess probe:

```
inside  damping 0.4   rho 0.8200   peak |x| 0.0593   bounded, as declared
outside damping 0.0   rho 1.2361   crosses 1e6 at step 82   as declared
```

`does not establish` that the limits are tight — only that they are
declared, numeric, sourced, verified, and that measured behaviour matches
them. Whether the envelope is narrow enough is area 10's job.

**23 HELD · 17 OPEN · 13 ABSENT · 0 VOID**

The zero in the VOID column is the point. v2 was 23 VOID and reported
them as passes.

## current verdict

```
passed 8/23        VERDICT: FAIL
```

correct, and deliberately unflattering. Areas 6, 7 and 8 are still not
written; 9 is now measured. FAIL is the right verdict and it stays right
until every area holds.

## run

```
python -m pytest tests/ -q          # the exam testing itself
python -c "import sys;sys.path.insert(0,'src');from exam.cli import _main;_main(['--run'])"
python -c "import sys;sys.path.insert(0,'src');from exam.cli import _main;_main(['--list'])"
```

## the three that matter most

**9 — envelope.** everything else is un-actionable without it. no
declared limit means no test can be complete, because nobody can say
what "outside" means. **NOW HELD** — see above. What it still does not do
is certify that the declared bounds are tight; a system declaring +/-1e6
passes area 9 while being effectively unbounded.

**4.2 — motion direction.** areas 1–5 all pass with a system that
moves the *wrong way*. the 747 proves its engines produce the right
thrust. this is a hole, not a gap.

**1.7 — refusal independence.** on a 747 the thing that refuses and the
thing constrained are separate systems. here the gate is a function
call inside the process it governs.