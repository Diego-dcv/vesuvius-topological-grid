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
| page height | 200 mm | conventional for Herculaneum rolls; not measured on PHerc1218 in this work | **assumed** |

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

**Resolution levels.** 27 of 41 published surface predictions are level 0
rather than level 2, and the `L<k>` token in the filename is load-bearing; a
measurement that assumes one level across the collection silently mixes
resolutions. This is what produced the 207 → 187.3 µm correction above. The
level behind the PHerc1218 aggregates used here is not recorded — worth
establishing before any of these figures is quoted outside this repository.

### Writing grid (Paris 4, applied to the twin)

| parameter | value | provenance | status |
|---|---|---|---|
| letter pitch | 4.16 mm | measured in this repository (mode 1) on public Grand Prize 2023 renders of PHerc. Paris 4; replicated by independent implementations | **measured** |
| line spacing | 2.79 mm | as above, by spatial per-column estimation. Supersedes an earlier 4.45 mm, which was a resolution artefact (README §Lessons) — dispersion is large | **measured, dispersed** |
| column period | 43.0 mm | as above | **measured** |

> The Paris 4 grid is applied to PHerc1218 on the assumption of workshop
> standardization. Different scroll, possibly different scribe: this is an
> assumption, not a measurement, and a column-width drift would show up as a
> smooth residual trend.

### Papyrus manufacture (kollesis model)

- **Sheet joins and roll length.** Pliny the Elder, *Naturalis Historia*
  XIII.74–82: the *scapus* is described as not exceeding twenty sheets,
  giving a roll of roughly 11–12 Roman feet, hence kollemata of ~17–19 cm.
  This is the basis for the default `--kollesis-mm 180`. Pliny is a
  first-century source describing contemporary practice — the right period —
  but the passage is textually debated. Treat 180 mm as a **default to vary**,
  not a constant.
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
