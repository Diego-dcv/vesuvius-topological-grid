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
