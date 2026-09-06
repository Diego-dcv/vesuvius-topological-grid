# 10 / 11 — Unroll and diagnose (`scripts/displacement_field.py`)

*Moved unchanged from the README on 2026-09-06; the README now holds only the summary. Figures and scripts are referenced relative to the repository root.*


*One script, two modes in the table above: **10** is the displacement
field and its inversion (11.1–11.2); **11** is the folding law that the
collapsed windings turn out to share, and 11B is its check against the
raw scan.*

> **The flattening is the vehicle. The map of where to trust it is the result.**

One argument in three steps, and it only stands as one. The crush displaced every
point of papyrus; that field is measurable from geometry alone. Invert it and the
sheet lies flat. Project the per-ray diagnostics onto that flat sheet and you get
the thing a reader of this repository can actually use: **a map of where the
recovered geometry is trustworthy and where it is not**, in sheet coordinates
rather than roll coordinates.

Nothing in the chain uses ink, renders, labels or a fitted model of the crush. The
only physical premise is that **papyrus bends and crushes but does not stretch** —
arc length along a winding is conserved.

```bash
python scripts/displacement_field.py field  --from-csv rays.csv.gz
python scripts/displacement_field.py rings  --from-csv rays.csv.gz --plot rings3d.png
python scripts/displacement_field.py sheet  --from-csv rays.csv.gz --plot sheet.png
python scripts/displacement_field.py test
```

### 11.1 — The displacement field: where the crush put every point

Where the crush put each point of papyrus, measured rather than modelled.
Mark points along the axial striations of the wound cylinder, crush it, and ask
where each one ended up — because the answer is what an unwrapping has to
invert.

The sheet is inextensible, so arc length along a turn is conserved and a
point's position on the **sheet** is recoverable from the crushed shape alone:
measure the boundary r(θ) of a turn, integrate arc length around it, and a
point's arc fraction is where it sat on the cylinder. The displacement is the
difference from its polar angle in the crushed frame. No model of the crush is
required — only the measured shape, which a per-ray crossing table provides.

![Material points before and after the crush](../../figures/rings3d.png)

*Four rings, nine heights, sixty material points each. Colour is the same
papyrus in both panels. The "before" is not a model — it is the cylinder
reconstructed from the measured shape by arc length.*

### Measured on PHerc1218

Over the public per-ray crossings (1.39 M, z 1000–11000 on the L1 grid):

| ring | radius | max displacement | correlation with outer ring | transfer residual |
|---|---|---|---|---|
| 0 | 13.8 mm | 16.5° | 1.000 | — |
| 16 | 10.5 mm | 18.2° | 0.991 | 0.25 mm |
| 25 | 8.9 mm | 19.0° | 0.984 | 0.28 mm |
| 45 | 5.7 mm | 19.4° | 0.959 | 0.30 mm |

**The twin's depth-invariance prediction holds.** An arc-length-preserving
crush onto sections that scale with r gives a displacement depending only on
arc fraction and shape — identical at every depth. Measured: r ≥ 0.959 across a
factor 2.4 in radius, and r = +0.956 between the lower and upper halves of the
scroll. That was a prediction before it was a measurement.

**The amplitude is 40 % higher than the ellipse allows.** The 2.08:1 ellipse
predicts 12.3° at 54° from the crease axis; the measurement gives 16.5–19.4°
with maxima at 324° and 138–144°. Fitting the **median** boundary gives a = 21.36, b = 10.27 mm, ratio 2.08,
R² = 0.948 — but see the correction below: that fit is to an average shape and
individual sections are markedly less elliptical. The excess remains
unexplained.

