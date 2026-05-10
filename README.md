# vesuvius-topological-grid

A geometric validation tool for the segmentation of Herculaneum scrolls in the [Vesuvius Challenge](https://scrollprize.org).

The premise: any classical writing on papyrus or parchment produces, when correctly segmented and unrolled, a regular spatial grid (line spacing, letter spacing, column spacing) whose Fourier signature can be measured automatically. A correct segmentation produces this grid; an incorrect one breaks it. This makes the signature usable as a **ranking criterion** between segmentation alternatives during a layer-by-layer growth process — without replacing or modifying the existing pipeline.

This repository contains the Python implementation of the analysis, the empirical validation on the public Grand Prize 2023 rendered surfaces, and the technical proposal as a PDF.

---

## What is in this repo

```
.
├── README.md                        ← this file
├── proposal.pdf                     ← six-page technical proposal
├── requirements.txt                 ← Python dependencies
├── LICENSE                          ← MIT
├── src/
│   ├── analyze_grid.py              ← global Fourier analysis on a single image
│   └── compare_versions.py          ← local topological maps and comparison between two images
├── examples/
│   ├── analysis_fourier.png         ← reference output of analyze_grid.py
│   ├── fft2d.png                    ← reference 2D FFT
│   ├── comp_originals.png           ← two versions of Paris 4 side by side
│   ├── comp_scores.png              ← local topological maps of each version
│   └── comp_diff.png                ← consensus and divergence maps
└── docs/
    └── data_sources.md              ← how to obtain the input images
```

## Quick start

```bash
# 1. Clone and enter
git clone https://github.com/Diego-dcv/vesuvius-topological-grid.git
cd vesuvius-topological-grid

# 2. Set up environment (Python 3.10+)
python3 -m venv venv
source venv/bin/activate                # Linux/macOS
# venv\Scripts\activate                 # Windows
pip install -r requirements.txt

# 3. Get the input images (see docs/data_sources.md for permanent links)
#    You will need at least one PNG/WEBP rendered surface from Paris 4.

# 4. Run the global analysis
python src/analyze_grid.py path/to/rendered_surface.png

# 5. Run the comparison between two versions
python src/compare_versions.py path/to/version_A.png path/to/version_B.png
```

Both scripts produce PNG figures in the working directory. The analysis takes under a minute on a laptop for a Paris 4-sized image.

---

## What this tool does

### `analyze_grid.py`

Computes the global Fourier signature of a rendered surface. Outputs:

- **The three dominant spatial periods** (line, letter, column), automatically detected without assuming predefined values.
- **A six-panel figure** showing the original image, the Y projection (with peaks at the line spacing), the X projection (with peaks at letter and column spacing), and their respective spectra.
- **A 2D FFT** showing the cross structure that signals a regular grid (orthogonal peaks with harmonics).

Validated on the Grand Prize 2023 rendered surface of Paris 4 (Nader's TimeSformer version):

| Quantity | Predicted by papyrology | Detected (autocalibrated) |
|----------|------------------------:|--------------------------:|
| Line period (Y)   | ~5 mm    | 4.77 mm  |
| Letter period (X) | ~3 mm    | 3.77 mm  |
| Column period (X) | ~10–15 mm | 11.30 mm |

### `compare_versions.py`

Given two rendered surfaces of the same scroll (e.g. produced by two different ML architectures over the same geometric segmentation), computes:

- **Local topological maps**: for each window in the image, the spectral prominence of the expected peaks. High value = grid clearly present; low value = grid broken or absent.
- **Consensus map**: zones where both versions independently detect a clear grid. These are the most robust readings.
- **Divergence map**: zones where one version detects more structure than the other. These are candidates for papyrological review — one may be capturing real signal the other misses, or one may be hallucinating structure.

Validated on the two public versions of Grand Prize 2023 (TimeSformer by Nader, squeeze-net by Hao Qian). The two versions, while operating on the same geometric segmentation, produce statistically different local topological maps, with consensus zones and divergence zones automatically identified.

---

## Use case

The tool does not aim to read new letters or replace existing segmentation methods. It offers:

- **An arbitration metric** for layer-by-layer segmentation pipelines: when the algorithm generates several candidates for the next layer, rank them by topological coherence and accept the best.
- **A quality assurance layer** for already-produced rendered surfaces: localize zones where the grid breaks (likely segmentation errors, ML hallucinations, or genuine atypical regions).
- **A robustness measure** for ML readings: when two or more architectures agree on a zone's grid, the reading is robust; where they disagree, manual review is needed.

It integrates as a callable subroutine in any existing pipeline (Henderson, Thaumato Anakalyptor, Volume Cartographer, VC3D) without modifying the pipeline architecture.

---

## Declared limitations

- **The grid measures geometric regularity, not textual correctness.** A coherent grid is necessary but not sufficient: an ML model could produce coherent hallucinations. Final calibration requires papyrological ground truth available only to the Vesuvius Challenge team.
- **Autocalibration requires a minimum well-segmented region** in the scroll to extract the per-scribe periods. For scrolls completely compressed without an accessible clean zone, an a priori value would be needed.
- **Atypical zones legitimately lack the grid**: margins, intercolumnia, physical tears, illustrations. The tool must be combined with a prior classification of zone type to avoid flagging these as errors.

---

## Reproducing the validation

The two reference images are publicly available at scrollprize.org (Grand Prize 2023 renders by the Nader–Farritor–Schilliger team). See `docs/data_sources.md` for download instructions.

To reproduce the figures in `examples/`:

```bash
python src/analyze_grid.py path/to/youssef_text_wbb.png
python src/compare_versions.py path/to/youssef_text_wbb.png path/to/sq_text_wbb.webp
```

Note: the resolution parameter (`PIXEL_SIZE_UM` in the scripts, default 7.91 µm/pixel) may need adjustment depending on the version of the rendered surface used. The detected periods will scale linearly with this parameter; if all three detected values are off by the same factor, recalibrate.

---

## Future work

- Quantitative calibration of the topological score against papyrological reading rates on already-validated surfaces (requires VC internal data).
- Integration of the ranking subroutine into a specific segmentation pipeline (Thaumato Anakalyptor or other).
- Extension to other scribal traditions: the framework is corpus-agnostic but requires per-corpus validation.

---

## Citation

If this work is useful to your research or pipeline, please reference:

> Diego [Apellido]. *Topological grid as an iterative selection criterion in segmentation of Herculaneum scrolls*. Technical proposal, May 2026. https://github.com/Diego-dcv/vesuvius-topological-grid

---

## Contact

Diego — Madrid, Spain
For substantive technical discussion, please open an issue in this repository or contact me directly.

---

## License

MIT License. See `LICENSE` file.

This work is offered as a contribution to the open scientific effort of the Vesuvius Challenge. It does not claim priority on any specific finding, nor does it require attribution beyond standard scientific citation. If equivalent approaches have been explored internally by the team, the author would be glad to be informed and would withdraw any claim of novelty.
