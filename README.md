# vesuvius-topological-grid

**An ML-independent structural metric for Herculaneum scroll surfaces — measure, arbitrate, detect, screen, orient, reconcile.**

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
    --letters-mm 4.16 --lines-mm 2.79
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
column 1. Only two of the four are measured: the section (42 × 21 mm,
cross-confirmed) and the column period (43.0 mm, Paris 4, replicated). The
pitch is contested (173 µm human anchor vs 187.3 µm from the corrected
35-scroll atlas) and the lead-in is assumed. Run `sensitivity` before quoting
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
`scripts/band_sensitivity.py` settles it: it sweeps the search band and
reports whether a detected period is a property of the image (STABLE) or of
the band we chose to look in (TRACKING / JUMP). Both `BAND_LETTERS` and
`BAND_COLUMNS` currently return values within ~10 % of a band edge; only the
line spacing sits comfortably interior.

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

And a falsifiable arithmetic consequence: 4.43 m of sheet is **24.6 kollemata,
above Pliny's scapus of twenty** — so either the roll was made by gluing more
than one scapus, or the sheets were wider than standard. Real kolleseis in the
CT would say which.

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

| assumed pitch | source | implied work | implied turns |
|---|---|---|---|
| 173 µm | community human anchor | 95 columns | 69.7 |
| **187.3 µm** | **35-scroll winding atlas, level 1** | **88 columns** | **64.7** |
| 207 µm | same atlas at level 2, since corrected | 78 columns | 58.2 |

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
│   ├── void_aware_expected_n.py       ← layer-count reconciliation
│   ├── orient_acceptance_test.py      ← acceptance test for orient mode
│   ├── grid_metric.py                 ← analyze / compare / rank
│   ├── make_rank_candidates.py        ← acceptance test for rank mode
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
    --width-mm 129 --letters-mm 4.16 --lines-mm 2.79

# 7. Detect buried line structure by epoch folding
python scripts/epoch_folding_prototype.py --input surface.png --width-mm 129 --noise-test

# 8. Map the local tilt of the writing baseline
python scripts/grid_metric.py orient IMAGE.png --width-mm 129 \
    --letters-mm 4.16 --lines-mm 2.79

# 9. Void-aware layer-count reconciliation (runs its acceptance test with no args)
python scripts/void_aware_expected_n.py

# 10. Build the synthetic twin for a work of N columns (no input images needed)
python scripts/synthetic_scroll_twin.py build --columns 95 --script greek \
    --csv twin_truth.csv --plot twin.png

# 11. What the crushed section implies about the length of the work
python scripts/synthetic_scroll_twin.py sweep --script greek --plot sweep.png

# 12. Sheet joins: the kollesis landmarks and their angular chirp
python scripts/synthetic_scroll_twin.py kollesis --columns 95 --plot koll.png

# 13. Export a voxel volume as a test bench (fused turns, crossed fibers)
python scripts/synthetic_scroll_twin.py volume --columns 95 --z-window 8 \
    --voxel-um 60 --fuse 20,24,60,150 --fibers --out twin_vol.npy

# 14. The falsifiable column map for the real scroll; anchors tighten it
python scripts/text_layout_predictor.py predict --columns 95 --csv map.csv
python scripts/text_layout_predictor.py calibrate --anchors anchors.csv

# 15. What the implied work depends on (never quote a figure without this)
python scripts/synthetic_scroll_twin.py sensitivity

# 16. Acceptance tests for both (no arguments, no data required)
python scripts/synthetic_scroll_twin.py test
python scripts/text_layout_predictor.py test
```

Steps 10-16 need no input images: the twin and the predictor run on geometry
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
