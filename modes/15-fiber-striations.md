# 15 — Fiber striations inside the closed scroll

*Moved unchanged from the README on 2026-09-06; the README now holds only the summary. Figures and scripts are referenced relative to the repository root.*


**Context.** Papyrus sheets are made of plant strips whose individual
fibers leave a fine parallel striation — a few millimeters in pitch,
unique to each sheet, like a fingerprint. Papyrologists have used this
striation for over a century to match fragments ("fiber matching"): if
the pattern continues, two pieces belong to the same sheet. Until now
this required holding the fragment under raking light. The question
here: is that fingerprint measurable in the CT of a scroll that has
never been opened?

**Result.** Yes. On the Scroll 1 GP segment (2.4 um surface volume),
aggregate spectra show a periodic intensity pattern with fundamental
period ~4.2–4.7 mm (first harmonic 8.3–9.3 mm), on both faces and in
crossed orientations — height-wise on the recto, arc-wise on the verso,
matching the two crossed strip layers of papyrus manufacture.

**Controls.** Three alternative explanations were tested and excluded:
- *Ink/text*: the pattern strengthens away from the inked surface
  (core ~155x background), and is stronger between text columns
  (~1162x) than under text (~731x).
- *Render tiling*: the dominant peak sits at ~65 px, not at the 128 px
  tile stride.
- *Crumpling*: the surface geometry undulates at other periods
  (~20 mm along arc, ~10 mm in height — itself a first measurement of
  the crush corrugation of the near-core windings); at 2–5 mm the
  geometry is smooth while the intensity is not.

**Stated limit.** At the 67 um/px render the striation is visible in
aggregate but not traceable block-to-block (baseline continuity
0.27–0.33 across four estimators (including phase tracking of the fundamental); synthetic benches with noise, drift
and shear keep >=0.85, so the limit is sampling, not method). Tracing
fibers individually — and detecting sheet joins (kolleseis) as breaks
in the striation, including joins crushed below any thickness ratio —
needs the 1.129 um data. That run is next.

**Reproduce.** `scripts/fiber_striations.py` (Colab-ready, anonymous
S3); outputs `archives/results/fiber/fiber_striations_results.json` and the
figure below.

![Fiber striations and controls](../../archives/results/fiber/fiber_striations.png)

**Cross-scroll check (PHerc. 1218).** The same instruments ran on the
1218 raw volume (17 µm voxels, ray/ring geometry from the census
inputs). The crush corrugation is measured there too: 19.8 mm vertical
period, 10.2× background, over 3,363 sheet columns — against ~10 mm on
the Paris 4 near-core segment. Two scrolls, one instrument; the more
brutally crushed roll corrugates at twice the wavelength. The fiber
striation is *not* detectable in 1218, and the check was run both ways:
straight dense columns (4,025 at 17 µm steps — nothing over background)
and crest-following tracking that rides the sheet's local maximum
through its undulation (1,389 columns, matched shuffled null — still
nothing). So the absence is a property of the material, not of
sectioning a corrugated sheet. Read against Paris 4 — better preserved,
striation strong — the natural reading is that 1218's fine texture did
not survive its collapse, though one window is not the whole scroll.

The crush geometry of PHerc. 1218 (corrugation, unrolled ribbon, and where
segmentation survives) is mapped in mode 16.

---



---

## Caveat found 2026-09-06 (not yet re-run)

`scripts/cross_scroll_1218.py` reads the per-slice origins by column
*position*; the origins file lists its columns as `z, cy, cx`, so the script
used the centre with x and y swapped (~120 voxels, ~2 mm) and without the
(−3, −1) offset that every other raw-CT script applies. The 88 % material
sanity check does not catch this (papyrus is nearly everywhere). The 1218
results on this page — the striation null and the 19.8 mm corrugation — were
obtained with that centre and should be re-run with the origins from
`scripts/pherc1218_io.py` before they are quoted. The Paris 4 results are
unaffected.
