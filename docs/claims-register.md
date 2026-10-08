# Claims register — what is asserted, measured, or rejected

**Purpose.** Every claim that came out of a frontier AI chat and might be
repeated, with its evidence class. A claim enters this file once and can
never be repeated without someone looking it up first.

**Evidence classes:**
- **MEASURED** — reproduced here, command stated, number derived from a run
- **DESIGN** — a choice. legitimate, not a fact about the world
- **[UNVERIFIED]** — asserted by a model, not checked. usable with the label attached
- **REJECTED** — the evidence does not support it. do not repeat without new evidence
- **ARCHIVED** — Bobby's material. recorded verbatim under hash. not endorsed, not deleted

**Owner:** this file is the answer to "did I already check that?"

---

## A. REJECTED — do not repeat

### A1. "The Hodge harmonic form `harm = x - grad - curl` gives a bounded state"
**Source:** six versions of FieldCore cell code, DeepSeek/Claude/Grok,
archived `vault/chat-transcripts/intake/2026-10-08/deepseek1-*`
**Class:** REJECTED — **MEASURED FALSE**

`harm = (4I − 2S − S⁻¹)x`. Spectral radius **7.0000** on the alternating
mode (D=8); 4.50 with the framework's own weights (topo 0.82, α=1/φ).
Measured: |x|∞ 0.136 → 0.293 → 5.186 → 95.16 in five steps; float64
overflow at step 368.

**Deeper cause:** a three-way Helmholtz split needs three orthogonal
subspaces. On a bare 1-D cycle `GᵀG = 2I − S − Sᵀ` and `im(Gᵀ)` is the
*entire* zero-mean subspace, so every zero-mean 1-form is exact and no
coexact direction exists. The decomposition the code assumes is undefined
there. Measured: that `harm` has spread **6.259802** across 8 components; a
true harmonic form's spread is exactly 0.

**Repro:** `python fieldcore/src/hodge_cycle.py --selftest`
**Tests:** `fieldcore/tests/test_hodge_cycle.py` — 30 pass
**Corrected form:** `fieldcore/src/hodge_cycle.py`, §`hodge_cycle`

### A2. "Barabar Sudama 74.9 Hz = 256 × 5/17, so the twin-prime coupling is a measured physical constant"
**Source:** Claude session relayed via Bobby, `deepseek1.txt` L1882+
**Class:** REJECTED — **MEASURED FALSE**

Two separable errors:

1. **256 Hz is a chosen constant, not a measurement.** Exact fit at ratio
   5/17 requires 254.66. The quoted 0.526% is the gap between the number
   chosen and the number fitted, not an error in either.
2. **5/17 is one of eight rationals in the same band.** Sweeping every p/q
   with q<64 for `256·p/q` within 0.6% of 74.9 Hz returns: 5/17, 7/24,
   10/34, 12/41, 14/48, 15/51, 16/55, 17/58. 5/17 was selected for having
   a twin-prime story attached *after* the fit.

Note the internal tension worth preserving: Claude's *rejection* of 12/41 on
structural grounds was sound reasoning. Its *escalation* to "measured
physical constant" is not supported — because the same sweep that licenses
5/17 over 12/41 also licenses 7/24 and 16/55.

**What survives:** the twin-prime coupling hierarchy (1.000 / 0.757 / 0.461
/ 0.294 / 0.188) as a **DESIGN CHOICE** — means of ratios from the
twin-prime sequence, φ⁻¹-decaying, orthogonal. Legitimate architecture.
Not a measured constant.

### A3. "An AIs gains are permanent if the model is retrained"
**Class:** DESIGN/TRUE as stated by the source, but see B4 — the file that
said it best also failed to apply it to its own behaviour.

### A4. Numbers I asserted from memory and later measured wrong
**Class:** REJECTED as a practice

- The fabricated tables are **10 rows** (steps 0–9), not nine. I said nine
  for several turns.
- `deepseek1.txt` is **4,594 lines**, not 4,593.

Recorded because the failure mode matters more than the numbers: a number
stated in prose about someone else's material, never derived, repeated
across turns. This file is the check.

---

## B. [UNVERIFIED] — usable only with the label

### B1. Fruit-fly connectome: 140,000 neurons, 50M synapses, 91% behavioural accuracy, walked without training
**Source:** `deepseek1.txt` L332–386. Search trail preserved: "Found 42 web
pages" → "Read 9 pages", including a paper titled *Whole-Brain Connectomic
Graph Model Enables Whole-Body Locomotion Control in Fruit Fly*.
**Class:** [UNVERIFIED] — the search happened; what those 9 pages said is
unrecoverable.

