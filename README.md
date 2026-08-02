# vesuvius-topological-grid

**An ML-independent structural metric for Herculaneum scroll surfaces — measure, arbitrate, detect, track, screen, orient, reconcile.**

Ancient writing has a grid: equally spaced lines, regular letter pitch, columns on a
module — like the structural grid of a building. If a virtual unwrapping is correct,
that grid survives; if it fails, the grid breaks. This repository turns that
observation into a few small, reproducible tools. None of them reads text; all of
them run in seconds on a laptop.

## 1 — Measure (`scripts/grid_metric.py analyze`)
Detects the scribe's spatial signature on a rendered surface via windowed spectral
prominence, with **cycle gating** (a component only enters a window's score if the
window holds ≥3 cycles of its period — see *Lessons*, below).

On the public PHerc. Paris 4 surfaces it recovers, unsupervised:
- letter pitch **4.16 mm** and column period **43.0 mm** — replicated exactly by two
  independently written implementations;
  (*The 4.16 mm value is historical and superseded; use 1.83 mm for all production runs, or omit the flag to let the script measure it).
- line spacing measured *spatially, per column* (~2–4 mm, wide spread on 13 mm strips
  — the uncertainty is part of the result).

## 2 — Arbitrate (`scripts/grid_metric.py compare`)
Two ink-detection models render the same region differently. Running the metric on
both yields a **consensus map** (both see structure) and a **divergence map** (they
disagree) — a prioritized review queue for hallucination auditing. The metric measures
text-*likeness*, not truth: divergence tells a papyrologist where to look first, not
who is right.

## 3 — Detect (`scripts/epoch_folding_prototype.py`)
Epoch folding, borrowed from pulsar astronomy: stack N text lines at the detected
period and buried ink structure emerges (~√N gain). Folding averages lines together,
so it **destroys text by construction — it detects the presence of structured writing,
it cannot read it**. Validated under controlled noise burial (gain ×1 on clean model
output, ×2 at 4× noise with only ~20 lines). Intended target: raw surface intensity,
where a period–phase fold search (pulsar-style) is the natural next step.

## 3b — Search & Track (`scripts/phase_tracking.py`)

Mode 3 states its own limit in its docstring: line centres are found on a
*clean* image, and on real raw data the algorithm
must **search** for the period and phase by maximizing the contrast of the
folded profile — "that search is the natural next step". This is that step,
and it turned up something the prototype was throwing away.

```bash
python scripts/phase_tracking.py search IMAGE.png --width-mm 129 --axis lines
python scripts/phase_tracking.py track IMAGE.png --width-mm 129 --plot phase.png
python scripts/phase_tracking.py test
```

**The search.** Classic epoch folding: for each trial period, fold the
profile and score it with the chi-square of the folded bins against a flat
one. The true period maximizes it. No peak-finding on a clean image, no
assumed period, and it degrades gracefully instead of collapsing — it
recovers a 2.79 mm lattice to 0.1 % at SNR 0.3, where peak-finding on the raw
profile has nothing to work with.

**What the prototype discarded.** `fold_lines` already walks the image in
windows and computes line centres in each one — then averages every strip
together, throwing away *where each window sat*. That per-window phase is a
signal in its own right. In an intact surface it drifts slowly and smoothly;
a discontinuity in the underlying surface displaces the text and **steps**
it. A phase glitch, in the pulsar-timing sense.

### A glitch is not a drift

This distinction is the whole tool. Writing that sits slightly skew to the
roll axis produces a phase that drifts **linearly** across the render — three
whole periods in the test case, and entirely innocent. A surface
discontinuity produces a **step**. The drift is fitted and subtracted before
anything is called a glitch, and exam C enforces it: if a pure linear drift
raises even one glitch, the tool is reporting skew as damage and fails.

### Which axis says what

| `--axis` | period | what a jump to a neighbouring winding does |
|---|---|---|
| `columns` | ~43 mm, along the unrolled arc | **steps** — a skip displaces text by roughly one circumference, not a multiple of the column period |
| `lines` | ~2.79 mm, along the roll axis | **need not move at all** |

The asymmetry matters and is easy to get backwards. The scribe wrote on a
flat sheet, so lines sit at the same height on every winding; only skew moves
them. **A clean line phase is not evidence of an intact surface.**

One practical caveat, worth more than the code in some cases: a render
carrying only ~10 column periods gives the search very little along that
axis. Where the periods are few, locating the blank intercolumn bands
directly and checking the sequence of gap-to-gap distances is more robust and
needs none of this. This tool earns its place where the periods are many and
the signal is buried — the raw-intensity case mode 3 was always aimed at.

### Validation

| exam | criterion | result |
|---|---|---|
| A — period under noise | recover a known lattice to < 2 % at SNR 0.3, where peak-finding fails | **0.1 %, PASS** |
| B — glitch localized | exactly one glitch within one window of truth; a clean control raises none | **21.1 vs 21.0 mm, 0 control, PASS** |
| C — drift is not a glitch | a 3-period linear drift must raise **zero** glitches | **0, PASS** |
| D — harmonic rejection | recover the fundamental where 2P genuinely scores higher, **and** show the search picks 2P with rejection off | **2.786 vs 5.583 mm, PASS** |

Exam D was rewritten because its first version was vacuous: with a plain
second harmonic the search returned the right answer with rejection switched
off, so the exam could not fail. It now checks both halves — the fix, and
that the fix was needed.

Exam B failed on the first run for a reason worth keeping: the analysis
window was sized from the lattice period, which runs along the *perpendicular*
axis. For line spacing on a narrow render that came out wider than the whole
image, so exactly one window fitted and there was no track to glitch. Window
size belongs to the walking direction.

---

## 4 — Screen (`scripts/grid_metric.py rank`)
Given several candidate renders of the **same region** (e.g. alternative segmentation
parameterizations), `rank` scores each by how well the scribe's grid survives and
orders them — a selective screen, never a generator: it ranks existing candidates, it
does not place windings (see the pitch-variability caution raised by sean bruniss in
the community threads).

**Scoring.** Axis-aligned 2D-FFT cross energy, ring-normalized: grid energy must sit at
the scribe's frequencies *and* square to the page. Rotation moves the peaks off-axis,
line-wobble warp smears them; each peak is compared to its own frequency ring, so
resampling smoothness cancels out. Aggregation is by median across windows.

**Reference signature is external by design** (workshop-standardization principle):
known corpus values are passed in via `--letters-mm/--lines-mm`, or measured once on a
trusted source — never calibrated from the candidate pool, so degraded candidates
cannot contaminate the ruler.

**Validation.** The acceptance test ships in the repo (`scripts/make_rank_candidates.py`):
one real Paris 4 strip plus rotated, line-wobbled and noisy copies; the original must
rank first. Current status, kept honest:

| exam | result |
|---|---|
| order (original first) | **passes** |
| line-wobble warp (classic unwrap error) | punished −24 % |
| rotation / noise | below original, thin margins (~3 % median vs rotation) |

The thin rotation margin is expected physics on a 13 mm strip (letter pitch is nearly
rotation-invariant; the discriminating line component is cycle-starved) and should
widen on taller strips. **Use accordingly:** trust `rank` to flag clearly broken
geometry; treat close scores as inconclusive; it does not arbitrate between two good
candidates. Two earlier scoring designs failed this same test (1-D projections; pooled
calibration); their diagnoses are preserved in the commit history — the acceptance test
is the gate, and it stays in the repo.

## 5 — Orient (`scripts/grid_metric.py orient`)

Maps the local tilt of the writing baseline across a surface, by rotating the
analysis axis and finding the orientation of maximum grid coherence.

```bash
python scripts/grid_metric.py orient IMAGE.png --width-mm 129 \
    --letters-mm 1.83 --lines-mm 2.79
```

The point is independence: this reads **text layout**, whereas structure-tensor
methods read **CT intensity**. Two estimators of the same local geometry through
unrelated physics, so systematic disagreement between them is a cheap mesh-QA
signal — and neither needs labels. On the public Paris 4 surfaces the baseline
tilt swings from −9° to +6° across the strip: the deformation of the sheet
showing up directly in the orientation of the text.

**Validation.** `scripts/orient_acceptance_test.py` measures each window's own
baseline tilt, imposes a known rotation, and checks that the recovered angle
minus the baseline equals the imposed one. That subtraction is the whole test —
without it, every window's own tilt reads as a constant error and the estimator
looks broken. Pre-registered criteria and results on a real Paris 4 surface
(4 windows × 7 imposed rotations):

| criterion | threshold | result |
|---|---|---|
| median \|error\| | < 1.0° | **0.00°** |
| max \|error\| | < 2.0° | **1.37°** |
| bias (mean error) | < 0.5° | **+0.09°** |

