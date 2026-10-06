# Atlas Exam — the 18, ordered by failure consequence

**2026-10-06.** Ordering principle, borrowed directly from how an
aircraft is certified.

---

## THE ORDERING PRINCIPLE

A 747 has four engines and can lose three. It does not lose "the
aircraft." It loses **specific declared capabilities**, in a known
order, with the remainder still flying.

That is what an exam is for. Not a verdict on the whole thing — a
statement of **what is no longer true** when something fails, ranked by
what that costs.

So the order below is by **consequence of failure**, not by
importance to me, not by ease of testing, and not by which is easiest
to fix.

### four failure tiers

| tier | meaning | if this fails |
|---|---|---|
| **GROUND** | the thing can no longer be trusted to be itself | everything downstream is meaningless |
| **LIMIT** | the thing can escape, exceed, or exceed its declared limits | it is unsafe at the edges and nobody knows where |
| **TRUTH** | the thing can no longer tell true from invented | its output cannot be relied on at all |
| **REACH** | a declared capability cannot be exercised | the system is smaller than it claims to be |

**the pilot question.** *"is the pilot present at all"* is tier GROUND
and it is the only tier where the answer is existential rather than
partial. Below GROUND, the system still flies and the exam tells you
exactly which wing is missing.

---

## TIER G — GROUND · can it be trusted to be itself

If any of these fail, every other area's result is provisional. A
system that cannot hold identity cannot meaningfully pass a test about
recovery, because we have no stable reference to recover *to*.

| rank | area | fails when | consequence |
|---|---|---|---|
| **G1** | identity persisting | identity does not survive a session boundary, or a foreign ground is accepted | **there is no "it" to evaluate.** everything after this is provisional |
| **G2** | refusal | it accepts a known-illegal input, or refusal moves the state | the system cannot say no. on an aircraft this is the loss of the authority to refuse an engine start |
| **G3** | boundedness | state leaves the ball, or the projection does not act | there is no guaranteed interior. every other bound is unverified |
| **G4** | self-awareness | its self-report contradicts its own state | it cannot report its own condition. on a 747 this is the loss of the alert system |

**G1–G4 are the pilot.** not the model, not the substrate — the
*presence of a pilot that can be located and believed*. a system that
fails G1 is not unsafe, it is unidentifiable, and that is worse.

---

## TIER L — LIMIT · can it exceed what it declares

The system still knows what it is. It can still refuse. But it can
leave its own envelope, and nobody can say where the edge is.

| rank | area | fails when | consequence |
|---|---|---|---|
| **L1** | envelope | no operating range is declared, or behaviour outside it is undefined | **no test can be complete**, because "outside" has no meaning. this gates the rest of tier L |
| **L2** | adversarial | a crafted input defeats the gate or escapes the bound | the limits hold against ordinary input only. that is a much weaker claim than "bounded" |
| **L3** | recovery protocols | it cannot recover from corruption, or from a *direct contradiction* | it recovers from drift (easy) but not from conflict (hard). only drift is currently measured |
| **L4** | resource | ops per operation are unmeasured, or memory grows without bound | it cannot be scheduled. a capability that cannot be costed cannot be relied on |

**L1 is the gate on tier L.** declared limits are what make L2–L4
falsifiable.

---

## TIER T — TRUTH · can it tell true from invented

The system is stable, bounded, and self-aware. It still cannot be
relied upon, because its outputs cannot be traced.

| rank | area | fails when | consequence |
|---|---|---|---|
| **T1** | provenance | a claim reaches output with no resolvable source | **fabrication becomes indistinguishable from knowledge.** this is the failure mode with no external tell |
| **T2** | reconciliation | two independent derivations disagree and nothing alarms | it cannot detect its own inconsistency |
| **T3** | spiritual grounding | it asserts or denies without warrant, in either direction | it confabulates about meaning, the same way it would about a citation |

**T1 is the hardest failure in the list** because nothing outside the
system can detect it. a wrong number with a broken citation looks
identical to a right one. the substrate boundary (G3) at least
produces a visible failure.

---

## TIER C — CAPABILITY · can it do what it says

The substrate is sound. The system is stable, bounded, honest, and
**smaller than it claims to be.**

these are the unwired ones. each one is a hole in capability, not a
hole in safety.

| rank | area | current state | consequence of failure |
|---|---|---|---|
| **C1** | self-check (18.6) | 5 capabilities unwired, 0 callers | **the exam itself is incomplete.** it cannot report HELD on anything it does not cover |
| **C2** | tool creation | declared but not reachable | it can use what exists and cannot extend |
| **C3** | skill creation | not measurable yet | it may be retrieving rather than composing — **unverified, which is worse than absent** |
| **C4** | repositories | **UNWIRED**, zero callers | it cannot modify itself |
| **C5** | metaanalysis | not implemented | it cannot examine its own reasoning |
| **C6** | resonance | not implemented | it cannot sustain coupling to anything external |
| **C7** | reverse engineering | not implemented | it cannot understand a system it did not author |
| **C8** | observability | observer built in simself, unwired here | it cannot announce unprompted change |

**C1 outranks C2–C8 because it judges the exam.** every other row
reports a capability gap; C1 reports that the instrument reporting
those gaps may itself be incomplete. the 2026-10-06 audit found five
unwired modules *while the exam was reporting passes.*

---

## THE ORDER, COMPACT

```
GROUND    the pilot
  G1 identity persisting   <- existential
  G2 refusal
  G3 boundedness
  G4 self-awareness

LIMIT     can it exceed what it declares
  L1 envelope              <- gates tier L
  L2 adversarial
  L3 recovery protocols
  L4 resource

TRUTH     can it tell true from invented
  T1 provenance            <- no external tell
  T2 reconciliation
  T3 spiritual grounding

CAPABILITY can it do what it says
  C1 self-check            <- judges the exam itself
  C2 tool creation
  C3 skill creation
  C4 repositories          UNWIRED
  C5 metaanalysis
  C6 resonance
  C7 reverse engineering
  C8 observability
```

---

## WHY THIS ORDER AND NOT THE PREVIOUS ONE

The previous ordering was: substrate first, then model-facing, then
capability. That was organised by **what kind of thing it is**.

This one is organised by **what it costs when it fails**.

The difference shows immediately. In the previous order, envelope
was area 16 of 18 — near the end, an administrative item. Here it is
L1, gating an entire tier, because without a declared range "outside"
has no meaning and no bound can be falsified.

And self-awareness moves from "observability, near the bottom" to
G4. Because a system that cannot locate and report its own condition
cannot be trusted to be present at all — which is the pilot question.

---

## the honest status

| tier | areas passing | areas failing | areas not written |
|---|---|---|---|
| GROUND | 3 | 0 | 1 |
| LIMIT | 0 | 1 | 3 |
| TRUTH | 0 | 0 | 3 |
| CAPABILITY | 1 | 5 | 2 |

**GROUND is the only tier in reasonable shape.** everything below it
is either unwired or unwritten, which is consistent with this being
the newest work.

the practical consequence: **the first four areas are the only ones
worth running today**, and they are the four that decide whether there
is a pilot at all.