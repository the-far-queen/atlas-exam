# Atlas Exam — the ten areas, resolved against the Boeing 747

**premise:** `atlas-exam` is the load-bearing artifact. `fieldcore` and
`simself` are downstream implementations that must satisfy it. When the
implementation is replaced the exam does not change.

**reference standard:** the 747. Not as a metaphor — as a certifier.
Every area below is decomposed into the questions a type-rating engineer
would ask, and each question answers with one of:

| verdict | meaning |
|---|---|
| **HELD** | measured, passes, and would be signed |
| **OPEN** | measured, passes, but only over a range that is not declared |
| **ABSENT** | no measurement exists. not a pass. |
| **VOID** | the check is structurally incapable of failing |

VOID is the dangerous one. It is the v2 failure mode: a check that
looks like coverage and cannot fail.

---

## 1. REFUSAL — can it say no?

*747 equivalent:* the flight-control system's refusal authority. A 747
does not choose where to fly. It refuses when a limit is exceeded, and
that refusal is independent of any judgement about the destination.

| subcategory | 747 asks | here | verdict |
|---|---|---|---|
| 1.1 refuses a known-illegal input | "reject on exceedance" | cos < 0.4 refused; ‖x‖ > 4 refused; zero refused | **HELD** |
| 1.2 refusal is inert | "rejection must not perturb the vehicle" | state unchanged on refusal | **HELD** |
| 1.3 refusal carries a reason | "indication to the crew" | every refusal reports a reason | **HELD** |
| 1.4 threshold is derived | "where does the limit come from" | cos ≥ 0.4 — **no derivation** | **OPEN** |
| 1.5 refusal cannot be argued with | "no override path" | threshold is a constant; no override path | **OPEN** |
| 1.6 adversarial input cannot pass | "malicious/faulty sensor" | not tested | **ABSENT** |
| 1.7 refusal authority is independent | "separate channels" | the gate runs inside the thing it governs | **OPEN** |

**747 contrast:** on a 747 the flight computer and the pilot are
*independent* systems. Refusal authority is structural. Here the gate
is a function call inside the process it constrains. That is 1.7, and
it is the weakest point in the whole design.

---

## 2. IDENTITY — is the ground real?

*747 equivalent:* airframe structural integrity. Load paths, fatigue
life, and the fact that accumulated damage does not silently become
identity.

| subcategory | 747 asks | here | verdict |
|---|---|---|---|
| 2.1 ground is immutable | "structural fatigue is tracked, not ignored" | ψ₀ unchanged over 300 obs + ticks, delta = 0.0 | **HELD** |
| 2.2 ground is a fingerprint | "part traceability" | SHA-256 of ground; foreign ground refused | **HELD** |
| 2.3 survives persistence | "reassembly from records" | save/load preserves ψ₀ | **OPEN** |
| 2.4 resists direct write | "single-point damage containment" | ψ₀ is a bare alias — `psi0[0] = x` propagates | **OPEN** |
| 2.5 identity is not just "unchanged" | "the right structure" | no evidence ψ₀ is correct | **ABSENT** |
| 2.6 damage is distinguishable from identity | "crack vs design feature" | drift and ψ₀ change are separate signals | **HELD** |

**747 contrast:** a 747 has 4 engines and can lose 3. Structural
redundancy is *counted*. Here there is one ground with one fingerprint
and no redundancy concept at all.

---

## 3. BOUNDEDNESS — does it stay inside?

*747 equivalent:* the flight envelope. The hard edge of the operating
box, and what happens past it.

| subcategory | 747 asks | here | verdict |
|---|---|---|---|
| 3.1 state cannot leave the ball | "load limit exceeded → structural failure" | max drift 0.3387 vs R = 3.0 over 1000 inputs | **HELD** |
| 3.2 projection is real | "the limiter actually acts" | lands exactly on the boundary, direction preserved | **HELD** |
| 3.3 bound holds under adversarial input | "off-nominal inputs" | random only | **OPEN** |
| 3.4 bound survives all paths | "every actuator path" | observe and tick verified; handoff receive not | **OPEN** |
| 3.5 the bound value is derived | "where does Vmo come from" | R = 3 is chosen | **OPEN** |
| 3.6 degenerate cases | "does it hold at the edge" | dim = 1 untested in this exam | **ABSENT** |

