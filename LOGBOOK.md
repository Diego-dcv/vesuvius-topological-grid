# Logbook

One line per action since the project started. Symbols:
**✔** held up (published or validated) · **✘** failed or retracted, kept on record · **⏳** in progress.
Failures are listed on purpose: they are part of the method.

## July 2026 — foundations (modes 1–9)

- ✔ Technical note: layer count as segmentation QA (Obs. 1) + spectral ink contrast idea (Obs. 2)
- ✔ Grid measured on Paris 4 renders: letter pitch, column period, line spacing
- ✔ Obs. 1 implemented independently by iyando on stitched PHerc1218 (plateau N≈37–46 as predicted); mutual credit
- ✔ Modes measure/arbitrate/detect/screen/orient/reconcile, each with an acceptance exam
- ✔ PHerc1218 cross-section reconstructed from public aggregates: 42×21 mm, folds at 0°/180°, confirmed by two independent magnitudes
- ✔ Mode 7 twin & predict: work size from geometry; circular claim about turn count caught and replaced by an invertible umbilicus exam
- ✘ Letter pitch 4.16 mm defended, then measured wrong: real value 1.83 mm (the search band excluded the answer); bands fixed
- ✘ Line spacing 2.79 mm wrong by ~1.3×; corrected from the render (3.69 mm)
- ✔ Column period 43 mm vindicated by the same measurement
- ✔ Mode 8 fibre strain: neutral-angle prediction formulated
- ✘ Neutral angle falsified by iyando's labels (band flat 20–70°) — claim withdrawn; the two damage mechanisms (void at hinges, fusion at flanks) confirmed
- ✔ Mode 9 work-size catalogue: Greek-prose base rate narrows PHerc1218 to 80–98 columns with no scanning at all

## August 2026, week 1 — displacement, twin v2, phantom

- ✔ Mode 10 displacement field: depth invariance confirmed (r ≥ 0.959); crush ratio settled at ~2.0
- ✘ "Missing material at the ends" — my miscount; deficit is interior (fused core layers), documented
- ✔ Mode 11B unrolled sheet: 3.99 m × 173 mm, 92% coverage; validated against raw CT at 0.66–0.83 mm (r = +0.99, per-height profiles)
- ✘ Ellipse fit R² = 0.948 was an averaging artifact — individual sections fit 0.848 and rotate; documented
- ✔ Geology bridge: crush is parallel flexural-slip folding — one law, all turns (collapse 1.000→0.952); held up under Paul's per-height objection (0.93 unaveraged)
- ✔ Phantom (mode 12) with real thickness: wire-phantom bug found by Jinhojeong, fixed with normal-direction painting; suite A–F pass; PR #2 merged
- ✔ Three-handed fusion readout (our geometry + aviad's checkpoint + J's reader): flat conditional found — bridging ~75–78% regardless of gap
- ✔ Kollesis with real overlap thickness in the twin + exam G (thickness ratio 2.43)

## August 2026, week 2 — joints, echo, lead, the fence

- ✔ Mode 13 kollesis detector: all three exams pass (precision 0.95, recall 1.00, control 17/18 — by one, and stated so)
- ✔ Fence idea (found joints calibrate the rest): blind fit recovers 165 vs 160 true (3%)
- ✘ First fence demo failed (centroid vs paint-origin centre mismatch — convention bug n.º 1 again); fixed by exporting centre_px
- ✔ Mode 14 sovrapposti echo: instrument with truth (exams A–E incl. shuffle placebo); on Paris 4 GP: placebo-controlled null at ~19 µm/px; two by-products (mesh self-overlap ~86 µm; ink map shows no bleed)
- ✘ Lead double-ratio test (54/78 keV): dies control by control — spectral route closed with these data
- ✘ Thickness detector on the 1218 crossing table: aborted before building — the ~70 crossings/ray are label boundaries, not air gaps (confirmed by J: 7 of 10 thick bands = one crossing)
- ✔ J reopens the road: 1.3–1.6 thickness stratum is real and fat (19,790 clusters, 30% of everything ≥1.3), never tested

## August 2026, week 3 — census13 fence, striations, cross-scroll

- ✔ Census13 conversion + fence on the 1.3–1.6 stratum: row-level identity on all 491,337; verdict no_lattice (+0.43 pp, p = 0.168); sensitivity: power 1.00 at 2 flags/joint, 0.00 at 1 — concentrated joint signal EXCLUDED, dispersed form stays open
- ✔ PR into Jinhojeong's repo merged (scripts + stratum + reports): "the next person can rerun it without asking either of us"
- ✔ Mode 15 fiber striations: the papyrus's own grain (~4.3 mm fundamental) measured in CT inside the closed scroll; three controls (depth, intercolumn, geometry); published with figure + JSON
- ✔ Crush corrugation of the Paris 4 near-core measured as a by-product: ~20 mm along the arc, ~10 mm in height
- ✘ Local striation tracing at 67 µm: four estimators (correlation, max-lag, shear-aligned bench, phase tracking) all lose it — sampling limit, measured and stated; finer data named as the step
- ✔ Cross-scroll check on PHerc1218 raw CT (17 µm): crush corrugation measured — 19.8 mm vertical, 10.2× background, 3,363 sheet columns (first in-house 1218 number)
- ✘ First 1218 pass at 69 µm voxels: my error (voxel larger than the sheet); redone at 17 µm with 88% material hits
- ✔ Striation not detectable in 1218, checked both ways after the "sponge objection": straight dense columns AND crest-following tracking with matched null — the absence is the material's, not the sectioning's
- ✔ 22-08 Ironing field (mode 17): one separable folding law fits all 78 windings of PHerc. 1218 — wedge exam 0.58 (outer half 0.62, criterion ≤0.70), R² 0.68, field exported. Two plumbing bugs found and fixed en route (empty wedge mask read as a verdict; edge-padded smoothing).
- ✘ 24-08 VOTE-1 (instance majority vote): prefixed purity exam returned REVIEW and blocked the result — instances legitimately span windings (the scroll is one sheet); unit of analysis wrong, not the data. Corrected to per-point assignment.
- ✔ 24-08 VOTE-2 (per-point winding by ray-profile bracketing): 85.8% assigned (exam ≥60% PASS), median |Δr| 2.61 vox = 45 µm (exam ≤3 vox PASS); first per-voxel flat sheet of PHerc. 1218 (subsample); 20,494 winding-gap instances shipped as two-way label-QA candidates.

- ⏳ Optional next steps (not debts): 1.129 µm mesh of the GP segment; more 1218 boxes; twin corrugation parameter
