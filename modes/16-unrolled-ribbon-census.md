# 16 — PHerc. 1218 unrolled: the ribbon and the segmentation census

*Moved unchanged from the README on 2026-09-06; the README now holds only the summary. Figures and scripts are referenced relative to the repository root.*


**What it does.** Rebuilds the scroll as a single continuous ribbon from the
per-ray crossing table (60 rays × 313 slices; same source table as the
census/fence work): median radius per (winding, θ) → developed length →
radial crush relief per (length, height). A second map counts, for every
(winding, θ) cell, how much of the height column the segmentation actually
traced — the coverage census.

**Figures.**

![PHerc. 1218 unrolled ribbon](../../figures/pergamino_desplegado_1218.png)

*PHerc. 1218 unrolled: 5.13 m of continuous ribbon across 78 traced
windings (winding pitch ~0.20 mm/turn; at least ~95 windings present, the
outer ~16 only as fragments). Color: radial crush relief, ±2.6 mm typical.
Coverage is sustained ≥50% out to L = 4.10 m; beyond that, only the
high-curvature rims of the flattened section survive segmentation. Lengths
from median geometry; per-height variation of a few percent. The ribbon is
~25% longer than a circular spiral of the same median radius — a geometric
signature of the crush.*

![PHerc. 1218 segmentation census](../../figures/cobertura_1218.png)

*Segmentation census by (winding, θ). Coverage decays smoothly from winding
~45 along two growing wedges — the flattened faces, where layers are
pressed together — while two nearly opposite meridians (the rims) survive
to the outermost windings. The thin dead line at θ≈180° is the fold crease
itself, matching the vertical fold stripe seen in the relief maps.*

**Numbers.** Ribbon 5.13 m; windings 2..79 usable (table reaches k=108;
k≥96 empty, k=80..95 at 1–10% coverage); pitch 0.20 mm/turn (median radius
0.58 → 16.04 mm); typical relief ±2.6 mm; sustained ≥50% coverage to
L = 4.10 m (~winding 70); perimeter excess +25% over the circular
equivalent. Horizontal relief bands repeat at fixed heights across dozens
of windings — the folding law seen along the whole ribbon.

**Limitations.** Geometry only — this places material, it does not produce
ink. Angular resolution is the table's 6° binning: a guide, not
letter-level. Median-geometry lengths; small z-gaps (≤2 mm) are
interpolated for display only, larger gaps are left blank. Windings below
10% coverage are excluded, not extrapolated.

**Status.** Instrument verified on a synthetic bench (phantom rings cut,
no edge artifacts, flank-shaped coverage recovered). Next step: the
ironing field — combining the in-plane de-crushing (mode 10/11) with this
radial relief matrix into a single 3D correction field, using the folding
law to interpolate across the dead wedges the census maps here.

**Script.** `scripts/unroll_1218.py` (Colab cell; expects the crossing
table loaded as `rows`). Figures in `figures/`.

---



---

## Addendum (2026-09-06) — what the 5.13 m is, and the numbers agreed with the labels' author

The 5.13 m above is the **path length of the ribbon** over the 78 well-traced
windings on the median geometry (a partial loom, +25 % perimeter over the
circular equivalent). It is **not** labelled papyrus. The labels' author asked
the question that exposed the reading; the corrected picture, measured by both
of us on our own data (his issue #1, 31 Aug 2026):

| Quantity | From the crossing table (this repo) | From the per-voxel label tree (labels' author) |
|---|---|---|
| Winding lanes | ~110 (k reaches 108) | 109 (k 0–108) |
| Loom length (full spiral at measured pitch) | 9.4 m (integrated) | 8.4 m (closed circles at median radius; reads short by construction) |
| Labelled papyrus per plane | 3.33 m (p10–p90 2.43–5.44); 2.55 m after merging split labels | 3.2 m (p10–p90 2.4–4.0); 1.8 m per voxel |
| Split-label rate | 30.7 % of consecutive crossings < 7 vox apart | median radial fill 2.6 vox vs 4.6 expected |
| Angular coverage per winding | — | median 0.76, p10 = 0 (inner and outer lanes nearly empty) |

Reading: about 60 % of the loom carries no label; the wedge audit (mode 19)
says most of that material is physically present (mass 0.85) but no longer
resolvable as separate laminae at 17 µm.
