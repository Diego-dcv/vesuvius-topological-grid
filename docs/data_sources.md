# Data sources

This repository does not redistribute the rendered surface images themselves —
they belong to the Vesuvius Challenge and the Grand Prize 2023 winning team.
This document explains how to obtain the public images used for validation.

## Grand Prize 2023 — PHerc. Paris 4 (Scroll 1)

The Grand Prize 2023 was awarded to Youssef Nader, Luke Farritor, and Julian
Schilliger for the first reading of substantial passages from a Herculaneum
scroll. Their submission included rendered surfaces produced by three
different ML architectures over the same geometric segmentation.

### Primary sources

- **Vesuvius Challenge official page**:
  [scrollprize.org/grandprize](https://scrollprize.org/grandprize)
  Contains the announcement, the technical paper, and links to the rendered
  surfaces.

- **Youssef Nader's repository**:
  [github.com/younader/Vesuvius-Grandprize-Winner](https://github.com/younader/Vesuvius-Grandprize-Winner)
  Contains the TimeSformer model code and example outputs.

### Specific images used in this work

The two images compared in `compare_versions.py` are public renders of the
same Paris 4 region produced by different ML architectures:

1. **TimeSformer version (Nader)**: typically named `youssef_text_wbb.png` or
   similar. Approximately 158 × 19 mm at ~7.91 µm/pixel resolution.

2. **Squeeze-net version (Hao Qian)**: hosted at
   [scrollprize.org/img/grandprize/sq_text_wbb.webp](https://scrollprize.org/img/grandprize/sq_text_wbb.webp).
   Approximately 129 × 13 mm.

Both versions operate on the same geometric segmentation but produce different
ink detections. They are ideal for testing the discriminative power of the
topological grid metric.

## Resolution parameter

The default `--pixel-size 7.91` matches the original CT resolution. Some
rendered surfaces are downsampled during the unwrapping process; if the
detected periods all scale by the same factor, the actual pixel size differs
from the default. Adjust `--pixel-size` accordingly.

For Paris 4, common effective resolutions are 7.91 µm/pixel (full resolution)
and 15.82 µm/pixel (one downsample step).

## Other Vesuvius Challenge data

For broader access to the CT volumes and segmentations:

- **Data portal**: [scrollprize.org/data](https://scrollprize.org/data)
  Requires registration. Volumes are large (hundreds of GB to TB per scroll).

- **Discord community**: linked from
  [scrollprize.org](https://scrollprize.org). Active technical discussion
  and pointers to derived datasets.

This tool operates on rendered surfaces (2D images), not on the 3D volumes
directly, so the lighter-weight download is sufficient for the analysis here.

## Citing the data

If you use these images in your own work, please cite the Vesuvius Challenge
team and the Grand Prize 2023 winners according to their respective
guidelines. The author of this repository claims no rights over the input
data, only over the analysis tool itself (MIT license, see `LICENSE`).

## PHerc. 1218 — geometry used by mode 7 (Twin & Predict)

Every headline number in mode 7 rests on the parameters below. They are
**inputs, not results**: if any of them is wrong, the twin and the predictor
are wrong with it. Provenance and status are given for each, because two of
them are weaker than the word "measured" would suggest.

| parameter | value | provenance | status |
|---|---|---|---|
| crushed section | 42 × 21 × ~190 mm, flattened 2:1 | reconstructed by this author from iyando's published aggregates on stitched PHerc1218 (`vesuvius-sheet-tools`); cross-confirmed by two independent quantities — the `ratio_va` dips and the `pitch_ref` values on the 0/180 vs 90/270 axis | **derived from community data, cross-confirmed** |
| fold positions | 0° / 180° on the long axis | same reconstruction; predicted in advance from the onion-skin-paper analogy and then confirmed | **predicted, then confirmed** |
| edge discontinuities | 265–280° (15° wide) and 75–110° (35° wide) | iyando's terminus-cluster hunt; the two clusters remain unresolved at one-slab margin. Together with the creases they explain the 90°-period harmonic (phase minima at 87/177/267/357°) | **measured, ambiguous** |
| winding pitch (mean) | 173 µm | **two independent measurements on THIS scroll agree**: iyando's stitched value of 173 and pscamillo's winding-atlas value of 172.8 for PHerc1218 at pyramid level 1. Not to be confused with the atlas *collection median* of 187.3 µm across 36 scrolls, which is a different quantity and does not apply here | **corroborated** |
| winding pitch (local) | — | **not usable.** Wrap-to-wrap spacing is reported as inconsistent even between adjacent index pairs, useful at most as an initialization (sean/bruniss, community channel). The mean over ~70 turns is a well-constrained quantity; the local pitch is not, and no result here may rest on it | **unusable — see below** |
| winding turns | ~70 | **not an independent measurement.** It follows from the section, the pitch and the assumed umbilicus: `n = (r_out − r₀) / p` | **derived** |
| umbilicus radius r₀ | 4.1 mm | **assumed.** Chosen as the value that makes ~70 turns consistent with a 173 µm pitch. Plausible for a Herculaneum roll, but not measured here | **free parameter** |
| page height | 200 mm (twin default) | inside the measured population envelope for intact Herculaneum rolls, **19–24 cm**, recorded above from the PHerc. 1667 unwrapping paper. (A Wikipedia infobox gives "16 cm" for Paris 4 in an ambiguous field; it was briefly taken here as a correction and should not have been — a catalogue infobox does not outrank a sourced population measurement) | **assumed, and consistent with the population** |

### Two consequences that must travel with any number quoted from mode 7

**1. The turn count cannot corroborate the section, because it is derived
from it.** Test C in `synthetic_scroll_twin.py` reports that the measured
section implies ~69.7 turns "against ~70 measured independently". That
framing is wrong: with the section and the pitch fixed, the turn count is a
function of r₀ alone, and r₀ was chosen to give 70.

| r₀ assumed | implied work | implied turns |
|---|---|---|
| 3.0 mm | 99 columns | 76.3 |
| 3.5 mm | 97 columns | 73.2 |
| **4.1 mm** | **95 columns** | **69.7** |
| 5.0 mm | 92 columns | 64.7 |
| 6.0 mm | 87 columns | 58.8 |

The honest statement is the inverse one, and it is still falsifiable: *if*
the winding count is ~70 and the pitch is 173 µm, *then* the umbilicus must
be ~4.1 mm — which a raw-CT look at the core would confirm or kill.

**2. The implied length of the work moves with the pitch.** For PHerc1218 the
mean pitch is corroborated at ~173 µm by two independent methods, so the
first row below is the working figure. The others are retained to show the
sensitivity, not as alternatives for this scroll:

| pitch | what it is | implied work | implied turns |
|---|---|---|---|
| **173 µm** | **PHerc1218, iyando 173 / atlas 172.8 — agreeing** | **95 columns** | **69.7** |
| 187.3 µm | atlas median over 36 scrolls — a collection statistic, not a 1218 value | 88 columns | 64.7 |
| 207 µm | the same median at level 2, before the merged-sheet correction | 78 columns | 58.2 |

A ~7 % change in pitch moves the implied work by ~7 columns, so any "the
section implies N columns" claim must still name the pitch it assumed.

**3. Nothing here may use a LOCAL pitch.** The mean over ~70 turns is well
constrained; wrap-to-wrap spacing is not, and is reported as inconsistent
even between adjacent index pairs. Uses divide accordingly:

| rests on | status |
|---|---|
| mean pitch — sheet length, capacity, implied work | fine |
| local pitch — per-column angles, the smoothness of the kollesis chirp | weakened; treat the idealized figures as properties of the twin, not predictions about a real scroll |
| neither — the neutral angle and the fold/flat strain ratio | untouched |

**Resolution level — resolved.** 27 of 41 published surface predictions are
level 0 rather than level 2, and the `L<k>` token in the filename is
load-bearing; a measurement that assumes one level across the collection
silently mixes resolutions, which is what produced the 207 → 187.3 µm
correction above. For the aggregates used here the level is stated by their
author: the PHerc1218 cell CSV is on the **L1 grid at 17.28 µm/voxel**
(2 × 8.64 µm, straight from the bucket metadata), with pitch and span already
converted to physical units. So the section reconstruction is L1, not a mix.

**Phantom sheet — does not reach these figures.** Published m7 surface
predictions can mark sheet where the masked CT is identically zero; a
36-scroll audit puts **PHerc1218 at 58.6 %** of predicted voxels in that
class. That would have been a serious inheritance problem, because the
section here is reconstructed from aggregates over those predictions. It is
not one: everything downstream of the cleaning step in
`vesuvius-sheet-tools` — instance labels, constraint pack, fitted surfaces —
descends from CT>0-gated data, so the phantom class never enters the
aggregates. Confirmed by their author on the same crop the cleaning figure
comes from, where the provable class is exactly 50.0 % of predicted voxels
and a small-component filter removes a further 18.4 %.

Note the direction: phantom sheet would have made the section *larger*, so
its absence does not soften the population finding below — the 3.24 cm
equal-perimeter diameter is a gated measurement, not an inflated one.

### Only two of the three grid numbers are periods

Worth stating before any of them is measured spectrally, because it decides
which failures to expect.

**Line spacing is a real period** — the scribe holds a constant line height.
**Column period is a real period** — columns are laid out at a regular
interval. **Letter pitch is not.** Greek majuscule is not monospaced: iota is
narrow, omega and mu are wide, and in prose the right edge of a column is
ragged precisely because of it. What is called "letter pitch" here is the
*mean* spacing of variable-width glyphs.

Two consequences:

1. Letters per line is a whole number on each line and a **fraction over a
   column**, varying line to line as the glyph mix varies. A fractional mean
   is expected, not an error.
2. The letter pitch is the member of the grid with the **weakest periodic
   signal**, so it is the one where a spectral search is least trustworthy —
   the opposite of the intuition that the smallest, most-repeated feature is
   the easiest to find. Any pitch measured this way carries a smearing that
   the other two do not.

### Grid self-consistency — measured, and resolved

Three grid quantities are related by arithmetic: written column width =
letter pitch x letters per line. The repository's own numbers gave **7.9
letters per line**, which is impossible for prose in scriptio continua. The
question was which number was wrong. It has now been settled **on the actual
Grand Prize render of Paris 4**, by a measurement that needs no physical
scale at all.

Measured on the render (8000 x 966 px):

| quantity | value |
|---|---|
| column period | 571 px |
| written column | 390 px (68 % of the period) |
| line spacing | 49 px |
| **letters per line, counted by eye on complete lines** | **16** |
| -> letter pitch | 390 / 16 = 24.4 px |

The decisive figure is a **ratio**, so no calibration argument touches it:

    column period / letter pitch   measured on the render : 23.4
                                   implied by 43 / 4.16   : 10.3
                                   discrepancy            : x2.27

One of the two is wrong by that factor, and the attribution is
straightforward:

- **If the 43 mm column period is right**, the true letter pitch is
  **1.83 mm** — and `BAND_LETTERS = (2.0, 4.5)` in `grid_metric` starts
  8 % above it. The search could never have found the answer; it returned the
  strongest peak inside a band that excluded the truth. `band_sensitivity.py`
  run on this render returns **JUMP**, which is exactly this failure.
- **If the 4.16 mm letter pitch is right**, the column period must be
  **98 mm**. Nothing supports that: roll reconstructions give 72–75 mm, and at
  98 mm the measured section would hold only 41 columns.

So the **column period is vindicated and the letter pitch is the failure** —
which also restores the roll-capacity checks below, where 43 mm is what makes
*On Piety* fit an ordinary roll. An earlier version of this file concluded the
opposite, on the strength of column widths measured on *other* scrolls; the
render settles it for this one.

Consequences, at the 43 mm scale: letter pitch **1.83 mm**, line spacing
**3.69 mm** (just under the 3.8–6.0 bracket from column-height arithmetic,
so the 2.79 mm on file is also low, by ~1.3x rather than the ~3x once
claimed here).

**The count is not certain, and the conclusion does not need it to be.** The
render is not a clean read, so the same arithmetic at 15, 16 and 17 letters:

| letters | letter pitch | period / pitch | vs the repo's 10.3 | pitch at the 43 mm scale |
|---|---|---|---|---|
| 15 | 26.0 px | 22.0 | x2.13 | 1.96 mm |
| **16** | 24.4 px | 23.4 | **x2.28** | 1.83 mm |
| 17 | 22.9 px | 24.9 | x2.42 | 1.73 mm |

The discrepancy runs 2.1-2.4x across the whole range, and in all three cases
the true pitch falls below the old 2.0 mm band floor -- by only 2 % at 15
letters, where the band-exclusion mechanism gets thin, but the ratio itself
does not care. The line spacing, 3.69 mm, does not depend on the count at all.

**Why the count had to come from a human.** An autocorrelation of the line
profile returns a strong peak at 17 px, which is NOT the letter pitch: Greek
majuscule carries several vertical strokes inside one letter -- pi, eta, mu,
nu -- so the strongest short-range periodicity is stroke-to-stroke, not
letter-to-letter, and a spectral estimator locks onto it. This compounds the
point above that the letter pitch is not a true period: it is both smeared by
variable glyph widths and shadowed by a stronger sub-letter periodicity.
Counting letters by eye is, for now, the reliable instrument.

**The fix is in the band, not in the number.** `BAND_LETTERS` must extend
below 2.0 mm before any letter pitch measured with it can be trusted.

### Writing grid (Paris 4, applied to the twin)### Writing grid (Paris 4, applied to the twin)

| parameter | value | provenance | status |
|---|---|---|---|
| letter pitch | 4.16 mm | measured in this repository (mode 1) on public Grand Prize 2023 renders of PHerc. Paris 4; replicated by independent implementations | **measured** |
| line spacing | 2.79 mm | as above, by spatial per-column estimation | **unsettled.** Plausible range from column-height arithmetic is 3–5 mm, which brackets the discarded 4.45 and sits just above 2.79. The production band (6.22–9.33) is a scoring tolerance from another scroll and is too generous — it implies ~14–20 lines per column |
| column period | 43.0 mm | as above | **vindicated** by the render measurement: 571 px against a 24.4 px letter pitch gives 23.4, consistent with 16 letters in 68 % of the period |
| letters per line | **16** | counted by eye on complete lines of the Paris 4 render; PHerc. 118 independently gives ~17 | **measured on this scroll** |
| letter pitch | 4.16 mm | **wrong by x2.27.** The true value at the 43 mm scale is 1.83 mm, which falls below `BAND_LETTERS = (2.0, 4.5)` — the search band excluded the answer | **contradicted; band must be widened** |

> The Paris 4 grid is applied to PHerc1218 on the assumption of workshop
> standardization. Different scroll, possibly different scribe: this is an
> assumption, not a measurement, and a column-width drift would show up as a
> smooth residual trend.

### The crush model tested against the real scroll

The twin's crush is an equal-perimeter 2:1 ellipse per turn. That predicts not
just "layers are further apart at the creases" but a **specific curve**: the
radial gap along a ray from the centroid should follow

    gap(theta)  ∝  1 / sqrt( cos²theta / R² + sin²theta )

which can be fitted to real data, and the fit returns R. Run against the
21,480 interior cells of the public PHerc1218 per-cell table
(`pitch_qa_cells.csv`, L1, 6° bins):

| | result |
|---|---|
| shape of the angular profile | **R² = 0.93** — the ellipse form fits |
| crease axis recovered by the fit | **0.0°** — independently, from the gap profile alone |
| crush ratio from the **pitch** | **1.55 : 1** |
| crush ratio from the **span** | **1.97 : 1** |

The shape is confirmed. The ratio is not: two quantities from the same table
disagree, and the disagreement is itself informative.

**Why they disagree, and what it confirms.** `counted_over_expected` is 19 %
**lower on the crease axis** (0.35) than on the flattened axis (0.43) — more
material unaccounted for at the creases. Void inflates the radial *span*
without moving the *median* gap, so a void excess at the creases raises the
span-based ratio and leaves the pitch-based one alone. That is exactly the
observed pattern.

And the void excess at the creases is what **mode 8 predicts**: bending strain
there is 3.4× the flattened sides, and carbonized papyrus cracks rather than
compresses. Cracking makes void. So the discrepancy between the two ratios is
independent corroboration of the cracking prediction, arriving from a column
nobody was looking at for that purpose.

**Honest bracket.** The pitch-based figure could itself be biased low if
cracking produces many *small* gaps rather than a few large ones, which would
pull the median down at the creases. So the true flattening sits somewhere in
**1.55–2.0 : 1**, and the neutral angle of mode 8 with it:

| crush ratio | neutral angle |
|---|---|
| 1.55 : 1 | 40.3° |
| 1.70 : 1 | 39.3° |
| 2.00 : 1 | 37.6° |

Which closes a loop worth noting: **measuring where the pristine sectors lie
would break this tie**, because the neutral angle depends on R and on nothing
else. The prediction and the open question are the same measurement.

### Ancient units: what was bought, and what the hand made

Every figure in this file is in millimetres, which is a unit from 1793 applied
to the work of a first-century-BC scribe. That is correct for *describing* the
artefact and misleading if it invites the expectation of round numbers. The
grid is not round in any ancient unit either:

| | in Roman digiti (18.5 mm) |
|---|---|
| column period 43 mm | 2.32 |
| written column 29.2 mm | 1.58 |
| line spacing 3.69 mm | 0.20 |
| letter pitch ~1.83 mm | 0.099 |

**That is the result, not a failure of the analysis.** There was no rule on
the scribe's table. Column width is a motor habit — which is why columns in
Greek rolls drift steadily leftward down the page, the signature of a hand
without a drawn guide. Looking for whole numbers here would be numerology:
with enough candidate units, something always fits.

**Where ancient units do bite is the sheet, because it was manufactured and
sold.** Pliny gives the papyrus grades by width in digiti — Augusta 13,
Liviana 11, amphitheatrica 9, emporitica 6, i.e. 240, 204, 166 and 111 mm.
Intact Herculaneum rolls stand **190–240 mm** tall, which is 10–13 digiti:
the good grades, in whole units. The twin's 200 mm page is ~11 digiti, a
standard grade.

So the division is clean and worth keeping in mind when reading any number
here: **what was purchased is in whole ancient units; what the hand produced
is not.** Roll height belongs to the first class, the writing grid to the
second.

### Papyrus manufacture (kollesis model)

- **Sheet joins and roll length.** Pliny the Elder, *Naturalis Historia*
  XIII.74–82: the *scapus* is described as not exceeding twenty sheets,
  giving a roll of roughly 11–12 Roman feet, hence kollemata of ~17–19 cm.
  **A measured Herculaneum roll now supersedes the inference**: Philodemus'
  *On Poems* II is 16 m long and made of 100 kollemata, i.e. **160 mm per
  sheet**. The repository default of 180 mm is 12 % high and should be read
  as an upper estimate. Pliny is close to these rolls in an arresting way -- he
  was prefect of the fleet at Misenum, some 30 km across the bay, and died at
  Stabiae in the very eruption that carbonized them. But close in place is not
  close in time: he describes the manufacture of the AD 70s, while the
  Philodeman library was assembled in the first century BC, over a hundred
  years earlier. His testimony is near-contemporary with the burial, not with
  the making -- a second reason the measured roll outranks it.
- **Multiple scapi were glued — this is documented, not hypothetical.** The
  same roll "was at first a roll of 70 sheets; a further 30 were glued on
  when the work proved to be long". This closes the question this repository
  raised about a 24.6-kollemata roll exceeding Pliny's scapus of twenty:
  exceeding it was normal practice, not evidence of unusual sheets. At
  160 mm per sheet the 4.43 m roll becomes 27.7 kollemata — comfortably a
  scapus plus a part.
- **Kollesis as double thickness.** Standard papyrological description of the
  glued overlap; modelled as an extra layer over `--kollesis-ov-mm`
  (default 15 mm). Not measured on any Herculaneum roll here.

### Latin at Herculaneum (layout regimes)

- The Latin portion of the Villa dei Papiri library is small relative to the
  Greek; a figure of roughly 60 Latin papyri is commonly reported. Verify
  against a current catalogue before citing a specific count.
- Identified Latin texts are largely **verse** (*Carmen de bello Actiaco*,
  Ennius, Lucretius, Caecilius Statius); PHerc. 1067 is the principal prose
  item. This is why `--script latin-verse` exists.
- **Interpuncts** appear in early rustic capital books including the
  Herculaneum *Carmen*, and fall out of use in Latin literary books by
  roughly the mid-second century AD.
- **No Latin Herculaneum roll has been measured to the precision of the
  Paris 4 Greek grid here.** The `latin-prose` and `latin-verse` metrics are
  **declared placeholders**; the script prints a runtime warning.

### Egyptian-language material

None is attested in the Villa dei Papiri library, a Greek philosophical
collection with a Latin appendix. The Egyptian element here is the
**support**, not the text: all papyrus was Egyptian manufacture, which is what
the kollesis model encodes.

### Community sources

The PHerc1218 quantities above come from open work by other Vesuvius
Challenge contributors, principally **iyando** (`vesuvius-sheet-tools`:
instance stitching, layer counting, the (z, θ) ray profile on stitched
PHerc1218) and **pscamillo** (35-scroll winding atlas). Provenance from a
Discord thread is legitimate when labelled as such; where a number below is
traceable to a specific thread or dataset release, the link belongs here.
