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

### Grid self-consistency — the check that fails

Three grid numbers are not independent. Letter pitch, letters per line and
written column width are related by arithmetic:

    written column width  =  letter pitch  x  letters per line

Herculaneum columns carry on the order of **17 characters per line** — the
figure Oxford papyrologists established for PHerc. 118 from the Seales 3D
composite, and use operationally to reassemble fragments. Put the repository's
own numbers in:

| | letter pitch | column period | written width | -> letters/line |
|---|---|---|---|---|
| as measured here | 4.16 mm | 43.0 mm | 33.0 mm | **7.9** |
| for 17 letters/line | 4.16 mm | ~75 mm | 70.7 mm | 17 |

**7.9 against 17 is not a discrepancy, it is an impossibility**, and it does
not depend on any other scroll: the two numbers measured here are mutually
incompatible. One of them is wrong.

**The community's production constants bear on this, but weakly, and an
earlier version of this file over-read them.** The `spiral-ink-metric-scale`
branch of `get_ink_metrics` restates the pixel priors physically:

    COL_WIDTH_MM  = 65.0            # expected text column width
    LINE_PITCH_MM = (6.22, 9.33)    # expected text-line pitch band

**These are scoring tolerances, not measurements.** They are priors for a
quality metric, derived on Scroll 1, and deliberately wide so that a range of
scrolls score well. Treating them as the true grid is a category error, and
this file made it: the line band was briefly written up here as settling the
question. It does not.

For the COLUMN they are corroborative, because they agree with independent
roll reconstructions (below) — 65 mm written plus an intercolumn lands on the
72–75 mm those give. For the LINE PITCH they are not: 9.33 mm would put about
14 lines in a Herculaneum column, and 6.22 mm about 20, against the few tens
such columns carry.

The one direct measurement found so far points the other way. The
phase-contrast tomography work on Herculaneum rolls describes "an 11 mm large
text of more than three lines" — **≤3.7 mm per line**, and closer to 2.8 mm if
four lines are meant.

So the honest position on the line pitch is a plausible range, not a value.
Run it backwards from the column instead: a 200 mm page leaves ~150 mm of
written height, and Herculaneum columns carry a few tens of lines.

| lines per column | implied line pitch |
|---|---|
| 40 | 3.75 mm |
| 35 | 4.29 mm |
| 30 | 5.00 mm |
| 25 | 6.00 mm |

That brackets the pitch at roughly **3.8–6.0 mm**. Two things follow, and
neither is a theory:

- **2.79 mm sits below the range** — it would need 54 lines in a column.
- **4.45 mm sits comfortably inside it**, at ~34 lines.

So the value this repository discarded as a resolution artefact is the one
the column arithmetic prefers, and its replacement is the one that does not
fit. That is not proof the correction was wrong — the two are not clean
harmonics of each other (4.45 / 2.79 = 1.60), so no simple aliasing story
connects them. It does mean the correction should not be treated as settled,
and that re-running the period search with a widened band is the way to
settle it.

Two independent roll reconstructions agree on the column figure:Two independent roll reconstructions agree on the column figure:

| roll | evidence | column period |
|---|---|---|
| Philodemus, *On Poems* II | 16 m of roll, 222 columns | **72.1 mm** |
| PHerc. 1667 | ~1.5 m unwrapped, ~20 columns | **75 mm** |
| Paris 4, implied | 4.16 mm x 17 letters + intercolumn | **~75 mm** |

All three cluster at 70–75 mm. The letter pitch survives; the **column period
does not**. **Why 43.0 comes out is not explained, and an earlier version of this file
claimed otherwise.** It said 43.0 sits near the bottom edge of
`BAND_COLUMNS = (40, 80)` and was therefore a band artefact. That reasoning is
wrong: the band *contains* 72 mm, so had 72 been the dominant peak the search
would have found it. Something in that render puts more spectral energy at
43 mm than at 72 mm, and what it is remains open. `grid_metric` records
neighbouring structure nobody has accounted for either — "a strong ~8 mm peak
of unknown origin has a ~32 mm relative at lower freq" — and the 40 mm lower
edge was chosen to exclude that relative. So the horizontal spectrum of this
render carries at least three features (~8, ~32, ~43 mm) with no established
origin, and the column period is being read off it.

That two implementations reproduced 43.0 does not rescue it: the same method
on the same render reproduces the same artefact.

**Consequence, and it is large.** The implied work for the measured
42 x 21 mm section scales inversely with the column period:

| column period | implied work |
|---|---|
| 43 mm (current) | 95 columns |
| 60 mm | 68 columns |
| **72 mm** | **57 columns** |
| 75 mm | 54 columns |

Until this is settled, treat every column count in this repository as
provisional by up to a factor of two. `band_sensitivity.py` and
`phase_tracking.py` exist to settle it and have not yet been run on the real
render.

### Writing grid (Paris 4, applied to the twin)

| parameter | value | provenance | status |
|---|---|---|---|
| letter pitch | 4.16 mm | measured in this repository (mode 1) on public Grand Prize 2023 renders of PHerc. Paris 4; replicated by independent implementations | **measured** |
| line spacing | 2.79 mm | as above, by spatial per-column estimation | **unsettled.** Plausible range from column-height arithmetic is 3–5 mm, which brackets the discarded 4.45 and sits just above 2.79. The production band (6.22–9.33) is a scoring tolerance from another scroll and is too generous — it implies ~14–20 lines per column |
| column period | 43.0 mm | as above | **contradicted — see the self-consistency check above.** Reproducible, but implies 7.9 letters per line against ~17 observed, and two roll reconstructions give 72–75 mm |
| letters per line | ~17 | PHerc. 118, established by Oxford papyrologists from the Seales 3D composite and used to reassemble fragments | external, measured |

> The Paris 4 grid is applied to PHerc1218 on the assumption of workshop
> standardization. Different scroll, possibly different scribe: this is an
> assumption, not a measurement, and a column-width drift would show up as a
> smooth residual trend.

### Papyrus manufacture (kollesis model)

- **Sheet joins and roll length.** Pliny the Elder, *Naturalis Historia*
  XIII.74–82: the *scapus* is described as not exceeding twenty sheets,
  giving a roll of roughly 11–12 Roman feet, hence kollemata of ~17–19 cm.
  **A measured Herculaneum roll now supersedes the inference**: Philodemus'
  *On Poems* II is 16 m long and made of 100 kollemata, i.e. **160 mm per
  sheet**, which is now the default; the earlier 180 mm was 12 % high.
  Pliny is close to these rolls in an arresting way — he was prefect of the
  fleet at Misenum, some 30 km across the bay, and died at Stabiae in the
  very eruption that carbonized them. But close in place is not close in
  time: he describes the manufacture of the AD 70s, while the Philodeman
  library was assembled in the first century BC, over a hundred years
  earlier. His testimony is near-contemporary with the burial, not with the
  making — a second reason the measured roll outranks it. The passage is
  also textually debated.
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
