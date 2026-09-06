# 12 — Contrast phantom (`scripts/contrast_phantom.py`)

*Moved unchanged from the README on 2026-09-06; the README now holds only the summary. Figures and scripts are referenced relative to the repository root.*


A measurement on the published surface model says the sheet it misses is the
**faint** sheet: missed voxels run 10.3 % darker than found voxels inside the
same volume, across 161 of 201 paired volumes, while local thickness and
component size show no difference at all. That measurement cannot say why.
In real papyrus brightness and compression travel together, so two
incompatible readings fit it equally well — *the model cannot learn faint
sheet*, or *faint regions are geometrically harder and darkness is the
symptom*. No measurement on real data separates them, because no real scroll
offers the same geometry at two contrasts.

A phantom does. This mode emits a grid over two axes that are confounded in
reality and independent here:

```bash
python scripts/contrast_phantom.py grid --out phantoms/
python scripts/contrast_phantom.py grid --arm physical    --out p/
python scripts/contrast_phantom.py grid --arm attribution --out a/
python scripts/contrast_phantom.py grid --arm physical --no-kollesis --out control/
python scripts/contrast_phantom.py test
```

The grid ships in **two arms**, because staying faithful to the physics and
isolating one variable are different goals. `--arm physical` holds the sheet
at its real 150 µm, so the gap closes as the pitch drops — which is what a
crushed scroll actually does (measured pitch ~147 µm against ~150 µm sheets on
PHerc1218's flattened axis). `--arm attribution` holds the gap at a fixed 42 %
of the pitch so a failure can be attributed to tightness alone, at the
declared price of a sheet that thins with pitch, which papyrus does not do.
`--no-kollesis` omits the double-thickness joins; single-sheet **control**
cells need it, because with joins on ~9 % of sites carry own-turn material at
~150 µm — inside a 360 µm reader span.

Geometry is bit-identical along a contrast row; intensity statistics are
identical down a geometry column. Every cell carries **per-voxel ground truth**
derived from the same geometry that painted the volume, so there is no
annotation step to be wrong. Each `.npz` also carries exact instance ground truth: `turn_id` (int16, 0 = air,
turn t → t+1) and `kollesis_mask` (bool, the footprint of the double-thickness
sheet joins) — both 2-D (ny, nx) and z-invariant by construction, so broadcast
over z if a reader wants three dimensions. The first feeds fusion readouts; the
second lets a join detector be validated against known joins, which no real
scroll can provide. Run a surface model over the grid and the
confound resolves by inspection:

| recall falls… | reading |
|---|---|
| along the contrast axis only | the model cannot learn faint sheet |
| along the geometry axis only | faint regions are geometrically harder |
| **only in the corner** | the two interact, and neither alone explains it |

The third outcome is the interesting one and it is **invisible in real data**.

**Why the geometry axis is the winding pitch and not the crush ratio** — the
obvious choice, and the wrong one. Under an arc-length-preserving crush the
ratio does not tighten the packing, it *redistributes* it: layers pack closer
on the flattened axis and further apart at the creases, by the same factor. A
ratio sweep makes some angles harder and others easier at once, so a
detector's failure could not be attributed to it. Pitch tightens everywhere,
monotonically. This was found by exam B failing: it measured the layer gap
along a mid-height row, which leaves through the crease axis, and the gaps
*grew* with ratio instead of shrinking.

**Why both axes, when the request was for contrast at fixed geometry.** A
contrast sweep alone shows that faintness hurts, which was never in doubt.
Separating the two readings needs the geometry arm as its control — otherwise
a fall along the contrast axis is still compatible with "the hard cases were
dark anyway", because one row cannot say what geometry costs.

### Validation

| exam | criterion | result |
|---|---|---|
| A — axes independent | geometry bit-identical across a contrast row; papyrus mean within 1 grey level down a geometry column | **identical; 65.31 vs 65.63, PASS** |
| B — geometry bites | layer gap falls monotonically with pitch | **12.3 > 10.0 > 8.8 vox, PASS** |
| C — truth exact, not annotated | every labelled surface voxel non-zero in the noiseless volume and vice versa | **0 mismatched, PASS** |
| D — faint level still detectable | papyrus/air separation above 2σ of the added noise at the faintest level | **32.6 against σ = 6, PASS** |
| E — the geometry axis is valid | attribution: gap fraction constant across the sweep, > 2.5 vox/pitch; physical: minimum gap > 0 and > 2.5 vox/pitch | **0.420 flat, 2.75; gap 10 µm, 5.33, PASS** |
| F — sheet thickness is painted | material fraction grows with declared thickness; measured crossing width tracks the declaration within discretisation | **ratio 1.64; 90 µm at 60, 150 at 120, PASS** |
| G — kollesis painted and labelled | median join/non-join thickness ratio in [1.5, 3.2] over measurable joins; empty mask with joins off | **5 joins, 2.43, PASS** |

These check that the phantom is a valid *instrument*, not that any detector
performs well on it. **Absolute recall on these volumes means nothing** — the
twin is a prism, identical top to bottom, with two analytic folds and no
tearing. The shape of the recall surface across the grid is the whole result.

Producing the phantoms and running a surface model on them are naturally
different hands: the attribution arm stays laptop-sized; the physical arm at a
30 µm voxel runs ~380 MB per 8 cells and is meant to be generated locally
rather than downloaded. Scoring needs the model and a GPU.

**In production.** The grid has been run end-to-end by aviad12g (frozen
checkpoint, five generation seeds) and read by Jinhojeong's fusion instrument;
the fixed-geometry contrast follow-up is preregistered in villa#191.

---

