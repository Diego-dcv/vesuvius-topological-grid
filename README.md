# vesuvius-topological-grid

**An ML-independent structural metric for Herculaneum scroll surfaces — measure, arbitrate, detect.**

Ancient writing has a grid: equally spaced lines, regular letter pitch, columns on a
module — like the structural grid of a building. If a virtual unwrapping is correct,
that grid survives; if it fails, the grid breaks. This repository turns that
observation into three small, reproducible tools. None of them reads text; all of
them run in seconds on a laptop.

## 1 — Measure (`scripts/grid_metric.py`)
Detects the scribe's spatial signature on a rendered surface via windowed spectral
prominence, with **cycle gating** (a component only enters a window's score if the
window holds ≥3 cycles of its period — see *Lessons*, below).

On the public PHerc. Paris 4 surfaces it recovers, unsupervised:
- letter pitch **4.16 mm** and column period **43.0 mm** — replicated exactly by two
  independently written implementations;
- line spacing measured *spatially, per column* (~2–4 mm, wide spread on 13 mm strips
  — the uncertainty is part of the result).

## 2 — Arbitrate (consensus / divergence maps)
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

## 4 — Screen (`rank` mode) *(new, v3)*

Given several candidate renders of the **same region** (e.g. alternative
segmentation parameterizations), `rank` scores each by how well the scribe's
grid survives and orders them — a selective screen, never a generator: it ranks
existing candidates, it does not place windings (see the pitch-variability
caution raised by sean bruniss in the community threads).

```bash
python scripts/grid_metric.py rank candA.png candB.png candC.png \
    --width-mm 129 --letters-mm 4.16 --lines-mm 2.79
```

**Scoring (v3).** Axis-aligned 2D-FFT cross energy, ring-normalized: grid
energy must sit at the scribe's frequencies *and* square to the page. Rotation
moves the peaks off-axis, line-wobble warp smears them; each peak is compared
to its own frequency ring, so resampling smoothness cancels out. Aggregation is
by median across windows.

**Reference signature is external by design** (workshop-standardization
principle): known corpus values are passed in via `--letters-mm/--lines-mm`, or
measured once on a trusted source — never calibrated from the candidate pool,
so degraded candidates cannot contaminate the ruler.

**Validation.** The acceptance test ships in the repo
(`scripts/make_rank_candidates.py`): one real Paris 4 strip plus rotated,
line-wobbled and noisy copies; the original must rank first. Current status,
kept honest:

| exam | result |
|---|---|
| order (original first) | **passes** |
| line-wobble warp (classic unwrap error) | punished −24 % |
| rotation / noise | below original, thin margins (~3 % median vs rotation) |

The thin rotation margin is expected physics on a 13 mm strip (letter pitch is
nearly rotation-invariant; the discriminating line component is cycle-starved)
and should widen on taller strips. **Use accordingly:** trust `rank` to flag
clearly broken geometry; treat close scores as inconclusive; it does not
arbitrate between two good candidates.

Two earlier scoring designs failed this same test (1-D projections; pooled
calibration); their diagnoses are preserved in the commit history — the
acceptance test is the gate, and it stays in the repo.

## Supporting analyses
- `scripts/experiment_A_degradation.py` — controlled-degradation validation of the
  metric (rotation, shear, warp, noise, erasure): the score falls monotonically, which
  is the calibration a ranking metric needs.
- `scripts/delta_beta_ink.py` — δ/β contrast of lead-bearing ink vs papyrus from
  tabulated scattering data. Key result: the exploitable channel is **K-edge
  subtraction (~88 keV)**, not differential phase — with the caveat that
  phase-retrieved public volumes may suppress exactly that absorption signal.

## Lessons (kept on purpose)
Our first line-spacing estimate (4.45 mm) was a resolution artifact: on a 13 mm strip
the FFT has only 3–4 usable bins in the whole 3–8 mm range, and the "peak" was bin
k = 3 of the strip height. Finding it, fixing it (cycle gating + spatial-domain
estimation) and reporting it is part of the method. Earlier versions live in
`archive/`, each with the correction that superseded it.

## Integrity note
Nothing here reveals or reconstructs hidden text. Per Vesuvius Challenge rules, any
actual text recovery requires the team's written approval before public posting;
these tools are methodology only. Developed with AI assistance (documented
human-in-the-loop workflow); all quantitative claims are regenerated by running the
scripts.


## What is in this repo

```
vesuvius-topological-grid/
├── README.md            
├── docs/
│   └── technical_note_revised.pdf
├── scripts
│   ├── grid_metric.py
│   ├── make_rank_candidates.py        
│   ├── epoch_folding_prototype.py
│   ├── experiment_A_degradation.py
│   └── delta_beta_ink.py
├── figures/             
├── archive/
│   └── results/            
└── requirements.txt     
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
pip install -r requirements.txt
python scripts/grid_metric.py analyze IMAGE --width-mm 129
python scripts/epoch_folding_prototype.py --input surface.png --width-mm 129 --noise-test

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

> Diego_dcv *Topological grid as an iterative selection criterion in segmentation of Herculaneum scrolls*. Technical proposal, May 2026. https://github.com/Diego-dcv/vesuvius-topological-grid

---

## Contact

Diego — Madrid, Spain
For substantive technical discussion, please open an issue in this repository or contact me directly.

---

## License

MIT License. See `LICENSE` file.

This work is offered as a contribution to the open scientific effort of the Vesuvius Challenge. It does not claim priority on any specific finding, nor does it require attribution beyond standard scientific citation. If equivalent approaches have been explored internally by the team, the author would be glad to be informed and would withdraw any claim of novelty.