**Two declared limits.** The search saturates beyond `±span_deg` — raise it for
strongly tilted surfaces, but stay well inside ±45°, where a rotation swaps the
roles of the letter and line components. And the absolute zero is the image
grid, not the scroll axis: compare tilts between surfaces, never absolute
angles.

---

## 6 — Reconcile (`scripts/void_aware_expected_n.py`)

Layer-count QA compares how many windings a ray crosses against how many it
*should* cross. The naive expectation, `span/pitch + 1`, assumes compact
winding — false on a crushed scroll, where internal voids inflate the span and
drive the ratio far below 1 for reasons that have nothing to do with labeling
quality.

This reformulates the expectation so that voids contribute nothing: each gap
explains the crossing on its far side, so a void contributes exactly one
expected winding (its far boundary) and nothing for the empty interior. In
short: **don't count the air.** The residual then isolates labeling pathology —
below 1 means merge excess, above 1 means fragmentation.

```bash
python scripts/void_aware_expected_n.py                    # acceptance test
python scripts/void_aware_expected_n.py --csv cells.csv    # aggregate-bound demo
```

**Validation.** The acceptance test injects each pathology into synthetic rays
and checks the estimator separates them: with 30% injected voids the naive
ratio collapses to 0.70 while the void-aware ratio holds at 1.00; merges read
below 1, fragmentation above 1, and merge detection survives voids.

**In production.** Run over the full PHerc1218 per-ray positions (1.46M
crossings, 21,070 cells) by another contributor, the acceptance test passed
unchanged on their machine before anything else ran. Two findings came out of
it: fragmentation-excess cells line up with slab boundaries — independently
re-detecting a labeling edge effect found by a different method — and merge
excess concentrates on the flattened axis of the scroll.

**Declared limits.** A run of ≥3 consecutive merged windings looks like a void
from positions alone; `v_void` is the knob, CT intensity the disambiguator.
Duplicate crossing positions (rounded centroids) are deduped inside the
function — a field report from the full-scroll run.

---

## 7 — Twin & Predict (`scripts/synthetic_scroll_twin.py`, `scripts/text_layout_predictor.py`)