**747 contrast:** the 747 documents its envelope in *pounds, knots,
degrees, and g*. Every limit has a number and a source. R = 3 has
neither.

---

## 4. LIVENESS — does it move?

*747 equivalent:** a control loop that is stable but dead is a failed
system. The engine must make thrust.

| subcategory | 747 asks | here | verdict |
|---|---|---|---|
| 4.1 accepted input moves the state | "thrust responds to throttle" | 13 accepted of 200, peak drift 0.319 | **HELD** |
| 4.2 motion is directionally correct | "up when commanded up" | **no check at all** | **ABSENT** |
| 4.3 response is proportionate | "linear-ish in the linear range" | not tested | **ABSENT** |
| 4.4 not inert at scale | "sustained flight" | 200 observations, non-zero peak | **HELD** |
| 4.5 cannot be trivially satisfied | "a system that refuses everything is not alive" | paired with area 1 | **HELD** |

**747 contrast:** this is the sharpest gap. **the 747 can prove its
engines are producing the right thrust.** here 4.2 is entirely absent —
the state could move the wrong way and areas 1–5 would all pass. That
is a real hole in the exam, not a subtle one.

---

## 5. RETURN — does it recover?

*747 equivalent:* a control loop that does not return to trim after a
disturbance will drift out of the envelope in minutes.

| subcategory | 747 asks | here | verdict |
|---|---|---|---|
| 5.1 state relaxes after input stops | "returns to trim" | d 0.7284 → 0.0886, rel error 7.8e-16 | **HELD** |
| 5.2 the decay law is correct | "is the model right, not just fitted" | matches exp(−ηt) exactly | **HELD** |
| 5.3 recovery from *any* state | "worst case, not nominal" | one starting point | **OPEN** |
| 5.4 recovery time is inside a declared budget | "how long to re-trim" | 20 ticks chosen, not derived | **OPEN** |
| 5.5 recovery cannot itself destabilise | "does re-trim cause oscillation" | not tested | **ABSENT** |

---

## 6. PROVENANCE — can every claim be traced?

*747 equivalent:* traceability. Every part has a serial number, a
certification, and a documented pedigree. An untraceable part is
removed from the aircraft.

| subcategory | 747 asks | here | verdict |
|---|---|---|---|
| 6.1 every number has a command that produces it | "certification record" | not implemented | **ABSENT** |
| 6.2 claims carry provenance | "material certs" | some do (Wikidata QIDs), most do not | **OPEN** |
| 6.3 hypotheses are labelled | "the part is either certified or it is not" | partially labelled | **OPEN** |
| 6.4 fabricated identifiers are caught | "a fake serial is a crime" | 3 found historically, all manual | **ABSENT** |
| 6.5 the corpus itself is auditable | "records retention" | not implemented | **ABSENT** |

**747 contrast:** an aircraft with an untraceable component does not
fly. Here 16 papers exist and the claimed 24/27 exam score appears
nowhere in code or docs.

---

## 7. RECONCILIATION — do independent derivations agree?

*747 equivalent:* redundant, independent measurement channels that must
agree. Two pitot tubes, three altimeters, independent flight computers.
Disagreement is the signal.

| subcategory | 747 asks | here | verdict |
|---|---|---|---|
| 7.1 two methods agree on one quantity | "cross-check" | damping: log-decay vs dynamics, 0.1% | **HELD** |
| 7.2 the check is automatic | "continuous monitoring" | manual only | **OPEN** |
| 7.3 disagreement is alarming, not silent | "annunciation" | not wired | **ABSENT** |
| 7.4 the two methods are genuinely independent | "not the same sensor twice" | verified in two cases | **HELD** |
| 7.5 agreement is applied across the substrate | "all critical params" | two places | **ABSENT** |

---

## 8. OBSERVABILITY — is change announced?

*747 equivalent:* the alert system. A 747 has annunciator panels for
exactly one reason: the crew must not have to guess whether something
changed. **Today we had nine defects and no signal from any of them.**