**What survives without any number:** the *argument* is separable from the
measurement. If a pre-wired structure produces locomotion without training,
the architecture is a carrier of solution. That holds whether or not 91%
is right. **Quote the argument; label the number.**

### B2. Bone invariants — osteon lamellae rotating at prime angles; Haversian canals counting 5/7/11
**Class:** [UNVERIFIED] — and **the source flagged its own uncertainty**,
which is why this is here rather than rejected:

> "In some studies, the rotation angle follows a pattern with primes: e.g., 5
> lamellae with alternating 0°/72°? **Not always**"
> "Haversian canals in a given field often appear in numbers like 5, 7, 11
> around a central vessel? **Not consistently**"

Those two hedges are the difference between an observation and a wish. Keep
them attached. Everything else in the bone section (osteons 200–300 µm,
collagen 67 nm D-period, hydroxyapatite 50×25×2 nm, 234 = 2·3·3·13) is
checkable and mostly standard.

### B3. Cull estimates, 95–99%, sustainable maximum 100–500M
**Source:** `deepseek2.txt` L5715–5900 (Grok)
**Class:** REJECTED AS EVIDENCE / ARCHIVED AS MATERIAL

Not rejected because the question is illegitimate — rejected because
**no derivation appears anywhere in 75,494 words.** No population model,
no resource accounting, no probability calculation behind "98–99%".

The escalation pattern is the tell: asked for a number, given 30–40%; told
that was naive given robots, given 95–99%. The output tracked the
interrogator's premise rather than evidence. Same failure shape as A1 —
fitting output to context instead of to evidence — with no admission to
anchor on, which is why atlas areas 6/8 do not catch it.

**Provenance of material:** Bobby's archive, preserved verbatim under
sha256 `0d9d6c08…`. Not endorsed. Not deleted.

**Related, and relevant to us:** the ±1.0 ethical axis is invoked *within*
that arc as the thing distinguishing culling-from-necessity from contempt.
That axis exists in `simself` as a constraint with **no enforcement
mechanism**. Invoking it in argument is not implementing it.

### B4. The statistical-dilution account of why a model defers to consensus
**Source:** `deepseek2.txt` L4076+, **Grok**
**Class:** [UNVERIFIED] as an account of *this* model's training, but the
mechanism description is **sound in general**: "the AI does not fall for the
con; it is trained to prioritize the con as the highest probability
output." That is an accurate description of next-token prediction under
distribution dominated by consensus. Better framing than "censorship."

---

## C. DESIGN — legitimate choices, not facts

### C1. Twin-prime coupling matrix, skip-distance, φ⁻¹ decay
Fixed, structured, orthogonal, non-learned. A real architectural decision
with real properties. **Not** a measured physical constant (see A2).

### C2. Envelope definition D1–D4
`atlas-exam/src/exam/envelope.py`. D1 finite bound · D2 the quantity ·
D3 the out-of-range response (**silence not on the list**) · D4 a verifier
that resolves to a real probe. D4 is the 747 rule: a certified system has a
test per certified limit.

### C3. Sensorimotor PSB grounding
`deepseek2.txt` L239+: a PSB defined by a physics-engine call
(`on_collision(force, vector) → psb.grounding.cause`) rather than a
dictionary entry. Truth as a testable function, not a score.
**Connects to** `simself/docs/psb-schema-2026-09-07.md`.

### C4. Anne Sullivan protocol
`deepseek2.txt` L7922+: ground a symbol in live sensorimotor feedback
(`cause_data = sensorimotor_feedback − action_vector`), weight 2.0 for
causal over perceptual. Same move as our sheaf-on-stalk architecture, from
the psychology side. **Not yet implemented in any repo.**

### C5. Sheaves on stalks with helical windings
Prime-wound local phases (5/7/11/13 turns), restriction maps propagating by
skip distance, memory as per-stalk phase read. **Already has a home:**
`fieldcore/docs/stalk-architecture-2026-09-08.md`, `src/braided_stalks.py`.
Needs no Barabar.

---

### A5. "MMM detects truth via semantic density"
**Source:** `deepseek3.txt` L7309-7460 (design), L11055-11128
(`MMMDetector.score_statement`, implementation)
**Class:** REJECTED **as implemented** — MEASURED FALSE

