# 14 — The mirrored echo (`scripts/sovrapposto_echo.py`)

*Moved unchanged from the README on 2026-09-06; the README now holds only the summary. Figures and scripts are referenced relative to the repository root.*


When the crush pressed the inked face of each winding against its
neighbour's back, physical ink transfer would leave a faint MIRRORED copy
there — the *sovrapposti* documented since the 18th-century physical
unrollings. Two consequences worth testing: a real letter should carry a
mirrored echo on the neighbouring back in contact zones (a validator for
ink readings), and a model artifact copies text UN-mirrored, so the mirror
separates physics from artifact.

    python scripts/sovrapposto_echo.py test

**Phase 1 — manufactured in the twin, all four exams pass.** The echo is
painted with exact ground truth at the real 1218 pitch (at 173 µm the
flattened axis is in genuine contact; at coarser pitches nothing touches),
conservation built in. The mirrored estimator detects a 5 % transfer
(margin over the direct estimator 0.50), stays silent on open gaps (0.07),
and scores un-mirrored bleed the opposite way (0.48) — the discriminator
works. One exam was re-registered with the original kept: the absolute
correlation gate presumed uniform SNR across stretches; the detector's
statistic is the mirror-minus-direct margin.

**Phase 2 — asked of the real scroll, answered with a bounded null.** On
the GP segment over the 2.4 µm scan (390k winding-to-winding pairs matched
by angle, height and radius; separations 150–780 µm, so both genuine
contact and open gap are sampled; 37k windows), the contact and gap strata
give identical margins (−0.012 each, CI ±0.006): **no mirrored echo at
this resolution**, and no contact-concentrated negative either — which
doubles as measured evidence that the ink map carries no detectable
surface-bleed. The small uniform negative matches radially organised
damage (cracks crossing windings at fixed angle) rather than either
hypothesis. A finer imprint stays open; the 1.129 µm mesh of the same
segment is the next rung.

    
![sovrapposto_test](../../figures/sovrapposto_test.png)

Two artifacts were caught by the in-cell sanity checks before any margin
was read: the GP mesh self-overlaps with a ~86 µm offset (the same papyrus
appears twice), and its tail survived a naive distance filter — the
final pairing defines the neighbour physically (same angle, same height,
different radius) so mis-identification is excluded by construction.

A fifth exam was added after the real-scroll campaign: the shuffled-pairing placebo, 
which the field run proved decisive — and which, run on the twin, reproduces the 
real scroll's shuffled offset (+0.10 clean vs +0.008 noisy, same sign): the estimator's 
intrinsic mirrored bias with lettered profiles, now characterized.

---