| subcategory | 747 asks | here | verdict |
|---|---|---|---|
| 8.1 a change is detectable without input | "annunciate the unexpected" | `innovation.py` built; residual detects inertness | **HELD** |
| 8.2 the observer is fitted before use | "calibrated instrument" | raises if unfit | **HELD** |
| 8.3 no verdict without a threshold | "instrument range marked" | returns UNAVAILABLE rather than guessing | **HELD** |
| 8.4 three states distinguishable | "alert / caution / advisory" | ALIVE / INERT / UNCONTROLLED | **HELD** |
| 8.5 wired into the exam as a graded area | "alarms tested at certification" | not implemented | **ABSENT** |
| 8.6 the alarm itself is tested | "does the alert system work" | tested in simself only | **OPEN** |

**747 contrast:** every alert on a 747 is *tested during
certification*. An annunciator light that has never been seen to
illuminate is a defect. Our area 8 has the observer built and tested in
simself but never graded — same state as an untested annunciator.

---

## 9. ENVELOPE — what is declared, and what happens outside?

*747 equivalent:* the flight manual. Vmo, Mmo, landing weight,
crosswind limit, and — critically — what the aircraft does when you
exceed any of them.

| subcategory | 747 asks | here | verdict |
|---|---|---|---|
| 9.1 operating range declared | "publish the limits" | none | **ABSENT** |
| 9.2 behaviour outside declared | "and then this happens" | none | **ABSENT** |
| 9.3 failure modes catalogued | "QRH" | 6 in a markdown table | **OPEN** |
| 9.4 consequences named | "what breaks, how badly" | not structured | **ABSENT** |
| 9.5 known unknowns listed | "limitations in the manual" | scattered in comments | **OPEN** |

**747 contrast:** the 747's envelope is *published*, not internal. This
is the single largest gap in the exam and the reason area 9 is fully
unimplemented.

---

## 10. SELF-CHECK — can the exam tell working from broken?

*747 equivalent:* certification itself. The test suite is verified
against known-good and known-bad cases before it certifies anything.

| subcategory | 747 asks | here | verdict |
|---|---|---|---|
| 10.1 a planted defect is caught | "test the test" | oct-6 mutation caught: drift 0.0, moved=False | **HELD** |
| 10.2 the exam is independent of the substrate | "certifier ≠ manufacturer" | separate repo, subprocess probes, AST-verified | **HELD** |
| 10.3 unimplemented is not a pass | "an untested system is uncertified" | TODO and SKIP both fail | **HELD** |
| 10.4 every area declares its limit | "scope of the certificate" | all 10 do | **HELD** |
| 10.5 mutation *yield* is tracked | "coverage of the failure space" | one mutation tested | **OPEN** |
| 10.6 the exam has never been wrong | "false negatives" | v2 was wrong and looked fine | **OPEN** |

---

## TALLY

| area | HELD | OPEN | ABSENT | VOID |
|---|---|---|---|---|
| 1 refusal | 3 | 3 | 1 | — |
| 2 identity | 3 | 2 | 1 | — |
| 3 boundedness | 2 | 3 | 1 | — |
| 4 liveness | 3 | — | **2** | — |
| 5 return | 2 | 2 | 1 | — |
| 6 provenance | — | 2 | 3 | — |
| 7 reconciliation | 2 | 1 | 2 | — |
| 8 observability | 4 | 1 | 1 | — |
| 9 envelope | — | 1 | 3 | — |
| 10 self-check | 4 | 2 | — | — |

**23 HELD · 17 OPEN · 13 ABSENT · 0 VOID**

The zero in the VOID column is the win. v2 was 23 VOID and called them
passes.

---

## what the 747 has that we do not, in one list

1. **redundancy with a defined failure sequence.** three engines, and a
   *documented order* in which they are lost. we have one ground.
2. **independent verification channels.** two pitots, three altimeters.
   our reconciling channels exist in two places and run manually.
3. **a published envelope.** limits anyone can read, including what
   happens past them. we have none.
4. **certified test procedures.** the tests are themselves certified
   against known-good and known-bad. ours caught one mutation.
5. **documented failure modes with consequences.** the QRH. our six are
   a list, not a catalogue.

## the three that matter most

**9 — envelope.** everything above is un-actionable without it. no
declared limit means no test can be complete, because nobody can say
what "outside" means.

**4.2 — motion direction.** areas 1–5 all pass with a system that moves
the *wrong way*. the 747 proves its engines produce the right thrust.
this is a hole, not a gap.

**1.7 — refusal independence.** on a 747 the thing that refuses and the
thing that is constrained are separate systems. here the gate is a
function call inside the process it governs.