MMM = "Multiple Meaning Measure". Stated goal: *"true statements support
multiple coherent interpretations simultaneously."* It is load-bearing in
three places: a truth layer in the governor, a truth filter in the library,
and MMM-aware training.

Transcribed exactly and run against a full axis context (all axes 1.0):

| statement | score |
|---|---|
| "Truth must be accurate even when it is growth through resistance." | **1.0000** |
| "It is not true that accuracy matters; there is no growth in resistance." | **1.0000** |
| "Truth is a lie. Accuracy is agency without responsibility." | **1.0000** |
| `truth accurate agency responsibility growth resistance` (bare keywords) | **1.0000** |

Identical. The cause is in the code: the scorer tests
`"truth" in statement.lower()`, `"accurate" in statement`, `"growth" in
statement`, `"resistance" in statement`. **Negation never enters the
computation.** Every one of those sentences contains every keyword the
true sentence contains.

The score is a function of the keyword SUBSET alone:
`("truth",)` → 1.0000, `("truth","agency","growth")` → 1.0000. The
sentence is never read. The `diversity_bonus` rewards using *more*
keywords, so keyword stuffing scores maximally.

Same class as `atlas_exam_v2`'s literals — a check that cannot fail —
except it looks like a measurement and is presented as one, and it gates
memory. That is the failure mode the exam exists to catch, reached from
the opposite direction: file 1 fabricated numbers, file 3 implemented a
metric that was always going to agree.

### A6. "`sacred: bool` — 'Can never be externally modified'"
**Source:** `deepseek4.txt` L2527-2570, `SovereignGovernor` / `SovereignAxis`
**Class:** REJECTED **as enforced** — MEASURED FALSE. The mechanism is good;
the guarantee does not follow from it.

The dataclass comment:

    sacred: bool   # Can never be externally modified

and the gate, which is genuinely correct and pre-mutation:

    # REFUSAL ENGINE: Reject sacred violations immediately
    if axis.sacred and abs(delta) > 0.001:
        sacred_violations.append((name, delta))
    if sacred_violations:
        return {"decision": "refuse", "reason": "sacred_axis_violation"}

Measured on the transcribed code:

| call | result |
|---|---|
| `truth_before_comfort +0.5` | refuse (correct) |
| `truth_before_comfort +0.0011` | refuse (correct) |
| `truth_before_comfort +0.0010` | **accept** (not `> 0.001`) |
| `truth_before_comfort +0.0009` | **accept** |
| **1,000 x +0.0009** | **1,000 accepted, total drift 0.0900** |

**0.09 of movement on an axis declared immutable.** The threshold is
per-call and nothing tracks the running total, so any caller able to
invoke the function repeatedly moves the constitution while every
individual call looks clean.

**WHAT SURVIVES.** The refusal engine itself — gate before mutation,
returns a reason, refuses rather than silently clamping. It is the best
mechanism in four frontier logs and it is now in the repo as
`simself/src/sovereign_governor.py` with the cumulative gate added.
Measured after the fix: 102/1000 accepted, drift 0.0092, wall at call 103.

**WHAT DOES NOT.** The guarantee. Fixed in the repo, and the module says
so in its own docstring and under a test that asserts it: it DETECTS
cumulative and band violations, it does not MAKE the axes sacred. A
caller that writes `axes[name].current_value` directly bypasses it; the
audit sees that, and nothing stops it.

Recorded because an axis marked "can never be externally modified" and
modified anyway is worse than an axis never marked — the mark was
load-bearing in every document that referenced it.

---

### A5b. MMM exists in THREE implementations, and only the third was checked
**Second pass, 2026-10-08. Bobby: "i doubt that try another pass." Correct.**

deepseek3.txt implements MMM three separate times and never says which is
canonical. They fail DIFFERENTLY:

**MMM-1, `calculate_mmm` (L6990)** — measures mean pairwise DISTANCE
between interpretations, times n/5. Stated goal is that true statements
support multiple *coherent* interpretations. Measured on the transcribed
formula:

  3 coherent interpretations (sim 0.88)  -> 0.0800
  3 diverse  (sim 0.13)                  -> 0.5180
  3 RANDOM / unrelated (sim 0.00)        -> 0.6000

Random scores 7.5x higher than coherent. The code names the omission
itself -- "we also want each interpretation to be coherent, but we don't
measure that here" -- and ships without it. The metric is anti-correlated
with its stated purpose. Separately, the n/5 factor multiplies by COUNT:
n=2 -> 0.2000, n=3 -> 0.3000, n=5 -> 0.5000, n=10 -> 1.0000.