**That ratio was over-stated here and is now corrected.** An earlier version
read the 2.08 as a constant measured off the boundary, and used it to settle
the span-versus-pitch disagreement of Mode 8 in favour of the span. Two things
were wrong with that. The fit was to the **median** profile over 313 heights,
and averaging irregular sections manufactures an ellipse that exists at no
height: fitted individually, real sections give R² **0.848** (range
0.592–0.934) against the median's 0.948. And the ratio is not one number but a
wide distribution — **1.35 to 3.16, median 2.01**, with the major axis rotating
through the roll (standard deviation 85°) rather than holding a fixed
orientation. The span still looks closer than the pitch, but on a median of a
broad distribution, not on a constant.

### What it is for, and the claim that was withdrawn

**For:** deducing what deformation each point underwent, so it can be put back.
The field transfers inward — applying the outer ring's profile to inner rings
leaves 0.20–0.33 mm of arc against a 4.0 mm amplitude. That matters because the
outer turns are where segmentation is reliable and the inner turns are where the
unread text sits.

**Withdrawn:** an earlier version argued that unwrapping pipelines map by polar
angle and therefore misplace text by two or three letters, and offered this as
the fix. Paul (ScrollPrize) replied that their renders are flattened by
minimising symmetric Dirichlet energy and do not map by polar angle. The failure
mode the argument rested on does not exist there, and minimising distortion over
the whole surface is a better solution than an arc-length lookup anyway. **What
fell was that claim, not the use above.**

### What else the rings say

- **No longitudinal compression.** Had the roll shortened, material would bulge
  outward where compressed and the section perimeter would track height. It does
  not: median 117.0 mm, correlation with height r = +0.143.
- **But the crush is not uniform along the roll.** Isoperimetric circularity of
  the outer ring runs 0.563 at 125–150 mm of height against 0.806 at 175–200.
  Markedly flatter in the middle than at the ends. (The absolute ratio implied by
  circularity is biased high by boundary roughness — read the variation, not the
  value.)
- **Fewer resolved windings in the middle, and it is not lost material.**
  Median crossings per ray fall to 56 at 125–150 mm of height against 70 at
  both ends. An earlier version of this section read that as erosion, in the
  opposite direction and from a badly pooled count. The control settles it: if
  outer turns were gone the slice perimeter would fall with them, and it does
  not — perimeter against crossing count gives r = +0.084, and at 125–150 mm
  the perimeter is a normal 115.1 mm. The outer boundary is where it should be;
  the missing crossings are interior layers the segmentation cannot separate.
  (A raw correlation of crossing count against *outer radius* does read +0.31,
  but that is the flattened shape: a ray leaving along the short axis has both
  a small outer radius and less radial distance to cross. Perimeter is the
  angle-independent control and it is flat.)

  Note also what this indexing cannot see. Ring 0 is defined as the outermost
  surviving crossing, so if outer turns were lost the index simply shifts and
  the loss is invisible. Testing for outer erosion would need a model of the
  intact roll to compare against, which is exactly what is missing.

### Feeding it back into the twin

`synthetic_scroll_twin.py --section-profile` now takes a **measured** section in
place of the analytic ellipse, rescaled per turn so the perimeter still equals
the wound circumference. The shipped profile
(`archives/results/pherc1218_section.csv`, 60 angles, median over 313 L1 slices) moves
the twin's crushed section from 41.9 × 21.0 mm to 44.4 × 21.2 mm.

This is the order that was wrong before and is right now: **the data set the
shape, the model came after.** Keeping the ellipse once a measured profile
exists would be modelling first.

### Validation

| exam | criterion | result |
|---|---|---|
| A — arc integration | chord-based arc fraction within 0.002 of a turn of the exact elliptic value | **2.1e-4 (0.077°), PASS** |
| B — depth invariance | nested synthetic sections agree to < 0.01° | **1.6e-13°, PASS** |
| C — amplitude scales | monotone in aspect ratio, and < 0.2° on a circular section | **1.4 → 26.5°, 0.014°, PASS** |
| D — transfer | residual under a third of the target amplitude on a deliberate 2.08→2.6 mismatch | **3 %, PASS** |

