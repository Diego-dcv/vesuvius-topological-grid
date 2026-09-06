# vesuvius-topological-grid

**Geometry instruments for Herculaneum scrolls — no ML, no text reading, every claim with its exam and its checker.**

Ancient writing has a grid: equally spaced lines, regular letter pitch,
columns on a module — like the structural grid of a building. If a
virtual unwrapping is correct, that grid survives; if it fails, the
grid breaks. This repository began as a few small tools built on that
observation, and has grown into a set of geometry instruments for the
same mission: none of them reads text, and there is no ML anywhere in
the chain.

**What is input and what is produced here.** The PHerc1218 per-ray
crossing table and per-slice origins are an **external input**
(iyando's convention and script, Jinhojeong's run — credit and
provenance in mode 16). This repository does **not** detect windings
from raw CT; it reconstructs and analyses geometry from those published
crossings, and validates the results against the raw CT volume where
that is possible.

**Evidence levels used throughout:**
`SYNTHETIC` (twin/bench with planted truth) · `REAL-DERIVED` (built
from published real-scroll data) · `RAW CT` (checked directly against
the CT volume) · `THIRD-PARTY` (validated against another
contributor's ground truth).

## What this repository is, in four lines

- It **measures** the geometry of a crushed scroll and of the segmentation that traced it. It reads no text and uses no machine learning.
- Its inputs are other people's data: rendered Paris 4 surfaces, and Jinhojeong's per-ray crossing table of PHerc. 1218 (iyando's convention).
- Every instrument is examined on a synthetic twin with planted truth before it touches real data, and every claim below says who checked it.
- The long write-up of each mode lives in [`docs/modes/`](docs/modes/). This page is the summary.

## Results that other people have checked

| What | How it was checked | Where |
|---|---|---|
| **Void-aware winding count** ("don't count the air") | Adopted unchanged by iyando and run on the full PHerc. 1218 (1.46M crossings); acceptance test passed on his machine | [mode 6](docs/modes/06-reconcile.md) |
| **Reconstructed cross-section matches the raw scan** | Overlaid on the CT at four heights: 0.66–0.83 mm error, correlation +0.99 with per-height profiles | [mode 11B](docs/modes/11b-raw-scan-check.md) |
| **Every label sent back to its winding** | Replicated exactly by the labels' author on the full 5.2 GB tree (85.8 %, median 2.6 voxels); the same pass corrected his published seam figure (82.9 → 88.8 %) | [mode 18](docs/modes/18-unwrap-per-point.md) |
| **Unlabelled papyrus is there** | 9,034 predicted positions with raw-CT evidence of material; cross-checked by the labels' author: 6,616 survive at exact voxel, most of the rest are edge grazes within the declared tolerance | [mode 19](docs/modes/19-recovery-map.md) |
| **Local sheet coherence in microns** | A hidden winding is recovered to 32 µm from its neighbours (60 µm with three hidden), held-out exam; our own global field does worse (370 µm) and the comparison was published against us | [mode 17](docs/modes/17-ironing-field.md) |
| **Winding count and roll length agree with the per-voxel map** | 109–110 winding lanes (ours from the table, his from the voxel tree); loom length 8.4–9.4 m; labelled material ~3.2 m per plane by both routes | [metrology note](docs/modes/16-unrolled-ribbon-census.md) |

## PHerc. 1218 in numbers

What the crossing table says about the scroll. **Measured** means an exam or a third party stands behind it; **expected** means a forecast with no judge yet.

- **Winding lanes: 109–110** (measured, two routes). The table reaches ordinal k = 108.
- **Loom length: 8.4–9.4 m** (measured) — the length of the full spiral at the measured pitch (~0.2 mm/turn). This is the *loom*, not the papyrus.
- **Labelled papyrus: ~3.2–3.3 m per plane** (measured, both routes); **~2.5 m** once split labels are merged. About 30 % of consecutive crossings are one label cut in two — measured at the table and at the voxel independently.
- **The 5.13 m "ribbon" of mode 16 is a path length** over 78 well-traced windings on the median geometry, not labelled papyrus. It stays in the mode-16 page with that reading.
- **Unnamed material: roughly 60 % of the loom** (measured by subtraction); the wedge audit says most of it is physically present (mass 0.85) but no longer resolvable as separate laminae at 17 µm.
- **Crush ratio: median ~2:1**, varying 1.35–3.16 between heights; the ellipse is an average, not a section (measured).
- **Where the scroll fails**: hinge axes lose material to voids, flattened faces to fusion; the core buckled as a column (S-shaped axis ~15–20 mm) with the crush on top (measured on the table and the CT).
- **Expected, not yet measured**: the column count of the hidden work (Greek-prose band 47–98 columns), and the kollesis positions (three searches null).

## Status of every mode

`measured` = passed its pre-registered exam on real or synthetic data · `null` = looked for, not found, sensitivity floor stated · `withdrawn` = claimed, then failed its own audit, kept on record · `instrument` = tool with tests, no real-data claim.

| Mode | Question | Status | Page |
|---|---|---|---|
| 1 | Does the scribe's grid survive on a rendered surface? | measured; original letter pitch 4.16 mm **superseded by 1.83 mm** (the search band excluded the answer) | [01](docs/modes/01-measure.md) |
| 2 | Where do two ink models disagree? | instrument | [02](docs/modes/02-arbitrate.md) |
| 3 | Can buried lines emerge by stacking at the period? | instrument (synthetic gain only) | [03](docs/modes/03-detect.md) |
| 3B | Can period and phase be tracked on raw intensity? | measured (4 exams) | [03b](docs/modes/03b-search-track.md) |
| 4 | Which segmentation candidate keeps the grid best? | measured, margins declared thin | [04](docs/modes/04-screen.md) |
| 5 | Local baseline tilt | measured | [05](docs/modes/05-orient.md) |
| 6 | Windings a ray should cross, voids included | measured, **adopted by a third party** | [06](docs/modes/06-reconcile.md) |
| 7 | Work size and text placement from geometry | measured on the twin; real-scroll column count is *expected* (factor-2 revision on record) | [07](docs/modes/07-twin-predict.md) |
| 8 | Where does papyrus crack under the crush? | **withdrawn** — neutral angle not found on real labels; the two damage mechanisms were confirmed | [08](docs/modes/08-fibre-strain.md) |
| 9 | Work size from a measured section + catalogue | measured (round trip); population claim is *expected* | [09](docs/modes/09-work-size.md) |
| 10 / 11 | Can the in-plane flattening be undone? One law for all windings? | measured (residual 0.2–0.33 mm; collapse 1.000→0.952) | [10-11](docs/modes/10-11-unroll-and-diagnose.md) |
| 11B | Does the reconstruction match the raw CT? | measured, **RAW CT** | [11b](docs/modes/11b-raw-scan-check.md) |
| 12 | Digital twin with planted truth | instrument (suite A–G; wire-phantom bug found by a third party and fixed) | [12](docs/modes/12-contrast-phantom.md) |
| 13 | Can sheet joins (kollesis) be detected? | **null**, calibrated against 63 third-party fusion loci; two θ≈0° suspects closed as instrumental by raw CT | [13](docs/modes/13-kollesis-detector.md) |
| 14 | Mirrored ink transfer? | **null**, placebo-controlled, ~19 µm/px | [14](docs/modes/14-the-mirrored-echo.md) |
| 15 | Fiber striations in CT? | Paris 4 **yes** (control chain); PHerc. 1218 **null** — *see the origin caveat on the page before quoting the 1218 result* | [15](docs/modes/15-fiber-striations.md) |
| 16 | Unroll the scroll from the crossings | measured; 5.13 m re-read as loom path length (see above) | [16](docs/modes/16-unrolled-ribbon-census.md) |
| 17 | One folding law for the whole scroll? | measured (held-out 0.58; neighbours beat the field, 32 vs 370 µm) | [17](docs/modes/17-ironing-field.md) |
| 18 | Every label back to its origin | measured, **replicated by the labels' author** | [18](docs/modes/18-unwrap-per-point.md) |
| 19 | Is the missing 40 % lost or unlabelled? | measured (9,034 positions, cross-checked); **281 "certified" crossings withdrawn** after a half-pitch audit, kept as candidates | [19](docs/modes/19-recovery-map.md) |

## Limits found on the way (they are results too)

- **Rays 6° apart cannot certify a sheet.** Between adjacent rays the sheet radius drifts by up to half a winding pitch (p95 ≈ 4.5 voxels against a half-pitch of 5), so no neighbour-continuity rule tells a real sheet from a ghost shifted half a pitch. Measured three independent ways; it is why the 281 were withdrawn and why any per-sheet atlas has to be built on the per-voxel labels, not on a 60-ray table.
- **k is an ordinal, not an identity.** The crossing index counts crossings along a ray; a fused pair of sheets is one crossing. Anything that treats fixed k as one sheet is wrong by construction.
- **Sheets cannot be traced on raw CT by simple detectors** at 17 µm (best of three finds 13 %); that is what the trained segmentation pipeline is for.
- **Averaging sections fabricates an ellipse** that exists at no height (R² 0.95 averaged, 0.85 per section).

## Scope and method

This repository does not trace surfaces, does not flatten better than
[flatboi](https://github.com/ScrollPrize/villa/blob/main/volume-cartographer/libs/flatboi/flatboi.cpp),
does not fit spirals better than
[fit_spiral](https://github.com/ScrollPrize/villa/blob/main/volume-cartographer/scripts/spiral/fit_spiral.py),
and does not detect ink at all. Those problems have teams and tooling.
What it does is **measure** — properties of the roll itself and of the
segmentation that produced its geometry: winding pitch, fusion rate,
crush ratio, unrolled length, per-point collapse displacement, where
the segmentation stops being trustworthy, whether a period is real or
an artefact of the band it was searched in. Its inputs are declared
above; its instruments are built and examined on a synthetic twin with
planted ground truth before touching real data, and validated against
raw CT and third-party ground truth where possible — with no ML
anywhere in the chain.

That is a narrow niche, and it is a stated one: the project's own
[open-problems page](https://scrollprize.org/2026_open_problems) says
twice that "we do not always know which part of the pipeline is
limiting us" and that "better diagnostics matter just as much as better
models". Everything here is aimed at that sentence. Every mode ships an
acceptance test written before the answer was known, and several of
those tests have failed and are documented where they failed (see
`LOGBOOK.md`).

---

## What is in this repo

```
vesuvius-topological-grid/
├── README.md                          ← this summary
├── LOGBOOK.md                         ← one line per action, failures included
├── CITATION.cff · LICENSE.md · requirements.txt
├── docs/
│   ├── modes/                         ← the full write-up of every mode (01 … 19)
│   ├── data_sources.md                ← where every number and image comes from
│   └── technical_note_revised.pdf     ← the original technical note (July)
├── scripts/
│   ├── pherc1218_io.py                ← loader for the PHerc. 1218 table, origins, CT
│   ├── *_1218.py                      ← modes 15–19 (run standalone or as Colab cells)
│   ├── synthetic_scroll_twin.py, contrast_phantom.py, kollesis_detector.py …
│   │                                  ← synthetic instruments with their `test` targets
│   ├── grid_metric.py, phase_tracking.py, displacement_field.py …
│   │                                  ← measurement tools (modes 1–11)
│   └── …
├── figures/                           ← every figure referenced in docs/modes
└── archives/
    ├── results/                       ← CSV / NPZ / JSON outputs, incl. `for J/` (benches shared with the labels' author)
    └── earlier script versions and the July proposal
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
    --width-mm 129 --letters-mm 1.83 --lines-mm 2.79

# 7. Detect buried line structure by epoch folding
python scripts/epoch_folding_prototype.py --input surface.png --width-mm 129 --noise-test

# 8. Search the period and phase, and track the phase for glitches
python scripts/phase_tracking.py search IMAGE.png --width-mm 129 --axis lines

# 9. Map the local tilt of the writing baseline
python scripts/grid_metric.py orient IMAGE.png --width-mm 129 \
    --letters-mm 1.83 --lines-mm 2.79

# 10. Void-aware layer-count reconciliation (runs its acceptance test with no args)
python scripts/void_aware_expected_n.py

# 11. Build the synthetic twin for a work of N columns (no input images needed)
python scripts/synthetic_scroll_twin.py build --columns 95 --script greek \
    --csv twin_truth.csv --plot twin.png

# 12. What the crushed section implies about the length of the work
python scripts/synthetic_scroll_twin.py sweep --script greek --plot sweep.png

# 13. Sheet joins: the kollesis landmarks and their angular chirp
python scripts/synthetic_scroll_twin.py kollesis --columns 95 --plot koll.png

# 14. Export a voxel volume as a test bench (fused turns, crossed fibers)
python scripts/synthetic_scroll_twin.py volume --columns 95 --z-window 8 \
    --voxel-um 60 --fuse 20,24,60,150 --fibers --out twin_vol.npy

# 15. The falsifiable column map for the real scroll; anchors tighten it
python scripts/text_layout_predictor.py predict --columns 95 --csv map.csv
python scripts/text_layout_predictor.py calibrate --anchors anchors.csv

# 16. What the implied work depends on (never quote a figure without this)
python scripts/synthetic_scroll_twin.py sensitivity

# 17. Where the crush cracks the sheet, and where it leaves it intact
python scripts/fibre_strain.py map --plot fibre.png

# 18. Which work fits a measured section, and which rolls match nothing
python scripts/work_size.py identify --section 42 21
python scripts/work_size.py population --section 42 21

# 19. Acceptance tests (no arguments, no data required)
python scripts/synthetic_scroll_twin.py test
python scripts/text_layout_predictor.py test
python scripts/fibre_strain.py test
python scripts/work_size.py test
python scripts/phase_tracking.py test
python scripts/displacement_field.py test
python scripts/contrast_phantom.py test
python scripts/kollesis_detector.py test
```

```bash
# 20. PHerc. 1218 modes (15–19): the loader fetches the crossing table and
#     origins once (cached), checks them against the README census, and every
#     1218 script then runs from a terminal exactly as it ran as a Colab cell
python scripts/pherc1218_io.py                       # self-check: 1,404,796 crossings, 323 planes, 60 rays
python scripts/unroll_1218.py                        # mode 16 (needs nothing else)
python scripts/planchado_heldout_um_1218.py          # mode 17 addendum
# modes needing the raw CT (wedge_audit, unwrap_texture, kollesis_search): pip install zarr s3fs
# modes needing J's label points (vote_instance, winding_per_point):     pip install kagglehub
```

Inside a Colab notebook the same scripts are still cells: they only load the
table themselves when `rows` is not already defined, so nothing changes there.
One line gives a cell everything the old loading step gave it:
`from pherc1218_io import load_all; globals().update(load_all())`.

The scripts listed above run on geometry alone — no input images. That is
no longer true of the repository as a whole, so the modes split three ways:

- **Core tools, standalone** — modes 1–13 and their `test` targets above:
  synthetic twin, predictor, folding, displacement, detectors.
- **PHerc. 1218 experiments** — modes 15, 16, 17, 18: require the crossing
  table and the label tree from the labels' author's repository
  (`scripts/pherc1218_io.py` fetches and checks the table and origins).
- **Raw-CT experiments** — modes 11B, 14, 19: require access to the scan
  volume (and, for mode 14, the Paris 4 fragment).

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
