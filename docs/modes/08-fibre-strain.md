# 8 — Fibre strain (`scripts/fibre_strain.py`)

*Moved unchanged from the README on 2026-09-06; the README now holds only the summary. Figures and scripts are referenced relative to the repository root.*


Where does the papyrus crack when the roll is crushed? Sections 7 and 8 stop
at geometry; this one asks what the geometry does to the material. It is the
one mode that makes a claim about the real scroll rather than about a
phantom, and it earns that by being **derived rather than calibrated**: every
result below follows from the measured 2:1 section and classical plate
bending, with nothing fitted to anything.

```bash
python scripts/fibre_strain.py map --plot fibre.png
python scripts/fibre_strain.py map --reference flat   # the naive model
python scripts/fibre_strain.py test
```

![Bending strain against angle and depth](../../figures/fibre_strain.png)

### Which fibres, and why

Papyrus is a two-ply cross laminate: recto fibres run along the roll's
length, verso fibres along its axis. Herculaneum rolls are wound with the
written recto inward, so at a fold the **verso is the convex face** and takes
the tension. That tension acts circumferentially — along the arc. The recto
fibres lie along it and resist it the way fibres are strong, along their own
axis. The verso fibres lie *across* it and carry nothing, so the only thing
that can give is the bond between them: **they separate laterally.** It is a
consequence of the laminate structure, not an assumption.

### The reference state is the wound roll, not a flat sheet

A first pass used absolute curvature and got a fold/flat strain ratio of
exactly (a/b)³ = 8 for a 2:1 crush. That is the ratio for a sheet that is
stress-free when **flat** — true of fresh papyrus being wound for the first
time, false here. These rolls stood wound for decades and then carbonized in
that shape, so the stress-free reference is the **wound** state and what
strains the material is the *change* in curvature:

    ε(θ) = (t/2) · | κ_crushed(θ) − 1/r |

That changes the picture. At the fold the sheet is sharpened (κ: 1/r →
3.084/r); along the flattened sides it is **unbent** (κ: 1/r → 0.386/r) — and
unbending strains the material too. So the flat sides are not unloaded, only
less loaded, and the contrast falls from 8.0× to **3.39×**. `--reference
flat` reproduces the old figure for comparison; `wound` is the default
because it is the defensible one.

### The neutral angle — the result worth having

Between a fold (κ sharpened above 1/r) and a flat side (κ relaxed below it),
the curvature must **pass through 1/r**. At that angle the crush leaves the
sheet exactly as it was wound: unstrained, neither cracked nor unbent.

It sits at **37.64° from the fold axis** — four pristine sectors at 38°,
142°, 218° and 322° — and it is **scale invariant**: a and b both scale with
r, so κ·r depends only on θ and the aspect ratio. The same angle at every
depth, running through the whole roll like spokes.

Which makes it **invertible**, and that is the point:

| crush ratio | neutral angle |
|---|---|
| 1.5 : 1 | 40.7° |
| **2 : 1** | **37.6°** |
| 3 : 1 | 33.5° |
| 4 : 1 | 30.8° |

It looked like it would also make a ruler — *measure where the best-preserved
sectors lie and read off the crush ratio*, with no dependence on pitch,
umbilicus, thickness or grid. **That claim has been tested and withdrawn.**
Run against per-cell labels on PHerc1218, the zones are there and the spokes
are not: the crease axis is severely damaged by void and the flattened axis by
merging — the two-mechanism split, confirmed — but the preserved fraction is a
broad flat band from ~20° to ~70°, and the neutral zone does not beat its own
flanks (z = −0.8 and +1.0). Details, and why the joins cannot account for it,
in [`docs/data_sources.md`](../data_sources.md), "The neutral angle: tested
on the labels, and not found".

### A three-zone angular signature

Put together with the layer spacing from section 7, one geometry predicts
three different states at three different angles:

| angle | prediction |
|---|---|
| 0° / 180° (folds) | **cracking** — strain 3.39× the flat sides, growing as 1/r toward the core |
| 38° / 142° / 218° / 322° | **intact** — the crush leaves the sheet unstrained |
| 90° / 270° (flattened axis) | **merging** — layers packed below the nominal winding pitch |

All three are angular, all three are measurable, and none needs a calibration
constant.

### What is derived and what is assumed

Derived, calibration-free: the curvature field, the 3.39× contrast, the 1/r
radial gradient, and the neutral angle. These follow from the measured 2:1
section alone.

Assumed, and dominating only the **absolute** percentages: the sheet
thickness (0.150 mm) and a failure strain for carbonized papyrus, which is
not established — `--failure-strain` is a knob and the tool reports the
threshold crossing for whatever you set. **The map is the result; the
percentages are provisional.**

### Validation

| exam | criterion | result |
|---|---|---|
| A — no crush, no strain | at ratio 1:1 the wound-reference strain must vanish; the flat-reference model must not | **6e-18 vs 1.8e-2, PASS** |
| B — closed form at the vertices | numeric fold and flat values match the analytic ones; ratio = 3.39 (wound) and 8.00 (flat) | **PASS** |
| C — radial gradient | inner/outer strain equals r_out/r_in exactly | **3.8513 vs 3.8513, PASS** |
| D — neutral angle | identical at turn 0 and turn 69, and inverts back to the input crush ratio | **37.64°, ratio 2.00, PASS** |

Exam A exists to catch the error that was actually made: with no crush at
all, a flat-reference model still reports strain. If anyone reinstates the
wrong reference state, it fails. Exam B was also earned — its first version
compared the maximum and minimum over θ, and failed, because the minimum is
the neutral-angle **zero**, not the flattened-axis value. Finding that is how
the neutral angle turned up at all.

---