Exam A was rewritten because its first version failed at 2.75° and the failure
was the exam's: it compared the displacement profile against the closed form
pointwise, but the two are inverse functions — arc fraction to polar angle
against polar angle to arc fraction — so the same numeric grid indexes different
material points. Exam C's second half exists so the method cannot pass by
measuring its own discretisation: on an uncrushed section it must report
nothing, and it reports 0.014°.

---

### 11.2 — Inverting it: the sheet laid flat

Mode 11 reconstructs the outer resolved part of PHerc1218 as a flat material sheet using only the published per-ray crossing positions. It uses no ink signal, no rendered surface, no OCR, and no fitted model of the crush.

The physical premise is deliberately small:

> **Papyrus may bend and crush, but arc length along each winding is approximately conserved.**

If the boundary of a winding can be measured in the crushed section, its material coordinate can be recovered by integrating distance along that boundary. Each transverse section can then be cut at a common radial reference, straightened into a segment, and stacked with its neighbours.

This does not yet read the scroll. It establishes a geometry on which later measurements — including ink, CT intensity, confidence, fibre direction or thickness — may be registered.

### What enters the reconstruction

The input is the per-ray crossing geometry published by [@iyando](https://github.com/iyando): ordered radial crossing positions for successive angular rays and transverse sections of PHerc1218.

For each resolved winding and section, Mode 11:

1. reconstructs the measured closed boundary \(r(\theta)\);
2. evaluates its perimeter by numerical arc-length integration;
3. assigns every sampled point a normalized material coordinate

\[
u(\theta)=
\frac{
\displaystyle\int_{\theta_0}^{\theta}
\sqrt{r(\varphi)^2+\left(\frac{dr}{d\varphi}\right)^2}\,d\varphi
}{
\displaystyle\oint
\sqrt{r(\varphi)^2+\left(\frac{dr}{d\varphi}\right)^2}\,d\varphi
};
\]

4. cuts all windings at the same radial reference \(\theta_0\);
5. maps \(u\in[0,1]\) to physical arc length along the flattened winding;
6. stacks the reconstructed transverse sections along the scroll axis.

No analytic ellipse is required. The measured PHerc1218 section profile therefore replaces the idealized crushed section used by the synthetic twin in Mode 7.

![Geometry-only reconstruction of PHerc1218](../../figures/rings3d.png)

*Figure 11-1 — The same material points before and after the crush. Left: the cylinder reconstructed from the measured shape by arc length. Right: the measured crushed section. Colour identifies corresponding material points, not ink. The flattened sheet itself is Figure 11-3 below; the trust map is Figure 11-4.*

### Which way it reads

The reconstruction has an orientation, and it is not arbitrary.

**Ring 0 — the outermost winding — is the first column.** A book roll is
stored with the start of the text on the outside: the reader holds it in the
right hand, draws the free end leftwards, and winds the read portion onto the
left. The core is therefore the *end* of the work — which is why Herculaneum
end-titles survive, protected at the centre, and why loss of outer windings
costs the **opening** of a text rather than its close.

**The ink is on the inward-facing side, and is never exposed.** Papyrus is
written on the recto, the face with horizontal fibres, and the roll is wound
recto-inward. The text faces the core; the blank verso takes the outside. This
is the same recto-inward assumption the fibre-strain argument of Mode 8 rests
on, and it answers the obvious objection — writing on an exposed surface would
have destroyed the text before it could be read.

**One caveat on the horizontal axis.** The winding *sense* is not firmly
established for PHerc1218: it was set from a single multi-turn instance, and
the spiral constraints are mirror-symmetric, so a wrong sense mirrors the arc
axis. Until that is closed, a registered text could come out reversed. The
fix is at render time and costs nothing, but it has to be checked rather than
assumed.

This is what the flattening is for. The sheet is a **coordinate system**: once
each material point has a place, any per-point quantity can be registered onto
it — ink probability above all, but equally CT intensity, confidence, fibre
direction or local thickness. Whether the result reads is then a question the
geometry has made askable.

### Reconstructed extent

The current reconstruction covers the outer resolved portion of the scroll:

| quantity | reconstructed value |
|---|---:|
| resolved radial fraction | outer \(\sim 60\%\) |
| innermost resolved radius | 9.73 mm |
| crossing indices represented | 46 |
| transverse sections | 313 |
| samples per winding and section | 120 |
| measured cells | 92% |
| summed measured perimeter | 3.99 m |
| reconstructed sheet height | 173 mm |
| outer resolved winding length | 113.8 mm |
| inner resolved winding length | 61.1 mm |

Coverage is complete over the first metre of sheet length, remains approximately 94% to 2.9 m, and is still about 80% over the final resolved stretch. The decline beyond that point is treated as a segmentation limit, not as evidence of material loss.

---

### What the geometry measures

#### 1. The reconstruction passes an internal spiral-consistency test

For each measured winding perimeter \(L_i\), define the radius of a circle with the same perimeter:

\[
r_i=\frac{L_i}{2\pi}.
\]

For an Archimedean spiral of constant pitch \(p\), successive physical windings satisfy

\[
r_i=r_0-ip,
\]

and therefore

\[
L_i=L_0-2\pi p\,i.
\]

The equivalent radius must decrease linearly with physical winding number. That relation is not imposed by the flattening procedure: it is an independent consequence of a consistently indexed, approximately inextensible wound sheet.

Over the first forty resolved windings, the measured equivalent radii follow the expected linear relation with

\[
R^2=0.9998.
\]

The fit degrades after winding 45, reaching approximately \(R^2=0.94\) by winding 55 and \(R^2=0.83\) by winding 60. Because the outer range is exceptionally linear while the deterioration coincides with poorer crossing resolution, the conservative interpretation is that the degradation belongs to the segmentation rather than to a sudden change in papyrus pitch.

This test validates one property only: the recovered sequence is geometrically consistent with successive windings of a spiral over the well-resolved range. It does **not** prove that every individual correspondence or crossing label is correct.

![Spiral consistency and coverage](../../figures/peel.png)

*Figure 11-2 — Four views of the peel. Top left: the flat sheet with the
crush displacement painted on it. Top right: winding length shrinking toward
the core. Bottom right: the reconstructed cylinder, the spiral-consistency
test.*

*Read the bottom-left panel with care.* It shows the fraction of heights at
which each crossing index is complete, and that curve **must** fall with index
whatever the papyrus did: the n-th crossing only exists on rays carrying at
least n+1 crossings. It is a property of the indexing, not a map of material
loss — see "A result that did not survive testing" below, where the
angle-independent control settles the question.

#### 2. Crossing indices are not identical to physical windings

The crossing list contains 46 resolved indices over a radial interval that corresponds, at the corroborated mean pitch of 173 µm, to approximately 48.5 physical windings.

Thus

\[
\frac{48.5}{46}=1.054,
\]

or about **1.054 physical windings per resolved crossing index**.

Equivalently, approximately

\[
1-\frac{46}{48.5}=5.2\%
\]

of the physical windings in this interval are not represented as separate crossing indices. They are most naturally interpreted as neighbouring turns merged by the segmentation.

The sheet length provides a second estimate of the same loss:

- sum of individually measured perimeters: **3.99 m**;
- spiral integral over the same radial interval: **4.24 m**;
- missing length: **0.25 m**.

The difference is 5.9% of the spiral-integrated total, or 6.3% when expressed relative to the measured 3.99 m. These percentages are not numerically identical to the 5.2% unresolved-turn fraction because perimeter changes with radius and the comparison has finite-range boundary effects. They are nevertheless of the same magnitude and point in the same direction.

The important closure is therefore not an artificial equality of rounded percentages. It is that two independent calculations — radial winding count and integrated sheet length — both require a small population of unresolved turns.

> **Geometry closes within the expected effect of merged windings.**  
> 46 crossing indices represent about 48.5 physical turns; the directly measured sheet is correspondingly shorter than the spiral integral.

#### 3. The crush displacement field is nearly depth-invariant

Once each boundary point has both an angular coordinate in the crushed section and a material arc coordinate on the reconstructed sheet, the crush can be expressed as an angular displacement field.

Across a factor of approximately 2.4 in radius, displacement profiles correlate at

\[
r\geq 0.959.
\]

The lower and upper halves of the sampled scroll height correlate at

\[
r=0.956.
\]

The remaining arc-length residual is approximately 0.20–0.33 mm against a displacement amplitude of about 4.0 mm.

The conclusion is practical: the same crush pattern appears throughout the resolved depth of the scroll. The outer windings, where segmentation is clearer, can therefore act as a calibration region for deeper windings, where individual crossings become ambiguous.

This is not a claim that every inner winding can already be recovered. It is evidence that a correction field measured outside may transfer inward without requiring an independent deformation model at every depth.

![PHerc1218 deformation field, winding by winding](../../figures/sheet_v2.png)

*Figure 11-3 — Angular displacement expressed in material coordinates across winding depth and scroll height. The persistence of the same pattern is the relevant result; the colour scale should remain fixed across all panels.*

---

### A result that did not survive testing

An earlier interpretation treated the declining completeness of high crossing indices as evidence that material loss increased towards the core.

That inference was wrong.

The \(n\)-th crossing can only exist on rays containing at least \(n+1\) crossings. A completeness curve indexed from the outside must therefore fall even for a perfectly preserved roll. The indexing also makes outer loss invisible by construction, because crossing 0 is defined as the outermost surviving crossing on each ray.

An angle-independent control resolves the ambiguity. If outer windings were systematically missing, the measured slice perimeter should decrease with crossing count. It does not:

\[
r=+0.084.
\]

A raw correlation between crossing count and outer radius gives approximately \(r=+0.31\), but that follows from the flattened shape of the section and is not evidence of erosion.

Mode 11 therefore makes **no claim of outer material loss** from crossing completeness. The missing crossing indices identified above are interior unresolved or merged turns.

Keeping this retraction in the record is part of the method: an acceptance test is useful only when it is allowed to overturn the story that motivated it.

---

### The measured section is not an ellipse

The measured PHerc1218 section is close to elliptical, but not fully described by an ellipse:

\[
R^2_{\mathrm{ellipse}}=0.948.
\]

More importantly, the measured displacement amplitude is approximately 40% greater than predicted by an equal-perimeter ellipse with the observed aspect ratio, and its maxima are shifted away from the ellipse symmetry points.

The approximately 2% difference between the two hemispheres is too small to explain that excess.

Possible causes include localized plastic deformation, inter-layer slip, adhesion, core constraints or nonuniform relaxation, but the present geometry does not distinguish among them. The excess displacement remains unresolved.

For that reason, Mode 11 uses the measured section profile directly. The ellipse remains useful as a controlled analytic reference in the synthetic twin, but it is no longer treated as a complete description of the real crush.

---

### Acceptance tests

The mode should be considered usable only while the following tests continue to pass on regenerated data.

| exam | criterion | current result |
|---|---|---:|
| A — arc-length bookkeeping | every flattened winding length equals its numerically integrated measured perimeter within numerical tolerance | **PASS** |
| B — spiral consistency | equivalent radius linearity over the first 40 resolved windings, \(R^2>0.995\) | **0.9998, PASS** |
| C — independent count closure | pitch-based physical turn count exceeds resolved crossing count by the same order required by the length deficit | **48.5 vs 46, PASS** |
| D — depth transfer | displacement-profile correlation remains \(r>0.95\) across the tested radial range | **\(\geq0.959\), PASS** |
| E — height transfer | lower-versus-upper displacement correlation remains \(r>0.95\) | **0.956, PASS** |
| F — degradation is declared | the pipeline must report the winding range after which spiral linearity deteriorates rather than silently extrapolating through it | **after \(\sim45\), PASS** |

The exact numerical tolerances should live in the script rather than only in this README section, so that future changes can fail automatically.

---

### Declared limits

1. **Only the outer resolved \(\sim60\%\) of the radius is reconstructed.** Windings inside 9.73 mm are not resolved and are not inferred here.
2. **The method assumes approximate inextensibility along each winding.** Local tearing, slip or plastic extension can violate that assumption.
3. **Crossing identity remains an input dependency.** Spiral linearity is a strong consistency test, not proof that every crossing is correctly labelled.
4. **The mean pitch is used only as a radial accounting scale.** Local wrap-to-wrap pitch measurements remain too unstable to support pointwise predictions.
5. **No ink is detected.** The output is a material-coordinate surface, not a readable text render.
6. **The inner degradation is not filled by interpolation.** Transferability of the outer displacement field is measured, but reconstruction beyond the resolved range remains future work.
7. **The real crush is not elliptical.** Analytic ellipse results are references, not substitutes for the measured section.
8. **The source measurements remain attributable to their publisher.** This reconstruction is an arc-length integration over the published per-ray crossings, not an independent re-segmentation of the CT volume.

---

### Material coordinates: the reusable output

The principal output of Mode 11 is not a PNG. It is a material coordinate system.

Each reconstructed point can be stored as, for example,

```text
(section_z, winding_id, arc_fraction, arc_length_mm, x_flat_mm, y_flat_mm)
```

with provenance and confidence fields attached to the crossing from which it was derived.

That coordinate system is independent of imaging modality. Once established, any scalar or vector quantity sampled from the original volume may be associated with the same material point:

```text
ink probability
raw CT attenuation
surface confidence
crossing confidence
fibre orientation
surface normal
local thickness
damage class
multispectral response
segmentation provenance
```

The relationship is analogous to texture coordinates on a three-dimensional mesh: geometry defines the support first; measurements are then projected onto it.

This separation matters because future ink models need not solve the geometry again. They need only estimate a quantity in the source volume and transfer it to the existing material coordinates.

---

#### The displacement law, read through the full ring stack

**The transfer law holds through the roll, not just at the surface.** Reading
all rings of the published crossing table (0–38, step 2, medians over 313
heights), every winding follows the same displacement curve: correlation with
the outer ring runs 1.000 → 0.952 with no break, and the median residual grows
smoothly from 0.5° to 3.7° — sub-millimetre of arc throughout. Together with
the analytic match of the outer ring (+0.936 against the equal-perimeter
ellipse), this makes the crush a parallel, flexural-slip fold in the
structural-geology sense: one law, every winding. Practical consequence: given
the local aspect ratio, the law predicts point positions on any winding to
~1–2°, so the unrolling gains an interpolation term where segmentation drops
windings. Medians over height smooth the per-height figure; the per-height
residual will be somewhat larger.

---

### Future extensions

The following extensions are direct consequences of the present representation rather than claims of completed work.

#### Project CT or ink probability onto the sheet

If the source scan provides an intensity or ink-probability value \(I(x,y,z)\), each reconstructed material point can sample that field before flattening:

\[
I_{\mathrm{flat}}(u,z)=I\!\left(x(u,z),y(u,z),z\right).
\]

The flattening algorithm does not change. Geometry and reading remain separate stages.

A binary ink/empty label is possible, but retaining the continuous probability or attenuation value is preferable: thresholding can then be revised without recomputing the geometry.

#### Carry uncertainty into the flattened image

Every point should retain:

- crossing-position uncertainty;
- winding-identity confidence;
- local interpolation distance;
- spiral-fit residual;
- displacement-transfer residual;
- source-voxel support.

A flattened intensity map without its confidence map would look more certain than the underlying geometry warrants.

#### Transfer the measured displacement field inward

The observed depth invariance suggests a constrained inner reconstruction in which the outer field supplies a prior, while inner crossings and CT evidence determine local corrections.

The acceptance condition must remain strict: transfer is allowed only while held-out resolved windings are predicted within the measured 0.20–0.33 mm arc residual.

#### Replace the analytic crush in the synthetic twin

Mode 7 currently uses a controlled analytic section because it provides exact ground truth. Mode 11 adds the complementary object: a measured section profile.

Both should remain:

- the analytic ellipse for closed-form tests and known truth;
- the measured PHerc1218 profile for realistic deformation and segmentation stress tests.

The twin becomes more realistic without pretending that the measured profile supplies perfect labels.

#### Multi-modal registration

Because all measurements share the same material coordinates, geometry, ink probability, fibres, thickness and damage can be compared point by point on one flattened domain.

That creates a common reference frame for methods that currently operate on different representations of the scroll.

---

### Role within the repository

Modes 1–5 ask whether the scribe's spatial grid survives on a rendered surface. Mode 6 evaluates whether the crossing count is geometrically plausible. Modes 7–9 use an idealized scroll to make predictions about winding, strain and work size.

Mode 11 links those two halves.

It reconstructs a material sheet from measured real-scroll geometry, tests whether the winding sequence behaves like a spiral, quantifies unresolved turns, measures the crush displacement, and exposes the point at which segmentation stops supporting the reconstruction.

It therefore establishes the substrate on which the earlier text-grid tools may later operate:

\[
\text{measured crossings}
\rightarrow
\text{material coordinates}
\rightarrow
\text{registered CT / ink}
\rightarrow
\text{grid-based validation}.
\]

**Measure the geometry first; read the text later.**

---

### Credit and provenance

The reconstruction depends on @iyando's publication of per-ray crossing positions rather than only per-scroll aggregates. The flattened sheet, perimeter sums, spiral test and displacement field are derived from those measurements by arc-length integration.

The raw crossing source, preprocessing steps, commit identifier and any filtered subsets used to regenerate the figures should be recorded in `docs/data_sources.md`. Quantitative claims in this section should be regenerated from the scripts and not copied manually into release notes.

---


### 11.3 — Where to trust it: diagnostics in sheet coordinates

The flat sheet is a coordinate system, so any per-point quantity registers onto it.
Ink is the one everybody wants and PHerc1218 does not have. What it does have is the
per-ray quality table, and projecting that answers a question worth asking **before**
anyone spends compute here: which parts of this sheet are worth the compute at all.

![Where the geometry is trustworthy, winding by winding](../../figures/quality_v2.png)

*Figure 11-4 — Geometric trust by winding and angle. With the windings shown
side by side rather than concatenated, the vertical banding lines up across
them: the damage is organised by the crush axes, so it recurs at the same place
in every winding.*

| | fraction of the sheet |
|---|---|
| clean geometry | **19.5 %** |
| merge excess — layers stuck together | 73.6 % |
| void excess — cracked | 25.0 % |

**One fifth of the reconstructed sheet has clean geometry.** That is the headline,
and it is not a prediction about legibility: it says that four fifths of it carries a
*known geometric problem* before an ink model is even loaded.

The angular structure of Mode 8 survives the projection. Void concentrates at
135–225° and 315–360° — the crease axis, where bending strain is 3.4× and carbonized
papyrus cracks — while the flattened axis fails by merging instead. On the rolled
scroll that is an angular pattern; on the flat sheet it becomes **periodic banding
with the period of one winding**, which is directly actionable: it says which part of
each column is compromised, not just which region of the scroll.

Two honest limits on this map. The void threshold is the **upper quartile**, a
descriptive cut rather than a physical one — it partitions 25 % by construction, so
read the three-way split and not the 25 %. And the angular resolution is the source
data's 6°, which is 1.57 mm of arc on the outer windings against a letter pitch near
1.8 mm: **under one sample per letter.** This map tells you where to look. It cannot
tell you what letter is there, and no interpolation would change that — the
information between rays is not smoothed, it is absent.

Reading a scroll from this geometry would need an extraction at reading resolution,
roughly 500 rays per slice rather than 60. That is the same tool with a different
angular step, not a new method.

---

