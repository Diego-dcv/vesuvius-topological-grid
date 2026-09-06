# 11B — Checked against the raw scan, and what did not survive

*Moved unchanged from the README on 2026-09-06; the README now holds only the summary. Figures and scripts are referenced relative to the repository root.*


Everything above is built on published per-ray crossing positions, which are
themselves derived from surface predictions. This section goes to the **raw CT
volume** — the masked scan (8.64 µm native, read at pyramid level 1 =
17.28 µm) directly from the open bucket — and asks
whether the reconstruction lands on papyrus. Some of it does. Some of what was
claimed earlier does not, and that is recorded here rather than quietly fixed.

### What holds

**The reconstructed section matches the scan, per height.**

![Reconstructed section overlaid on raw CT slices](../../figures/seccion_sobre_ct.png)

*Figure 11B-1 — The reconstructed cross-section (cyan) drawn on four raw CT
slices of PHerc1218, one per height, with each slice carrying its own measured
profile. The orange curve on the same axes is the single median profile the
earlier version used, shown for contrast. Nothing here is fitted to the CT: the
profiles come from published crossing positions and the scan is read
independently.*

Overlaying the measured profile of a given height on the CT slice at that
height:

| height (L1) | error against CT | correlation |
|---|---|---|
| 2000 | 0.76 mm | **+0.993** |
| 4500 | 0.66 mm | **+0.990** |
| 7000 | 0.71 mm | **+0.993** |
| 9500 | 0.83 mm | **+0.992** |

Under 0.85 mm on a roll of 10–24 mm radius, and the reference angle agrees
without being fitted — the crossing data and a centre-of-mass on raw CT arrive
at the same orientation independently.

**The inter-layer spacing is anisotropic in the raw scan too.** Spectrally, the
period between laminae reads 235 µm on the crease axis against 203 µm on the
flattened axis, with the signal ~2.8× above the local noise floor. Mode 8's
angular prediction survives contact with the scanner, not just with derived
products.

### Three corrections

**The shape correlation quoted earlier was the best of four.** The post that
introduced this work cited 0.98; the other three heights were 0.97, 0.93 and
**0.81**. All four were penalised by comparing each slice against a *median*
profile. Per height they are 0.99 across the board — a better number reached by
a more honest method, and the earlier figure should not have been quoted
singly.

**The flat sheet of 11.2 is sheared, and the shear is mine.** The displacement
within each winding was computed per height, but the **cuts between windings**
used a median perimeter applied to every height. Measured properly, the
cumulative arc position after 46 windings varies by **1779 mm between heights —
44 % of the sheet length**, growing from 5.5 mm of spread after one winding to
412 mm after forty-five. A 150 mm column would drift ~180 mm horizontally top
to bottom, four column widths. The code now accumulates per height; the figure
is a map of deformation and coverage, **not of metric position**.

**Averaging manufactured an ellipse.** The R² = 0.948 elliptical fit cited
throughout is to the median of 313 sections. Fitted individually those sections
give 0.848 (down to 0.592), with the aspect ratio spanning 1.35–3.16 and the
major axis rotating through the roll. The twin's single symmetric section is
more regular than any real slice.

### What could not be fixed, and why

**The residual accumulation is not ours to remove.** Even accumulating per
height, each winding's perimeter varies ~9.8 % between heights — and a winding
of papyrus cannot change length by 9 % over a few millimetres of height. Most
of that is the segmentation losing or merging windings differently at different
heights, and summing over 46 windings amplifies it. Removing it means following
each winding as a continuous object through z rather than slice by slice, which
is surface tracking and belongs to the project's own pipeline.

**Layer-by-layer overlay on raw CT does not work here.** Three detectors were
tried against the raw scan — peak counting, spectral-strength gating, spacing
gating — and the best found **13 %** of the laminae present, with a median
spacing of 430 µm against the 173 µm pitch: two out of three windings skipped.
For comparison, the crossing data underlying everything above carries ~70 per
ray. Tracing laminae on raw CT is what the segmentation pipeline does with
trained models; it is not a scripting exercise and this repository does not
attempt it.

**And there is no simple ink statistic.** On Paris 4's published surface volume,
paired within the same windows, seven per-column statistics were tested against
the published ink labels — mean, spread, max, min, range, through-thickness
gradient, recto/verso asymmetry — resolved both pooled and plane by plane
across the 109 depth planes. **All below d = 0.2**, the best being −0.127 at the
mid-plane with a between-window sign coherence of only −0.33. Density separates
worst of all, at −0.049, which is the expected result and confirms the test was
sound. This is a null with a boundary: it rules out **per-column** statistics,
not the spatial texture between neighbouring columns, which is what a trained
model reads and which no single-point summary can express.

---

