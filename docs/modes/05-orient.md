# 5 — Orient (`scripts/grid_metric.py orient`)

*Moved unchanged from the README on 2026-09-06; the README now holds only the summary. Figures and scripts are referenced relative to the repository root.*


Maps the local tilt of the writing baseline across a surface, by rotating the
analysis axis and finding the orientation of maximum grid coherence.

```bash
python scripts/grid_metric.py orient IMAGE.png --width-mm 129 \
    --letters-mm 1.83 --lines-mm 2.79
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