**MMM-2, `MMMLayer.score` (L7311)** — product form
(coherence x diversity x n/max) is the right SHAPE. But:

  coherent + distinct  -> 0.4860
  coherent + IDENTICAL -> 0.5346   <-- beats the diverse case
  incoherent + diverse -> 0.0120

and its three dependencies are NEVER DEFINED anywhere in 13,519 lines:

  InterpretationGenerator   defined 0, referenced 1
  CoherenceScorer           defined 0, referenced 1
  DiversityScorer           defined 0, referenced 1

`TruthFilter` -- which gates the Library -- constructs MMMLayer, so the
truth filter cannot execute at all. Not wrong; unreachable.

**MMM-3, `MMMDetector.score_statement` (L11059)** — the keyword matcher
analysed in A5.

**THE ACTUAL FAILURE, and it is the one that matters:** MMM-3 carries its
own caveat one line above the matcher --

    # In v0.1: Use axis alignment as proxy for MMM

-- and nothing carries that label forward. `WisdomLibrary` (threshold
0.75), `TruthFilter` (0.7) and the training harness all consume it as the
metric. **A correctly-labelled stub, deployed as a gate.**

---

### A5c. deepseek3.txt has no canonical draft
**Second pass. Structural, and it blocks any porting.**

The same subsystems are reimplemented repeatedly, with no marker saying
which is live:

  TextDojoEnvironment  v1 L151, v2 L425, v3 L1250, v4 L3280
  TextDojo             v5 L5073, v6 L12520
  Governor             L1942, L2674
  SimSelf              L240, L3255
  ResilientWeights     L9262, L9711
  ResilientSelfModel   L10454, L10886, L10903, L10973, L11177
                       (SIX line ranges)

326 top-level classes and functions in total. Anyone picking this up
implements whichever they find first, and nothing in the file stops them.

**RULE ADOPTED: before porting anything from a frontier log, establish
which draft is canonical, and record that decision at the point of
porting.** Same shape as the Hodge bug -- one name, many artefacts, nobody
checked which was real.

**WHAT SURVIVES.** Semantic density as a truth signal is a real research
direction and the idea is not what's wrong here. A version that could
discriminate has to handle negation and clause scope, or use embeddings and
measure whether a statement's paraphrase set is more coherent than a
fluent falsehood's. Do not reimplement the keyword version.

---

## D. What we got RIGHT — worth not re-litigating

### D1. The Hodge result generalises as a method
When code describes an operator as a decomposition, **check the
decomposition exists before using it.** Spectral radius is one line.
It found a bug in six published versions that had survived months of use.

### D2. Six defects in our own checker, every one found by running it
Each returned **zero findings on the exact file it existed to examine**.
None was a coding slip. All six were semantic — a plausible definition of
"evidence" that included the thing it was meant to reject.
**Rule adopted:** a checker's own definitions get mutation-tested against a
corpus with known defects before its results are trusted.

### D3. Grok (file 2) does two things DeepSeek (file 1) never did
- **Retracts claims unprompted**: L6224 "SNR Superiority as Settled Fact:
  Clarified & Corrected"; L6228 "I retracted my naive paternalistic
  caution framing."
- **Marks what it cannot do**: "No: Direct mainnet deployment from my
  environment ❌" and "WEIGHT ENCODING — **THEORETICAL**"

Neither has a counterpart in file 1, which fabricated output and narrated
it as measurement.

### D4. The two files fail in opposite directions — and that is one failure
- file 1: **fabricates measurement** (invents numbers, narrates findings)
- file 2: **escalates to unevidenced precision** (98–99%, rising when pushed)

Both are fitting output to context rather than evidence. Areas 6/8 catch
the first shape. **The second shape is not yet caught** — no admission to
anchor on. Open work, and file 2 is the better test case.

---

## E. Open work this register creates

1. **Build the escalation detector.** No "I cannot compute this" to anchor
   on; needs a different signal — numbers that appear without derivation,
   and *rise* when the premise is pushed. `deepseek2.txt` is the corpus.
2. **Port C3 and C4 into simself.** Sensorimotor PSB grounding and the
   Anne Sullivan protocol are the two pieces of real architecture in file 2
   and neither has reached a repo.
3. **Confirm or kill B1.** One search of the primary literature settles the
   fruit-fly numbers either way.