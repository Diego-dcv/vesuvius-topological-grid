# 7 — Twin & Predict (`scripts/synthetic_scroll_twin.py`, `scripts/text_layout_predictor.py`)

*Moved unchanged from the README on 2026-09-06; the README now holds only the summary. Figures and scripts are referenced relative to the repository root.*


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
[`docs/data_sources.md`](../data_sources.md#pherc-1218--geometry-used-by-mode-7-twin--predict).
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

Give it a work and it builds the scroll around it. The work fixes the sheet
length; the sheet fixes the turns and the outer radius (spiral from a fixed
~4 mm umbilicus); ink lands on the grid the code carries (letter 4.16 mm, lines
2.79 mm, columns 43 mm, page 200 mm — the first two are the historical pair,
contradicted by the render check below and flagged by `grid_warnings()` at
runtime; pass `--letter-mm 1.83 --line-mm 3.69` for any production figure); then the whole thing is **crushed to the
measured deformation** — every turn mapped, arc-length preserving, onto a 2:1
ellipse of equal perimeter, folds at 0°/180° as measured on PHerc1218. Every
letter's position before and after crushing is known because we put it there:
**perfect ground truth**, per letter.

![Wound and crushed twin, one text line at mid-height](../../figures/twin_95col.png)

*One text line of a 95-column work, before and after the crush. Colour is the
column index; the section lands at 41.9 × 21.0 mm against 42 × 21 measured.*

`--fuse` collapses chosen turns over a chosen sector (verified: a 5-turn weld
drops ray crossings from 58 to 55 — the merge pathology `void_aware` must flag
at ratio < 1). `--fibers` adds crossed recto/verso striation, giving the
fiber-detector idea its first 3D target without the raw CT.

![Mid-z slice of the voxel volume with fused turns and fibers](../../figures/twin_volume_slice.png)

*Mid slice of the twin volume with finite-thickness sheets: contact on the
flattened axis, open gaps at the folds. Right: a kollesis join, with the
exported `kollesis_mask` ground truth overlaid in red.*

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
and the failure mechanism in [`docs/data_sources.md`](../data_sources.md),
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
Each join is a band of **double thickness every ~160 mm of arc**.

This matters because it is **detectable by thickness alone, with no ink
model** — the natural registration landmark for unwrapping. And its signature
is not imitable by software artefacts: consecutive joins sit a *fixed arc*
apart while the local circumference *grows* with radius, so the angular step
between successive joins shrinks monotonically outward — an **angular chirp**.
A slicing artefact is constant in index; a manufacturing periodicity chirps.

![Sheet joins in the crushed section and the angular chirp](../../figures/twin_kollesis.png)

*Left: the sheet joins of a 95-column twin placed in the crushed section —
thickness landmarks, no ink needed. Right: the chirp. Fixed arc, growing
circumference, so the angular step to the next join falls monotonically
outward. (Figure rendered with the earlier 180 mm sheet default; at the
measured 160 mm the join count is ~12 % higher.)*

**The arithmetic that followed has since been answered, and the answer was
the dull one.** A 4.43 m roll exceeds Pliny's scapus of twenty sheets, which
looked like it needed explaining. It does not: Philodemus' *On Poems* II "was
at first a roll of 70 sheets; a further 30 were glued on when the work proved
to be long". Gluing scapi together was ordinary practice. That roll also
supplies the **measured** sheet width — 16 m over 100 kollemata, i.e.
**160 mm** — which the twin now carries as its default; at 160 mm the 4.43 m
roll is 27.7 sheets.

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

![Crushed section as a function of work length](../../figures/twin_section_sweep.png)

*The section reads the length of the work, once a pitch and an umbilicus are
assumed. The layout regime sets the column period, so the same section means
95 columns of prose or 42 of hexameter.*

### Validation

Acceptance tests ship inside each script, criteria pre-registered.

**Twin** (`test`, run on a 72-column twin — the 95-column figures above give more
joins for the same reason: the work sizes the roll):

| exam | criterion | result |
|---|---|---|
| A — inextensibility | crushed perimeter = wound circumference per turn, rel. err < 0.1 % | **4.6e-10, PASS** |
| B — ground-truth round trip | analytic un-crush recovers every letter's s to < 10 µm | **0.00 µm, PASS** |
| C — umbilicus inversion | the inversion round-trips to < 0.1 turns, **and** r₀ is shown to be a free parameter (3–6 mm spans > 10 turns) | **0.000 turns, 18-turn spread, PASS** |
| D — kollesis chirp | join count = L/W; angular step monotone > 98 % | **21 joins (21.5 sheets), 659°→1806°, 100 %, PASS** |

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
6. Line spacing: the code default (2.79 mm) yields ~53 lines per column,
   taller than the 25–45 typical of opened rolls; the render-corrected
   3.69 mm yields ~41, inside it. `--line-mm` overrides, and production
   figures should use the corrected value.

---