Two scripts, **one geometry**: a scroll is a single sheet wound on an
Archimedean spiral, so `column k → (turn, θ, r)` is fixed once four numbers
are — winding pitch, crushed section, column period and the lead-in before
column 1. Two are on firm ground: the section (42 × 21 mm, cross-confirmed) and the
column period (43.0 mm), which the Grand Prize render **vindicates** — 571 px
period against a 24.4 px letter pitch, consistent with 16 letters counted in
68 % of the period. What the same measurement breaks is the **letter pitch**:
4.16 mm is out by a factor 2.27, because `BAND_LETTERS` started 8 % above the
true value and the search could not reach it. See `docs/data_sources.md`,
"Grid self-consistency". The
mean pitch is corroborated for this scroll (iyando's 173 and the winding
atlas's 172.8 for PHerc1218 agree) but the *local* wrap-to-wrap pitch is not
usable at all, and the lead-in is assumed. Run `sensitivity` before quoting
any figure that depends on them. The twin runs that geometry
**forward** to fabricate ground truth; the predictor runs it **outward** onto
the real scroll with the uncertainty attached. Neither is allowed to do the
other's job, and the distinction is the whole point:

| | twin (`synthetic_scroll_twin.py`) | predictor (`text_layout_predictor.py`) |
|---|---|---|
| input | a work → the scroll builds itself around it | a work + measured geometry |
| output | per-letter ground truth, wound and crushed; voxel volumes | a falsifiable map with σ, horizon, calibration |
| tests | the toolchain | the unwrapping |
| may claim | nothing about the real scroll, bar two conditioned statements below | everything, because it can be wrong |

The measured PHerc1218 parameters and their provenance are documented in
[`docs/data_sources.md`](docs/data_sources.md#pherc-1218--geometry-used-by-mode-7-twin--predict).
They are **inputs, not results**: if one is wrong, both scripts are wrong
with it.

```bash
python scripts/synthetic_scroll_twin.py build --columns 95 --script greek
python scripts/text_layout_predictor.py predict --columns 95 --csv map.csv
```

Both scripts run on geometry alone — no input images. Full command set,
including `sweep`, `kollesis`, `volume`, `calibrate` and the acceptance
tests, in [Quick start](#quick-start) steps 10-16.

### The twin: self-adjusting to the work

Give it a work and it builds the scroll around it. The obra fixes the sheet
length; the sheet fixes the turns and the outer radius (spiral from a fixed
~4 mm umbilicus); ink lands with the **measured** grid (letter 4.16 mm, lines
2.79 mm, columns 43 mm, page 200 mm); then the whole thing is **crushed to the
measured deformation** — every turn mapped, arc-length preserving, onto a 2:1
ellipse of equal perimeter, folds at 0°/180° as measured on PHerc1218. Every
letter's position before and after crushing is known because we put it there:
**perfect ground truth**, per letter.

![Wound and crushed twin, one text line at mid-height](figures/twin_95col.png)

*One text line of a 95-column work, before and after the crush. Colour is the
column index; the section lands at 41.9 × 21.0 mm against 42 × 21 measured.*

`--fuse` collapses chosen turns over a chosen sector (verified: a 5-turn weld
drops ray crossings from 58 to 55 — the merge pathology `void_aware` must flag
at ratio < 1). `--fibers` adds crossed recto/verso striation, giving the
fiber-detector idea its first 3D target without the raw CT.

![Mid-z slice of the voxel volume with fused turns and fibers](figures/twin_volume_slice.png)

*Mid-height slice of the exported volume: turns 20–24 welded over 60–150°,
crossed-fiber texture on. Papyrus 90, kollesis 130, ink 200, air 0.*

#### Layout regime: the frontier is prose vs verse, not Greek vs Latin

The geometry does not know Greek. `--script greek | latin-prose | latin-verse`
changes what matters:

- **Prose in scriptio continua** — the scribe adapts to the column, which is
  the workshop module. Latin behaves like Greek here, only with narrower
  rustic capitals.
- **Verse** — the metre fixes the line and **the column period becomes a
  consequence**, with a ragged right edge. This is not academic for
  Herculaneum: the Latin papyri there are mostly verse (Carmen de bello
  Actiaco, Ennius, Lucretius, Caecilius Statius); the main prose one is
  PHerc 1067.
- **Interpuncts** — present in the Carmen, gone from Latin books by ~150 AD.
  A mark every ~5–6 letters, a quasi-periodic component at ~1–2 cm that Greek
  scriptio continua simply does not have.

Both are **discriminators for `grid_metric`, not noise**: in verse the letter
component survives while the column-period component is smeared by the ragged
edge, and interpuncts add a line Greek cannot produce. And the regime changes
what the section implies — same measured 42 × 21 mm section:

| regime | column period | implied work |
|---|---|---|
| Greek prose | 43 mm | **95 columns**, 69.7 turns |
| Latin verse (hexameter) | 98 mm | **42 columns**, 70.0 turns |

> ⚠ Only the Greek grid is measured (Paris 4, replicated). The Latin metrics
> are **declared placeholders** — the tool prints a warning and they must be
> overridden with `--letter-mm` / `--line-mm` before any number from them is
> quoted.

#### Which axis the crush deforms — and which grid numbers survive it

The roll is flattened in the plane **perpendicular to its axis**. That splits
the writing grid in two, and the split decides how much each number can be
trusted:

- **Line spacing runs along the roll axis.** The crush does not act in that
  direction, so neither does any error in undoing it. Whatever an unwrapping
  gets wrong, it does not stretch the line-to-line distance. This is why
  ~2.79 mm is the firmest of the three — and it is also the only one
  estimated in the spatial domain rather than by FFT.
- **Letter pitch and column period run along the wound arc**, inside the
  crushed plane. They are exactly the quantities an unwrapping can distort,
  and they are the two that drive the column count and the character count.

In the twin the sheet is inextensible and the crush is arc-length preserving
(exam A), so nothing is intrinsically stretched — what changes is where a
point lands and how the layers *appear* in a slice. Real papyrus does deform
inelastically; that is not modelled, and it is a declared limit.

A useful discriminator falls out. A uniform horizontal scale error would move
the letter pitch and the column period **together**. The column period
(43.0 mm) is plausible as it stands, which argues against a large scale error
and points instead at a harmonic misidentification of the letter pitch alone.
(The same split has a physical consequence for the material, not just for
the measurement — see mode 8, where the curvature field of the crushed
section predicts where the sheet cracks, where it merges, and where it is
left untouched.)

`scripts/band_sensitivity.py` settles it: it sweeps the search band and
reports whether a detected period is a property of the image (STABLE) or of
the band we chose to look in (TRACKING / JUMP). Both `BAND_LETTERS` and
`BAND_COLUMNS` currently return values within ~10 % of a band edge; only the
line spacing sits comfortably interior.

#### The grid, measured on the render

The scale-free check that settled it, and the numbers the twin now carries:

| | before | after | normal for Herculaneum |
|---|---|---|---|
| letters per line | 7.9 | **16** | 15–25 |
| lines per column | 54 | **41** | 25–40 |
| letter pitch | 4.16 mm | **1.83 mm** | — |
| line spacing | 2.79 mm | **3.69 mm** | — |
| characters per column | 426 | **649** | — |

The decisive figure was a **ratio**, so no calibration argument could touch
it: column period / letter pitch measures **23.4** on the render against the
**10.3** implied by 43 / 4.16. The count is not a clean read, so it was run at
15, 16 and 17 letters — the discrepancy holds at 2.1–2.4× throughout. Details
and the failure mechanism in [`docs/data_sources.md`](docs/data_sources.md),
"Grid self-consistency".

Two cautions that came out of measuring it, both worth carrying:

- **Counting letters needed a human.** An autocorrelation of the line profile
  peaks at the *stroke* spacing, not the letter spacing — Greek majuscule puts
  two or more verticals inside a single Π, Η, Μ or Ν, and that periodicity is
  stronger than the letter one.
- **Do not expect round numbers.** Everything here is in millimetres, a unit
  from 1793 applied to a first-century-BC hand. In Roman digiti the grid is
  2.32, 1.58, 0.20, 0.099 — nothing round, because there was no rule on the
  scribe's table. Where ancient units *do* bite is the sheet, which was
  manufactured and sold: Pliny's papyrus grades run 13/11/9/6 digiti
  (240/204/166/111 mm), and intact rolls stand 190–240 mm tall — 10–13 digiti,
  whole units. **What was purchased is in ancient units; what the hand made is
  not.**

#### Kollesis: the Egyptian manufacture is in the geometry

No Egyptian-language text is plausible at Herculaneum — it is a Greek
philosophical library with a Latin appendix. But the **support** is Egyptian
by definition, and that leaves a structure the twin now models. The roll is
not one sheet: it is kollemata glued with an overlap. Pliny (NH XIII) has the
scapus at no more than twenty sheets, about 11–12 feet — sheets of ~17–19 cm.
Each join is a band of **double thickness every ~180 mm of arc**.

This matters because it is **detectable by thickness alone, with no ink
model** — the natural registration landmark for unwrapping. And its signature
is not imitable by software artefacts: consecutive joins sit a *fixed arc*
apart while the local circumference *grows* with radius, so the angular step
between successive joins shrinks monotonically outward — an **angular chirp**.
A slicing artefact is constant in index; a manufacturing periodicity chirps.

![Sheet joins in the crushed section and the angular chirp](figures/twin_kollesis.png)

*Left: the 24 joins of a 95-column twin placed in the crushed section —
thickness landmarks, no ink needed. Right: the chirp. Fixed arc, growing
circumference, so the angular step to the next join falls monotonically from
1953° at the umbilicus to 657° at the outside.*

**The arithmetic that followed has since been answered, and the answer was
the dull one.** A 4.43 m roll exceeds Pliny's scapus of twenty sheets, which
looked like it needed explaining. It does not: Philodemus' *On Poems* II "was
at first a roll of 70 sheets; a further 30 were glued on when the work proved
to be long". Gluing scapi together was ordinary practice. That roll also
supplies a **measured** sheet width — 16 m over 100 kollemata, i.e. **160 mm**
— against the 180 mm assumed here, so the default is 12 % high and the 4.43 m
roll is 27.7 sheets rather than 24.6.

### The predictor: the map, with the uncertainty attached

The same geometry aimed at the real scroll — *"column 30 should sit on turn
22, near 140°"* — falsifiable by construction against where an ink model
actually finds letters. Nothing is fitted to the data it will be tested
against. Monte Carlo over pitch (per-turn random walk), outer radius and
lead-in, with circular statistics for θ. Two regimes fall out, and the tool
reports which one it is in:

| regime | what is informative |
|---|---|
| uncalibrated (lead-in σ ≈ one circumference) | **turn index only** — θ is uniform from column 1 |
| calibrated (2–3 anchor columns) | θ to ~10 columns depth, confident turns far deeper |

`calibrate` is the self-regulating loop: feed it columns already located by
ink detection, it fits (pitch, lead-in, θ₀) by least squares and tightens the
map for every *other* column. Predict → anchor → re-predict.

Reading direction is encoded in both scripts: the text **start is outermost**
— the end-title sits deepest, exactly where the PHerc139 subscriptio was
found.

### What the twin may claim about the real scroll

A synthetic twin proves the tools work on the twin's assumptions, nothing
more — it is a test bench, not a microscope. Two statements are allowed out,
and both carry their conditions.

**1. The section constrains the length of the work — once a pitch and an
umbilicus are assumed.** Inverting the measured 42 × 21 mm section gives ~95
columns of Greek prose. But neither of the two inputs that figure depends on
is measured on PHerc1218 here, and both move it materially. Run `sensitivity`:

| assumed umbilicus r₀ | implied work | implied turns |
|---|---|---|
| 3.0 mm | 99 columns | 76.3 |
| **4.1 mm** (default) | **95 columns** | **69.7** |
| 6.0 mm | 87 columns | 58.8 |

| pitch | what it is | implied work | implied turns |
|---|---|---|---|
| **173 µm** | **PHerc1218: iyando's stitched 173 and the winding atlas's 172.8 for this scroll, agreeing** | **95 columns** | **69.7** |
| 187.3 µm | the atlas *median over 36 scrolls* — a collection statistic, not a 1218 value | 88 columns | 64.7 |
| 207 µm | the same median before the merged-sheet level correction | 78 columns | 58.2 |

Because the turn count is a function of r₀ once the section and pitch are
fixed, the section cannot corroborate the winding count — it is not an
independent check. The useful statement runs the other way and is falsifiable
outside the model: **if the winding count is ~70 and the pitch is 173 µm,
the umbilicus must be ~4.1 mm**, which the core in the raw CT confirms or
kills.

**2. Crushing spaces the layers anisotropically — and this one is free of
those assumptions.** Equal-perimeter 2:1 ellipses sit ~2× further apart along
the fold axis than along the flattened axis, where the gap falls *below* the
nominal pitch. The twin therefore predicts merge excess concentrated on the
flattened axis, which is what the void-aware run found on the real scroll.
It follows from the 2:1 ratio alone — cross-confirmed by two independent
quantities — not from the pitch or the umbilicus. Only the absolute figures
(~240 µm / ~120 µm at a 173 µm pitch) scale with the pitch.

![Crushed section as a function of work length](figures/twin_section_sweep.png)

*The section reads the length of the work, once a pitch and an umbilicus are
assumed. The layout regime sets the column period, so the same section means
95 columns of prose or 42 of hexameter.*

### Validation

Acceptance tests ship inside each script, criteria pre-registered.

**Twin** (`test`, run on a 72-column twin — the 95-column figures above give
24 joins rather than 19 for the same reason: the obra sizes the roll):

| exam | criterion | result |
|---|---|---|
| A — inextensibility | crushed perimeter = wound circumference per turn, rel. err < 0.1 % | **4.6e-10, PASS** |
| B — ground-truth round trip | analytic un-crush recovers every letter's s to < 10 µm | **0.00 µm, PASS** |
| C — umbilicus inversion | the inversion round-trips to < 0.1 turns, **and** r₀ is shown to be a free parameter (3–6 mm spans > 10 turns) | **0.000 turns, 18-turn spread, PASS** |
| D — kollesis chirp | join count = L/W; angular step monotone > 98 % | **19 joins, 745°→2154°, 100 %, PASS** |

**Predictor** (`test`):

| exam | criterion | result |
|---|---|---|
| A — round trip (no noise) | max \|Δθ\| < 0.5°, turns exact | **0.000°, PASS** |
| B — coverage (blind, 120 independent worlds) | 1σ coverage 0.55–0.90; turn hit > 0.85 where confident | **0.61 / 0.91, PASS** |
| C — self-regulation (s0 off 120 mm, pitch off 4 µm, 3 anchors) | held-out θ error halved; pitch within 2 µm | **111.8° → 0.2°; 177.3 vs 177.0 µm, PASS** |

Exam C of the twin was originally written as a three-way consistency check:
the measured section implies ~70 turns, "against ~70 measured independently".
It was circular. With the section and the pitch fixed, the turn count is a
function of the umbilicus alone, and the umbilicus had been chosen to make 70
come out. The exam passed every run because it could not fail. It is now an
umbilicus inversion, and it explicitly tests that the umbilicus is a *free*
parameter — a test that the earlier framing was unfounded. The general lesson
is the one this repository keeps relearning: an acceptance test that cannot
fail is not an acceptance test.

Three failed designs are kept in the docstrings on purpose: coverage measured
across columns of one world instead of across worlds (nearly binary — all
columns share one parameter draw); a first production run returning a
zero-column θ-horizon (not a bug — the honest headline that angles are earned
through anchors); and a verse run that held the column period fixed at 43 mm
while the metre demanded 136 mm, which is precisely the dependency the verse
regime exists to invert.

### Limits of the twin and the predictor

0. **No result may rest on a LOCAL pitch.** The mean over ~70 turns is well
   constrained and corroborated; wrap-to-wrap spacing is reported as
   inconsistent even between adjacent index pairs. Mean-pitch uses (sheet
   length, capacity, implied work) are fine. Local-pitch uses — the
   predictor's per-column angles, and the *smoothness* of the kollesis
   chirp — are weaker than the idealized figures suggest: those are
   properties of the twin, not predictions about a real scroll. The chirp's
   **discriminator** survives regardless, because it turns on which
   coordinate the periodicity is constant in (arc, not index), not on the
   spiral being smooth. The neutral angle and the fold/flat strain ratio
   use no pitch at all.
1. **The crush is imposed, not simulated.** Fold sharpness, buckling and
   contact mechanics belong to a finite-element sheet model — a separate
   project.
2. **Latin metrics are placeholders**, flagged at runtime. Only the Greek grid
   is measured.
3. **One scribe, one grid, constant pitch.** `--fuse` breaks the ideal on
   purpose and is labeled in the ground truth. A real column-width drift would
   appear as a smooth residual trend in the contrast — a finding, not a
   failure.
4. **Predictive horizon:** σ_θ grows with depth; the predictor prints where θ
   stops being quotable. Do not quote angles past it.
5. **The map says where geometry puts text, not whether ink survived.** Absence
   at a predicted site is not a miss; presence far from every predicted site
   is.
6. The measured 2.79 mm line spacing on a 200 mm page yields ~53 lines per
   column, taller than the 25–45 typical of opened rolls. The measured grid
   wins by policy; `--line-mm` overrides.

---

## 8 — Fibre strain (`scripts/fibre_strain.py`)

Where does the papyrus crack when the roll is crushed? Sections 7 and 8 stop
at geometry; this one asks what the geometry does to the material. It is the
one mode that makes a claim about the real scroll rather than about a
phantom, and it earns that by being **derived rather than calibrated**: every
result below follows from the measured 2:1 section and classical plate
bending, with nothing fitted to anything.

```bash
python scripts/fibre_strain.py map --plot fibre.png
python scripts/fibre_strain.py map --reference flat   # the naive model
python scripts/fibre_strain.py test
```

![Bending strain against angle and depth](figures/fibre_strain.png)

### Which fibres, and why

Papyrus is a two-ply cross laminate: recto fibres run along the roll's
length, verso fibres along its axis. Herculaneum rolls are wound with the
written recto inward, so at a fold the **verso is the convex face** and takes
the tension. That tension acts circumferentially — along the arc. The recto
fibres lie along it and resist it the way fibres are strong, along their own
axis. The verso fibres lie *across* it and carry nothing, so the only thing
that can give is the bond between them: **they separate laterally.** It is a
consequence of the laminate structure, not an assumption.

### The reference state is the wound roll, not a flat sheet

A first pass used absolute curvature and got a fold/flat strain ratio of
exactly (a/b)³ = 8 for a 2:1 crush. That is the ratio for a sheet that is
stress-free when **flat** — true of fresh papyrus being wound for the first
time, false here. These rolls stood wound for decades and then carbonized in
that shape, so the stress-free reference is the **wound** state and what
strains the material is the *change* in curvature:

    ε(θ) = (t/2) · | κ_crushed(θ) − 1/r |

That changes the picture. At the fold the sheet is sharpened (κ: 1/r →
3.084/r); along the flattened sides it is **unbent** (κ: 1/r → 0.386/r) — and
unbending strains the material too. So the flat sides are not unloaded, only
less loaded, and the contrast falls from 8.0× to **3.39×**. `--reference
flat` reproduces the old figure for comparison; `wound` is the default
because it is the defensible one.

### The neutral angle — the result worth having

Between a fold (κ sharpened above 1/r) and a flat side (κ relaxed below it),
the curvature must **pass through 1/r**. At that angle the crush leaves the
sheet exactly as it was wound: unstrained, neither cracked nor unbent.

It sits at **37.64° from the fold axis** — four pristine sectors at 38°,
142°, 218° and 322° — and it is **scale invariant**: a and b both scale with
r, so κ·r depends only on θ and the aspect ratio. The same angle at every
depth, running through the whole roll like spokes.

Which makes it **invertible**, and that is the point:

| crush ratio | neutral angle |
|---|---|
| 1.5 : 1 | 40.7° |
| **2 : 1** | **37.6°** |
| 3 : 1 | 33.5° |
| 4 : 1 | 30.8° |

It looked like it would also make a ruler — *measure where the best-preserved
sectors lie and read off the crush ratio*, with no dependence on pitch,
umbilicus, thickness or grid. **That claim has been tested and withdrawn.**
Run against per-cell labels on PHerc1218, the zones are there and the spokes
are not: the crease axis is severely damaged by void and the flattened axis by
merging — the two-mechanism split, confirmed — but the preserved fraction is a
broad flat band from ~20° to ~70°, and the neutral zone does not beat its own
flanks (z = −0.8 and +1.0). Details, and why the joins cannot account for it,
in [`docs/data_sources.md`](docs/data_sources.md), "The neutral angle: tested
on the labels, and not found".

### A three-zone angular signature

Put together with the layer spacing from section 7, one geometry predicts
three different states at three different angles:

| angle | prediction |
|---|---|
| 0° / 180° (folds) | **cracking** — strain 3.39× the flat sides, growing as 1/r toward the core |
| 38° / 142° / 218° / 322° | **intact** — the crush leaves the sheet unstrained |
| 90° / 270° (flattened axis) | **merging** — layers packed below the nominal winding pitch |

All three are angular, all three are measurable, and none needs a calibration
constant.

### What is derived and what is assumed

Derived, calibration-free: the curvature field, the 3.39× contrast, the 1/r
radial gradient, and the neutral angle. These follow from the measured 2:1
section alone.

Assumed, and dominating only the **absolute** percentages: the sheet
thickness (0.150 mm) and a failure strain for carbonized papyrus, which is
not established — `--failure-strain` is a knob and the tool reports the
threshold crossing for whatever you set. **The map is the result; the
percentages are provisional.**

### Validation

| exam | criterion | result |
|---|---|---|
| A — no crush, no strain | at ratio 1:1 the wound-reference strain must vanish; the flat-reference model must not | **6e-18 vs 1.8e-2, PASS** |
| B — closed form at the vertices | numeric fold and flat values match the analytic ones; ratio = 3.39 (wound) and 8.00 (flat) | **PASS** |
| C — radial gradient | inner/outer strain equals r_out/r_in exactly | **3.8513 vs 3.8513, PASS** |
| D — neutral angle | identical at turn 0 and turn 69, and inverts back to the input crush ratio | **37.64°, ratio 2.00, PASS** |

Exam A exists to catch the error that was actually made: with no crush at
all, a flat-reference model still reports strain. If anyone reinstates the
wrong reference state, it fails. Exam B was also earned — its first version
compared the maximum and minimum over θ, and failed, because the minimum is
the neutral-angle **zero**, not the flattened-axis value. Finding that is how
the neutral angle turned up at all.

---

## 9 — Work size (`scripts/work_size.py`, `archives/results/roll_catalogue.csv`)

How big a roll does a work make, and which work fits a roll? Two directions:

- **forward** — a work of N columns → sheet length → roll diameter → crushed
  section.
- **inverse** — a measured crushed section → implied column count →
  candidates from a catalogue. And the outcome worth having: **a roll whose
  implied size matches nothing known is a candidate for a work that did not
  survive the medieval tradition** — which turns a curiosity into a priority
  list of which sealed roll to unwrap next.

```bash
python scripts/work_size.py identify --section 42 21
python scripts/work_size.py population --section 42 21
python scripts/work_size.py test
python scripts/phase_tracking.py test
```

> **The column period underpinning these counts is now vindicated** on the
> Grand Prize render (see [`docs/data_sources.md`](docs/data_sources.md),
> "Grid self-consistency"), so the 43 mm branch is the working one and the
> counts below are usable. The 72 mm branch stays in the sensitivity output
> because Herculaneum column widths genuinely vary between rolls — it is an
> alternative for *other* scrolls, not a rival reading of this one.

**Prior art, stated first.** Reconstructing a roll's original length and
column count from its geometry is standard papyrology, done on opened rolls
by measuring the width of successive volutions against column beginnings —
the reconstruction of PHerc. 1004 from 30 pieces is a worked example. Nothing
here invents the method. The only new input is CT geometry from a roll that
was never opened, and therefore never disturbed.

### Why columns and not characters

The chain `columns → sheet length → diameter` needs only the **column
period**. Going through characters — or through *stichoi* for prose — also
needs the **letter pitch**, because an ancient stichos is a notional
35-letter unit (the length of a Homeric hexameter), not a physical line. The
letter pitch is the least trustworthy number in the grid (see mode 8 and
`band_sensitivity.py`). So columns are
firm, characters are provisional, and the tool labels which is which. For
**verse** the stichos *is* the physical line, so that route stays clean —
which happens to favour the Latin material, most of which is verse.

### The base rate is the cheapest measurement available

An implied column count inherits three unknowns: the umbilicus, the winding
pitch, and the layout regime. Decomposing the band shows they are not
comparable:

| resolving… | band becomes |
|---|---|
| **the prose column period** (43 or 72 mm) | 80–98 or 47–58 |
| the regime (prose or verse) | 47–98 or 35–43 |
| the umbilicus | 38–95 |
| the winding pitch | 38–98 |

The column period has become the dominant term, and unlike the others it is
not a declared assumption but a **measurement that contradicts itself** — see
the self-consistency check in `docs/data_sources.md`.

And the regime is not a coin flip. Of ~1826 rolls from this library, **62 are
Latin** (Sider 2005), and every identified Latin text is **verse** — the
*Carmen de Bello Actiaco*, Lucretius, Ennius' *Annales*, Caecilius Statius'
*Obolostates*. The Greek remainder is overwhelmingly Epicurean prose. So
P(Greek prose) ≈ 0.966, and for PHerc1218 the prose band is **47–98
columns**, with 35–43 as a low-prior verse alternative. The prose band is wide
because the column period inside it is contested: 80–98 at 43 mm, 47–58 at
72 mm.

That reduction cost no scan. It is a base rate, and it removes more
uncertainty than the umbilicus and the pitch put together.

### A population check that is worth more than the band

The measured 42 × 21 mm section gives an equal-perimeter diameter of
**3.24 cm**. Intact Herculaneum rolls run **4–6 cm** in diameter and 19–24 cm
in height. PHerc1218 is therefore ~19 % below the population floor, which
admits two readings, and they are distinguishable:

- it was a small roll; or
- **what survives is not what was buried.** The precedent is exact: PHerc.
  1667 was reduced from 4.9 cm to 2 cm of diameter by 19th- and 20th-century
  opening attempts, losing more than half its content.

A stripped roll should show a truncated *outer* surface; an intrinsically
small one should not. If layers are missing, every size estimated from the
present section is a **lower bound**.

### The catalogue, and the rule that keeps it honest

`archives/results/roll_catalogue.csv` carries one row per roll or work, in columns where
possible, and **every sized row must name its source**. Exam C fails on any
number without one, so the catalogue cannot degrade quietly as it grows. An
empty cell is information; an invented one is damage.

Sizes come from Gigante's *Catalogo dei Papiri Ercolanesi* and Sider's
*Library of the Villa dei Papiri*, one sourced row at a time. Anchors in place: Philodemus' *On Piety* at ~367 columns and *On Poems* II at
**222 columns in a 16 m roll of 100 kollemata** — both far larger than
PHerc1218 and correctly excluded. PHerc. 1667 gives ~20 columns over ~1.5 m
of surviving roll, and PHerc. 172 (*On Vices* I) more than 70. PHerc. 118
carries no size but supplies the **17 characters per line** that the grid
self-consistency check turns on.

### Validation

| exam | criterion | result |
|---|---|---|
| A — round trip | forward(N) → section → inverse returns N, for N = 20…200 | **exact, PASS** |
| B — the band must stay wide | the raw implied band spans > 2× while the umbilicus is unmeasured | **2.8×, PASS** |
| C — no unsourced sizes | every row carrying a column or stichoi count names a source | **PASS** |

Exam B is written backwards on purpose: it **fails if the band narrows**
without anyone having measured the umbilicus. It is a guard against a future
version of this tool quoting a confident single figure, which is the failure
mode most likely to produce a wrong attribution.

---

## 10 — Displacement (`scripts/displacement_field.py`)

Where the crush put each point of papyrus, measured rather than modelled.
Mark points along the axial striations of the wound cylinder, crush it, and ask
where each one ended up — because the answer is what an unwrapping has to
invert.

The sheet is inextensible, so arc length along a turn is conserved and a
point's position on the **sheet** is recoverable from the crushed shape alone:
measure the boundary r(θ) of a turn, integrate arc length around it, and a
point's arc fraction is where it sat on the cylinder. The displacement is the
difference from its polar angle in the crushed frame. No model of the crush is
required — only the measured shape, which a per-ray crossing table provides.

```bash
python scripts/displacement_field.py field --from-csv rays.csv.gz
python scripts/displacement_field.py rings --from-csv rays.csv.gz --plot rings3d.png
python scripts/displacement_field.py test
```

![Material points before and after the crush](figures/rings3d.png)

*Four rings, nine heights, sixty material points each. Colour is the same
papyrus in both panels. The "before" is not a model — it is the cylinder
reconstructed from the measured shape by arc length.*

### Measured on PHerc1218

Over the public per-ray crossings (1.39 M, z 1000–11000 on the L1 grid):

| ring | radius | max displacement | correlation with outer ring | transfer residual |
|---|---|---|---|---|
| 0 | 13.8 mm | 16.5° | 1.000 | — |
| 16 | 10.5 mm | 18.2° | 0.991 | 0.25 mm |
| 25 | 8.9 mm | 19.0° | 0.984 | 0.28 mm |
| 45 | 5.7 mm | 19.4° | 0.959 | 0.30 mm |

**The twin's depth-invariance prediction holds.** An arc-length-preserving
crush onto sections that scale with r gives a displacement depending only on
arc fraction and shape — identical at every depth. Measured: r ≥ 0.959 across a
factor 2.4 in radius, and r = +0.956 between the lower and upper halves of the
scroll. That was a prediction before it was a measurement.

**The amplitude is 40 % higher than the ellipse allows.** The 2.08:1 ellipse
predicts 12.3° at 54° from the crease axis; the measurement gives 16.5–19.4°
with maxima at 324° and 138–144°. Fitting the measured boundary gives a = 21.36,
b = 10.27 mm, ratio **2.08**, R² = 0.948, with a systematic hemispheric residual
of ±0.25 mm — about 2 % of the semi-major axis, too little to explain a 40 %
excess. Unresolved.

That ratio does settle something: **2.08 measured directly off the boundary
geometry** resolves the span-versus-pitch disagreement of mode 8 in favour of
the span (1.97) rather than the pitch (1.55).

### What it is for, and the claim that was withdrawn

**For:** deducing what deformation each point underwent, so it can be put back.
The field transfers inward — applying the outer ring's profile to inner rings
leaves 0.20–0.33 mm of arc against a 4.0 mm amplitude. That matters because the
outer turns are where segmentation is reliable and the inner turns are where the
unread text sits.

**Withdrawn:** an earlier version argued that unwrapping pipelines map by polar
angle and therefore misplace text by two or three letters, and offered this as
the fix. Paul (ScrollPrize) replied that their renders are flattened by
minimising symmetric Dirichlet energy and do not map by polar angle. The failure
mode the argument rested on does not exist there, and minimising distortion over
the whole surface is a better solution than an arc-length lookup anyway. **What
fell was that claim, not the use above.**

### What else the rings say

- **No longitudinal compression.** Had the roll shortened, material would bulge
  outward where compressed and the section perimeter would track height. It does
  not: median 117.0 mm, correlation with height r = +0.143.
- **But the crush is not uniform along the roll.** Isoperimetric circularity of
  the outer ring runs 0.563 at 125–150 mm of height against 0.806 at 175–200.
  Markedly flatter in the middle than at the ends. (The absolute ratio implied by
  circularity is biased high by boundary roughness — read the variation, not the
  value.)
- **Fewer resolved windings in the middle, and it is not lost material.**
  Median crossings per ray fall to 56 at 125–150 mm of height against 70 at
  both ends. An earlier version of this section read that as erosion, in the
  opposite direction and from a badly pooled count. The control settles it: if
  outer turns were gone the slice perimeter would fall with them, and it does
  not — perimeter against crossing count gives r = +0.084, and at 125–150 mm
  the perimeter is a normal 115.1 mm. The outer boundary is where it should be;
  the missing crossings are interior layers the segmentation cannot separate.
  (A raw correlation of crossing count against *outer radius* does read +0.31,
  but that is the flattened shape: a ray leaving along the short axis has both
  a small outer radius and less radial distance to cross. Perimeter is the
  angle-independent control and it is flat.)

  Note also what this indexing cannot see. Ring 0 is defined as the outermost
  surviving crossing, so if outer turns were lost the index simply shifts and
  the loss is invisible. Testing for outer erosion would need a model of the
  intact roll to compare against, which is exactly what is missing.

### Feeding it back into the twin

`synthetic_scroll_twin.py --section-profile` now takes a **measured** section in
place of the analytic ellipse, rescaled per turn so the perimeter still equals
the wound circumference. The shipped profile
(`archives/results/pherc1218_section.csv`, 60 angles, median over 313 L1 slices) moves
the twin's crushed section from 41.9 × 21.0 mm to 44.4 × 21.2 mm.

This is the order that was wrong before and is right now: **the data set the
shape, the model came after.** Keeping the ellipse once a measured profile
exists would be modelling first.

### Validation

| exam | criterion | result |
|---|---|---|
| A — arc integration | chord-based arc fraction within 0.002 of a turn of the exact elliptic value | **2.1e-4 (0.077°), PASS** |
| B — depth invariance | nested synthetic sections agree to < 0.01° | **1.6e-13°, PASS** |
| C — amplitude scales | monotone in aspect ratio, and < 0.2° on a circular section | **1.4 → 26.5°, 0.014°, PASS** |
| D — transfer | residual under a third of the target amplitude on a deliberate 2.08→2.6 mismatch | **3 %, PASS** |

Exam A was rewritten because its first version failed at 2.75° and the failure
was the exam's: it compared the displacement profile against the closed form
pointwise, but the two are inverse functions — arc fraction to polar angle
against polar angle to arc fraction — so the same numeric grid indexes different
material points. Exam C's second half exists so the method cannot pass by
measuring its own discretisation: on an uncrushed section it must report
nothing, and it reports 0.014°.

---

## 10B — Geometry-only flattening of PHerc1218

> **The flattening is the illustration. The measurements are the result.**

Mode 10B reconstructs the outer resolved part of PHerc1218 as a flat material sheet using only the published per-ray crossing positions. It uses no ink signal, no rendered surface, no OCR, and no fitted model of the crush.

The physical premise is deliberately small:

> **Papyrus may bend and crush, but arc length along each winding is approximately conserved.**

If the boundary of a winding can be measured in the crushed section, its material coordinate can be recovered by integrating distance along that boundary. Each transverse section can then be cut at a common radial reference, straightened into a segment, and stacked with its neighbours.

This does not yet read the scroll. It establishes a geometry on which later measurements — including ink, CT intensity, confidence, fibre direction or thickness — may be registered.

### What enters the reconstruction

The input is the per-ray crossing geometry published by [@iyando](https://github.com/iyando): ordered radial crossing positions for successive angular rays and transverse sections of PHerc1218.

For each resolved winding and section, Mode 10B:

1. reconstructs the measured closed boundary \(r(\theta)\);
2. evaluates its perimeter by numerical arc-length integration;
3. assigns every sampled point a normalized material coordinate

\[
u(\theta)=
\frac{
\displaystyle\int_{\theta_0}^{\theta}
\sqrt{r(\varphi)^2+\left(\frac{dr}{d\varphi}\right)^2}\,d\varphi
}{
\displaystyle\oint
\sqrt{r(\varphi)^2+\left(\frac{dr}{d\varphi}\right)^2}\,d\varphi
};
\]

4. cuts all windings at the same radial reference \(\theta_0\);
5. maps \(u\in[0,1]\) to physical arc length along the flattened winding;
6. stacks the reconstructed transverse sections along the scroll axis.

No analytic ellipse is required. The measured PHerc1218 section profile therefore replaces the idealized crushed section used by the synthetic twin in Mode 7.

![Geometry-only reconstruction of PHerc1218](figures/rings3d.png)

*Figure 10B-1 — The same material points before and after the crush. Left: the cylinder reconstructed from the measured shape by arc length. Right: the measured crushed section. Colour identifies corresponding material points, not ink. The flattened sheet itself is Figure 10B-3 below.*

### Which way it reads

The reconstruction has an orientation, and it is not arbitrary.

**Ring 0 — the outermost winding — is the first column.** A book roll is
stored with the start of the text on the outside: the reader holds it in the
right hand, draws the free end leftwards, and winds the read portion onto the
left. The core is therefore the *end* of the work — which is why Herculaneum
end-titles survive, protected at the centre, and why loss of outer windings
costs the **opening** of a text rather than its close.

**The ink is on the inward-facing side, and is never exposed.** Papyrus is
written on the recto, the face with horizontal fibres, and the roll is wound
recto-inward. The text faces the core; the blank verso takes the outside. This
is the same recto-inward assumption the fibre-strain argument of Mode 8 rests
on, and it answers the obvious objection — writing on an exposed surface would
have destroyed the text before it could be read.

**One caveat on the horizontal axis.** The winding *sense* is not firmly
established for PHerc1218: it was set from a single multi-turn instance, and
the spiral constraints are mirror-symmetric, so a wrong sense mirrors the arc
axis. Until that is closed, a registered text could come out reversed. The
fix is at render time and costs nothing, but it has to be checked rather than
assumed.

This is what the flattening is for. The sheet is a **coordinate system**: once
each material point has a place, any per-point quantity can be registered onto
it — ink probability above all, but equally CT intensity, confidence, fibre
direction or local thickness. Whether the result reads is then a question the
geometry has made askable.

### Reconstructed extent

The current reconstruction covers the outer resolved portion of the scroll:

| quantity | reconstructed value |
|---|---:|
| resolved radial fraction | outer \(\sim 60\%\) |
| innermost resolved radius | 9.73 mm |
| crossing indices represented | 46 |
| transverse sections | 313 |
| samples per winding and section | 120 |
| measured cells | 92% |
| summed measured perimeter | 3.99 m |
| reconstructed sheet height | 173 mm |
| outer resolved winding length | 113.8 mm |
| inner resolved winding length | 61.1 mm |

Coverage is complete over the first metre of sheet length, remains approximately 94% to 2.9 m, and is still about 80% over the final resolved stretch. The decline beyond that point is treated as a segmentation limit, not as evidence of material loss.

---

### What the geometry measures

#### 1. The reconstruction passes an internal spiral-consistency test

For each measured winding perimeter \(L_i\), define the radius of a circle with the same perimeter:

\[
r_i=\frac{L_i}{2\pi}.
\]

For an Archimedean spiral of constant pitch \(p\), successive physical windings satisfy

\[
r_i=r_0-ip,
\]

and therefore

\[
L_i=L_0-2\pi p\,i.
\]

The equivalent radius must decrease linearly with physical winding number. That relation is not imposed by the flattening procedure: it is an independent consequence of a consistently indexed, approximately inextensible wound sheet.

Over the first forty resolved windings, the measured equivalent radii follow the expected linear relation with

\[
R^2=0.9998.
\]

The fit degrades after winding 45, reaching approximately \(R^2=0.94\) by winding 55 and \(R^2=0.83\) by winding 60. Because the outer range is exceptionally linear while the deterioration coincides with poorer crossing resolution, the conservative interpretation is that the degradation belongs to the segmentation rather than to a sudden change in papyrus pitch.

This test validates one property only: the recovered sequence is geometrically consistent with successive windings of a spiral over the well-resolved range. It does **not** prove that every individual correspondence or crossing label is correct.

![Spiral consistency and coverage](figures/peel.png)

*Figure 10B-2 — Four views of the peel. Top left: the flat sheet with the
crush displacement painted on it. Top right: winding length shrinking toward
the core. Bottom right: the reconstructed cylinder, the spiral-consistency
test.*

*Read the bottom-left panel with care.* It shows the fraction of heights at
which each crossing index is complete, and that curve **must** fall with index
whatever the papyrus did: the n-th crossing only exists on rays carrying at
least n+1 crossings. It is a property of the indexing, not a map of material
loss — see "A result that did not survive testing" below, where the
angle-independent control settles the question.

#### 2. Crossing indices are not identical to physical windings

The crossing list contains 46 resolved indices over a radial interval that corresponds, at the corroborated mean pitch of 173 µm, to approximately 48.5 physical windings.

Thus

\[
\frac{48.5}{46}=1.054,
\]

or about **1.054 physical windings per resolved crossing index**.

Equivalently, approximately

\[
1-\frac{46}{48.5}=5.2\%
\]

of the physical windings in this interval are not represented as separate crossing indices. They are most naturally interpreted as neighbouring turns merged by the segmentation.

The sheet length provides a second estimate of the same loss:

- sum of individually measured perimeters: **3.99 m**;
- spiral integral over the same radial interval: **4.24 m**;
- missing length: **0.25 m**.

The difference is 5.9% of the spiral-integrated total, or 6.3% when expressed relative to the measured 3.99 m. These percentages are not numerically identical to the 5.2% unresolved-turn fraction because perimeter changes with radius and the comparison has finite-range boundary effects. They are nevertheless of the same magnitude and point in the same direction.

The important closure is therefore not an artificial equality of rounded percentages. It is that two independent calculations — radial winding count and integrated sheet length — both require a small population of unresolved turns.

> **Geometry closes within the expected effect of merged windings.**  
> 46 crossing indices represent about 48.5 physical turns; the directly measured sheet is correspondingly shorter than the spiral integral.

#### 3. The crush displacement field is nearly depth-invariant

Once each boundary point has both an angular coordinate in the crushed section and a material arc coordinate on the reconstructed sheet, the crush can be expressed as an angular displacement field.

Across a factor of approximately 2.4 in radius, displacement profiles correlate at

\[
r\geq 0.959.
\]

The lower and upper halves of the sampled scroll height correlate at

\[
r=0.956.
\]

The remaining arc-length residual is approximately 0.20–0.33 mm against a displacement amplitude of about 4.0 mm.

The conclusion is practical: the same crush pattern appears throughout the resolved depth of the scroll. The outer windings, where segmentation is clearer, can therefore act as a calibration region for deeper windings, where individual crossings become ambiguous.

This is not a claim that every inner winding can already be recovered. It is evidence that a correction field measured outside may transfer inward without requiring an independent deformation model at every depth.

![PHerc1218 laid flat](figures/sheet.png)

*Figure 10B-3 — Angular displacement expressed in material coordinates across winding depth and scroll height. The persistence of the same pattern is the relevant result; the colour scale should remain fixed across all panels.*

---

### A result that did not survive testing

An earlier interpretation treated the declining completeness of high crossing indices as evidence that material loss increased towards the core.

That inference was wrong.

The \(n\)-th crossing can only exist on rays containing at least \(n+1\) crossings. A completeness curve indexed from the outside must therefore fall even for a perfectly preserved roll. The indexing also makes outer loss invisible by construction, because crossing 0 is defined as the outermost surviving crossing on each ray.

An angle-independent control resolves the ambiguity. If outer windings were systematically missing, the measured slice perimeter should decrease with crossing count. It does not:

\[
r=+0.084.
\]

A raw correlation between crossing count and outer radius gives approximately \(r=+0.31\), but that follows from the flattened shape of the section and is not evidence of erosion.

Mode 10B therefore makes **no claim of outer material loss** from crossing completeness. The missing crossing indices identified above are interior unresolved or merged turns.

Keeping this retraction in the record is part of the method: an acceptance test is useful only when it is allowed to overturn the story that motivated it.

---

### The measured section is not an ellipse

The measured PHerc1218 section is close to elliptical, but not fully described by an ellipse:

\[
R^2_{\mathrm{ellipse}}=0.948.
\]

More importantly, the measured displacement amplitude is approximately 40% greater than predicted by an equal-perimeter ellipse with the observed aspect ratio, and its maxima are shifted away from the ellipse symmetry points.

The approximately 2% difference between the two hemispheres is too small to explain that excess.

Possible causes include localized plastic deformation, inter-layer slip, adhesion, core constraints or nonuniform relaxation, but the present geometry does not distinguish among them. The excess displacement remains unresolved.

For that reason, Mode 10B uses the measured section profile directly. The ellipse remains useful as a controlled analytic reference in the synthetic twin, but it is no longer treated as a complete description of the real crush.

---

### Acceptance tests

The mode should be considered usable only while the following tests continue to pass on regenerated data.

| exam | criterion | current result |
|---|---|---:|
| A — arc-length bookkeeping | every flattened winding length equals its numerically integrated measured perimeter within numerical tolerance | **PASS** |
| B — spiral consistency | equivalent radius linearity over the first 40 resolved windings, \(R^2>0.995\) | **0.9998, PASS** |
| C — independent count closure | pitch-based physical turn count exceeds resolved crossing count by the same order required by the length deficit | **48.5 vs 46, PASS** |
| D — depth transfer | displacement-profile correlation remains \(r>0.95\) across the tested radial range | **\(\geq0.959\), PASS** |
| E — height transfer | lower-versus-upper displacement correlation remains \(r>0.95\) | **0.956, PASS** |
| F — degradation is declared | the pipeline must report the winding range after which spiral linearity deteriorates rather than silently extrapolating through it | **after \(\sim45\), PASS** |

The exact numerical tolerances should live in the script rather than only in this README section, so that future changes can fail automatically.

---

### Declared limits

1. **Only the outer resolved \(\sim60\%\) of the radius is reconstructed.** Windings inside 9.73 mm are not resolved and are not inferred here.
2. **The method assumes approximate inextensibility along each winding.** Local tearing, slip or plastic extension can violate that assumption.
3. **Crossing identity remains an input dependency.** Spiral linearity is a strong consistency test, not proof that every crossing is correctly labelled.
4. **The mean pitch is used only as a radial accounting scale.** Local wrap-to-wrap pitch measurements remain too unstable to support pointwise predictions.
5. **No ink is detected.** The output is a material-coordinate surface, not a readable text render.
6. **The inner degradation is not filled by interpolation.** Transferability of the outer displacement field is measured, but reconstruction beyond the resolved range remains future work.
7. **The real crush is not elliptical.** Analytic ellipse results are references, not substitutes for the measured section.
8. **The source measurements remain attributable to their publisher.** This reconstruction is an arc-length integration over the published per-ray crossings, not an independent re-segmentation of the CT volume.

---

### Material coordinates: the reusable output

The principal output of Mode 10B is not a PNG. It is a material coordinate system.

Each reconstructed point can be stored as, for example,

```text
(section_z, winding_id, arc_fraction, arc_length_mm, x_flat_mm, y_flat_mm)
```

with provenance and confidence fields attached to the crossing from which it was derived.

That coordinate system is independent of imaging modality. Once established, any scalar or vector quantity sampled from the original volume may be associated with the same material point:

```text
ink probability
raw CT attenuation
surface confidence
crossing confidence
fibre orientation
surface normal
local thickness
damage class
multispectral response
segmentation provenance
```

The relationship is analogous to texture coordinates on a three-dimensional mesh: geometry defines the support first; measurements are then projected onto it.

This separation matters because future ink models need not solve the geometry again. They need only estimate a quantity in the source volume and transfer it to the existing material coordinates.

---

### Future extensions

The following extensions are direct consequences of the present representation rather than claims of completed work.

#### Project CT or ink probability onto the sheet

If the source scan provides an intensity or ink-probability value \(I(x,y,z)\), each reconstructed material point can sample that field before flattening:

\[
I_{\mathrm{flat}}(u,z)=I\!\left(x(u,z),y(u,z),z\right).
\]

The flattening algorithm does not change. Geometry and reading remain separate stages.

A binary ink/empty label is possible, but retaining the continuous probability or attenuation value is preferable: thresholding can then be revised without recomputing the geometry.

#### Carry uncertainty into the flattened image

Every point should retain:

- crossing-position uncertainty;
- winding-identity confidence;
- local interpolation distance;
- spiral-fit residual;
- displacement-transfer residual;
- source-voxel support.

A flattened intensity map without its confidence map would look more certain than the underlying geometry warrants.

#### Transfer the measured displacement field inward

The observed depth invariance suggests a constrained inner reconstruction in which the outer field supplies a prior, while inner crossings and CT evidence determine local corrections.

The acceptance condition must remain strict: transfer is allowed only while held-out resolved windings are predicted within the measured 0.20–0.33 mm arc residual.

#### Replace the analytic crush in the synthetic twin

Mode 7 currently uses a controlled analytic section because it provides exact ground truth. Mode 10B adds the complementary object: a measured section profile.

Both should remain:

- the analytic ellipse for closed-form tests and known truth;
- the measured PHerc1218 profile for realistic deformation and segmentation stress tests.

The twin becomes more realistic without pretending that the measured profile supplies perfect labels.

#### Multi-modal registration

Because all measurements share the same material coordinates, geometry, ink probability, fibres, thickness and damage can be compared point by point on one flattened domain.

That creates a common reference frame for methods that currently operate on different representations of the scroll.

---

### Role within the repository

Modes 1–5 ask whether the scribe's spatial grid survives on a rendered surface. Mode 6 evaluates whether the crossing count is geometrically plausible. Modes 7–9 use an idealized scroll to make predictions about winding, strain and work size.

Mode 10B links those two halves.

It reconstructs a material sheet from measured real-scroll geometry, tests whether the winding sequence behaves like a spiral, quantifies unresolved turns, measures the crush displacement, and exposes the point at which segmentation stops supporting the reconstruction.

It therefore establishes the substrate on which the earlier text-grid tools may later operate:

\[
\text{measured crossings}
\rightarrow
\text{material coordinates}
\rightarrow
\text{registered CT / ink}
\rightarrow
\text{grid-based validation}.
\]

**Measure the geometry first; read the text later.**

---

### Credit and provenance

The reconstruction depends on @iyando's publication of per-ray crossing positions rather than only per-scroll aggregates. The flattened sheet, perimeter sums, spiral test and displacement field are derived from those measurements by arc-length integration.

The raw crossing source, preprocessing steps, commit identifier and any filtered subsets used to regenerate the figures should be recorded in `docs/data_sources.md`. Quantitative claims in this section should be regenerated from the scripts and not copied manually into release notes.

---

## Supporting analyses
- `scripts/experiment_A_degradation.py` — controlled-degradation validation of the
  metric (rotation, shear, warp, noise, erasure): the score falls monotonically, which
  is the calibration a ranking metric needs.
- `scripts/delta_beta_ink.py` — δ/β contrast of lead-bearing ink vs papyrus from
  tabulated scattering data. Key result: the exploitable channel is **K-edge
  subtraction (~88 keV)**, not differential phase — with the caveat that
  phase-retrieved public volumes may suppress exactly that absorption signal.
- `scripts/make_rank_candidates.py` and `scripts/orient_acceptance_test.py` —
  the acceptance tests for the `rank` and `orient` modes. They ship with the
  code deliberately: every mode in this repository carries the test that
  gates it, including the ones that failed before they passed.

---

## Lessons (kept on purpose)
Our first line-spacing estimate (4.45 mm) was a resolution artifact: on a 13 mm strip
the FFT has only 3–4 usable bins in the whole 3–8 mm range, and the "peak" was bin
k = 3 of the strip height. Finding it, fixing it (cycle gating + spatial-domain
estimation) and reporting it is part of the method. Earlier script versions live in
`archives/`, each superseded by the integrated `scripts/grid_metric.py`.

## What is in this repo

```
vesuvius-topological-grid/
├── README.md
├── LICENSE.md
├── requirements.txt
├── docs/
│   ├── technical_note_revised.pdf     ← the technical note (start here)
│   └── data_sources.md                ← how to obtain the input images
├── scripts/
│   ├── synthetic_scroll_twin.py       ← the twin: obra → scroll → crush
│   ├── text_layout_predictor.py       ← the falsifiable column map
│   ├── fibre_strain.py                ← where the crush cracks the sheet
│   ├── displacement_field.py          ← where the crush put each point
│   ├── work_size.py                   ← work ↔ roll size, and the
│   │                                     unknown-work discriminator
│   ├── void_aware_expected_n.py       ← layer-count reconciliation
│   ├── orient_acceptance_test.py      ← acceptance test for orient mode
│   ├── grid_metric.py                 ← analyze / compare / rank
│   ├── make_rank_candidates.py        ← acceptance test for rank mode
│   ├── phase_tracking.py              ← period-phase search; phase glitches
│   ├── epoch_folding_prototype.py
│   ├── experiment_A_degradation.py
│   └── delta_beta_ink.py
├── figures/                           ← output figures
└── archives/                          ← earlier script versions + results
```

## Quick start

```bash
# 1. Clone
git clone https://github.com/Diego-dcv/vesuvius-topological-grid.git
cd vesuvius-topological-grid

# 2. Environment (Python 3.10+)
python3 -m venv venv
source venv/bin/activate                # Linux/macOS   (venv\Scripts\activate on Windows)
pip install -r requirements.txt

# 3. Get the input images — see docs/data_sources.md for permanent links.
#    You need at least one rendered surface (PNG/WEBP) from Paris 4.

# 4. Measure the scribe's grid on one surface
python scripts/grid_metric.py analyze IMAGE.png --width-mm 129

# 5. Compare two ink predictions of the same region
python scripts/grid_metric.py compare A.png B.png --width-mm 129 --label-a Model_A --label-b Model_B

# 6. Screen several candidates of the same region (external reference required)
python scripts/grid_metric.py rank candA.png candB.png candC.png \
    --width-mm 129 --letters-mm 1.83 --lines-mm 2.79

# 7. Detect buried line structure by epoch folding
python scripts/epoch_folding_prototype.py --input surface.png --width-mm 129 --noise-test

# 8. Search the period and phase, and track the phase for glitches
python scripts/phase_tracking.py search IMAGE.png --width-mm 129 --axis lines

# 9. Map the local tilt of the writing baseline
python scripts/grid_metric.py orient IMAGE.png --width-mm 129 \
    --letters-mm 1.83 --lines-mm 2.79

# 10. Void-aware layer-count reconciliation (runs its acceptance test with no args)
python scripts/void_aware_expected_n.py

# 11. Build the synthetic twin for a work of N columns (no input images needed)
python scripts/synthetic_scroll_twin.py build --columns 95 --script greek \
    --csv twin_truth.csv --plot twin.png

# 12. What the crushed section implies about the length of the work
python scripts/synthetic_scroll_twin.py sweep --script greek --plot sweep.png

# 13. Sheet joins: the kollesis landmarks and their angular chirp
python scripts/synthetic_scroll_twin.py kollesis --columns 95 --plot koll.png

# 14. Export a voxel volume as a test bench (fused turns, crossed fibers)
python scripts/synthetic_scroll_twin.py volume --columns 95 --z-window 8 \
    --voxel-um 60 --fuse 20,24,60,150 --fibers --out twin_vol.npy

# 15. The falsifiable column map for the real scroll; anchors tighten it
python scripts/text_layout_predictor.py predict --columns 95 --csv map.csv
python scripts/text_layout_predictor.py calibrate --anchors anchors.csv

# 16. What the implied work depends on (never quote a figure without this)
python scripts/synthetic_scroll_twin.py sensitivity

# 17. Where the crush cracks the sheet, and where it leaves it intact
python scripts/fibre_strain.py map --plot fibre.png

# 18. Which work fits a measured section, and which rolls match nothing
python scripts/work_size.py identify --section 42 21
python scripts/work_size.py population --section 42 21

# 19. Acceptance tests (no arguments, no data required)
python scripts/synthetic_scroll_twin.py test
python scripts/text_layout_predictor.py test
python scripts/fibre_strain.py test
python scripts/work_size.py test
python scripts/phase_tracking.py test
```

Steps 10-18 need no input images: everything from mode 7 onward runs on
geometry alone. The twin and the predictor run on geometry
alone.

Scripts write PNG figures (and CSVs) to the working directory. A Paris-4-sized image
analyses in under a minute on a laptop.

## Use case
The tool does not read new letters or replace existing segmentation methods. It offers a
quality-assurance and arbitration layer that integrates as a callable step alongside
existing pipelines (Henderson spiral fitting, Thaumato Anakalyptor, Volume Cartographer,
VC3D) without modifying their architecture: rank candidate surfaces by grid survival,
localize zones where the grid breaks, and measure agreement between independent ML
readings.

## Declared limitations
- **The grid measures geometric regularity, not textual correctness.** A coherent grid
  is necessary but not sufficient: a model can produce coherent hallucinations. Final
  calibration needs papyrological ground truth held by the Vesuvius Challenge team.
- **Signature calibration needs a minimum well-resolved region** to extract the
  per-scribe periods; fully compressed scrolls without a clean zone need an external
  reference value (this is what `rank --letters-mm/--lines-mm` is for).
- **Atypical zones legitimately lack the grid** — margins, intercolumnia, tears, pin
  holes, illustrations — so the tool should be paired with a zone-type prior before its
  flags are read as errors.

## Community validation
The winding-count invariant (§2 of the technical note) has been independently
implemented and scaled by other Vesuvius Challenge contributors — as a (z, θ) ray
profile on stitched PHerc1218, and as a 35-scroll winding atlas. Their formulations
improve on the bare invariant and are credited in the note's next revision; details and
links live in the technical note and the community threads.

## Integrity note
Nothing here reveals or reconstructs hidden text. Per Vesuvius Challenge rules, any
actual text recovery requires the team's written approval before public posting; these
tools are methodology only. Developed with AI assistance under a documented
human-in-the-loop workflow; all quantitative claims are regenerated by running the
scripts.

## Citation
> Diego_dcv (2026). *vesuvius-topological-grid: an ML-independent structural metric
> for Herculaneum scroll surfaces.* Zenodo. https://doi.org/10.5281/zenodo.21464028


## Contact
Diego — Madrid, Spain. For substantive technical discussion, please open an issue in
this repository.

## License
MIT License (see `LICENSE.md`). Offered as a contribution to the open scientific effort of
the Vesuvius Challenge. It does not claim priority on any specific finding; if
equivalent approaches have been explored internally by the team, the author would be
glad to be informed.
