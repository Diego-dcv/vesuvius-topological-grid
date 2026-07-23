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
`archive/`, each superseded by the integrated `scripts/grid_metric.py`.

## What is in this repo

```
vesuvius-topological-grid/
├── README.md
├── LICENSE
├── requirements.txt
├── docs/
│   ├── technical_note_revised.pdf     ← the technical note (start here)
│   └── data_sources.md                ← how to obtain the input images
├── scripts/
│   ├── void_aware_expected_n.py       ← layer-count reconciliation
│   ├── orient_acceptance_test.py      ← acceptance test for orient mode
│   ├── grid_metric.py                 ← analyze / compare / rank
│   ├── make_rank_candidates.py        ← acceptance test for rank mode
│   ├── epoch_folding_prototype.py
│   ├── experiment_A_degradation.py
│   └── delta_beta_ink.py
├── figures/                           ← output figures
└── archive/                           ← earlier script versions + results
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
```

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
MIT License (see `LICENSE`). Offered as a contribution to the open scientific effort of
the Vesuvius Challenge. It does not claim priority on any specific finding; if
equivalent approaches have been explored internally by the team, the author would be
glad to be informed.
