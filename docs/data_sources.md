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
are wrong with it, and a reader must be able to check them without asking.

| parameter | value | where it comes from | status |
|---|---|---|---|
| winding pitch | 173 µm | | measured |
| winding turns | ~70 | | measured |
| crushed section | 42 × 21 mm (2:1) |  | measured |
| fold positions | 0° / 180° on the long axis | | measured |
| edge discontinuities | 265–280° and 75–110° | community (z, θ) ray-profile work on stitched PHerc1218 — see Community validation in the README | independent |

> ⚠ **Do not publish this table with the FILL INs open.** The three
> measured rows are what the Discord post stands on; a reader who cannot
> trace them will (correctly) discount the rest. If a number came from a
> community thread rather than a publication, say exactly that and link the
> thread — provenance from a Discord message is perfectly respectable when
> it is labelled as such.

### Writing grid (Paris 4, applied to the twin)

| parameter | value | source |
|---|---|---|
| letter pitch | 4.16 mm | measured in this repository (mode 1) and independently replicated — see README §Community validation |
| line spacing | 2.79 mm | as above; supersedes the earlier 4.45 mm, which was a resolution artefact (README §Lessons) |
| column period | 43.0 mm | as above |
| page height | 200 mm | conventional for Herculaneum rolls |

### Papyrus manufacture (kollesis model)

- **Sheet joins and roll length.** Pliny the Elder, *Naturalis Historia*
  XIII.74–82, on papyrus manufacture: the *scapus* is described as not
  exceeding twenty sheets, giving a roll of roughly 11–12 Roman feet. This
  yields kollemata of ~17–19 cm, the basis for the default
  `--kollesis-mm 180`. Pliny is a first-century source describing
  contemporary practice, which is the right period for Herculaneum, but the
  passage is textually debated — treat 180 mm as a **default to be varied**,
  not a constant.
- **Kollesis as double thickness.** Standard papyrological description of
  the glued overlap. The twin models it as an extra layer over an overlap
  width of `--kollesis-ov-mm` (default 15 mm).

### Latin at Herculaneum (layout regimes)

- The Latin portion of the Villa dei Papiri library is small relative to the
  Greek: a figure of roughly 60 Latin papyri is commonly reported. Verify
  against a current catalogue before citing a specific count.
- Identified Latin texts are largely **verse** (*Carmen de bello Actiaco*,
  Ennius, Lucretius, Caecilius Statius); PHerc. 1067 is the principal prose
  item. This is why `--script latin-verse` exists and why the verse regime
  is not a hypothetical.
- **Interpuncts** separating words appear in early rustic capital books
  including the Herculaneum *Carmen*, and fall out of use in Latin literary
  books by roughly the mid-second century AD.
- **No Latin Herculaneum roll has been measured to the precision of the
  Paris 4 Greek grid here.** The `latin-prose` and `latin-verse` letter and
  line metrics in `SCRIPTS` are therefore **declared placeholders**; the
  script prints a runtime warning and they must be overridden with
  `--letter-mm` / `--line-mm` before any number derived from them is
  quoted.

### Egyptian-language material

None is attested in the Villa dei Papiri library, which is a Greek
philosophical collection with a Latin appendix. The Egyptian element in this
work is the **support**, not the text: all papyrus was Egyptian manufacture,
which is precisely what the kollesis model encodes.  [scrollprize.org](https://scrollprize.org). Active technical discussion
  and pointers to derived datasets.

This tool operates on rendered surfaces (2D images), not on the 3D volumes
directly, so the lighter-weight download is sufficient for the analysis here.

## Citing the data

If you use these images in your own work, please cite the Vesuvius Challenge
team and the Grand Prize 2023 winners according to their respective
guidelines. The author of this repository claims no rights over the input
data, only over the analysis tool itself (MIT license, see `LICENSE`).
