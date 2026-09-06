# Fair-controls package — iterative placement machinery (PHerc.1218)

For J (vesuvius-surface-geometry-diagnostic), from the topological-grid
project. Everything here was calibrated on synthetic scrolls with
planted truth BEFORE touching real data, and every criterion was
declared before looking. The intended first use is exactly the one you
proposed: reproduce our pass/fail on planted truth, then run the two
fair controls unchanged on your per-voxel tree.

## Files

- `machinery.py` — the three locks, the iteration, the two fair
  controls, the pre-declared exams. Pure functions over a documented
  column dictionary; no I/O. The docstring at the top is the spec,
  including the one hard-won constraint: the continuity window DR_VEC
  must be < pitch/2 or the lock is vacuous (our first version used
  ±7 vox at 11.6 pitch — the windows tiled the whole range and the
  biased control passed at 0.46 before the bench caught it).
- `bench_iteration.py` — synthetic scroll (60×41 columns, 30 windings,
  truncation at winding 15, 4 deep rays, 8% noisy columns), runs the
  full iteration + both fair controls + mush control.
- `bench_panorama.py` — the global exam (healing of traced verticals +
  the vein arm), with its declared blind spot: a globally COHERENT
  half-pitch shift is a valid picture and only the external CT-vein
  arm catches it.

Both benches are standalone: `python3 bench_iteration.py`,
`python3 bench_panorama.py` (numpy only).

## Expected outputs (what you should reproduce)

bench_iteration.py:
    recovery 96% (criterion ≥80%) · round 1 alone 14% (<30%) ·
    false radii 0 · E3 median pitch 11.6 · frozen dice ratio 0.03 ·
    half-pitch ratio 0.00 (both ≤0.33) · mush control 0

bench_panorama.py:
    healing gains: real +248 vs incoherent +5 (ratio 0.02, ≤0.33) ·
    vein arm: real 100% vs coherent ghost 0% (Δ≥0.25)

## Our results on the real scroll at 6° sampling (the fail you asked
## to see before running your tree)

Iteration on the 60-ray table: 3,699 accepted in 4 rounds, E3 pass
(10.0 vox), converged as designed. Fair controls: frozen dice **0.80**,
half-pitch **1.19** — both FAIL, nothing exported. Pointed backwards at
the 281 previously "certified" crossings: ghost support 71% vs real
75% (ratio 0.95) — certification withdrawn. Measured cause: sheet
radius decorrelates by more than pitch/2 (~86 µm) between rays 6°
apart. At 17 µm neighbour spacing that decorrelation argument vanishes,
which is why your tree is the right board — and why "if either control
passes there too" is, as you said, the result worth having more.

## Adapting to the per-voxel tree

The column dict is angular-sampling-agnostic: a "ray" is whatever
angular bin your tree provides, and lock 3's neighbours are the
adjacent columns in angle and z. Things to re-derive on your data, all
printed before use in our cells: the material threshold (p5 of
brightness at labelled positions), the local pitch per column (median
consecutive labelled spacing, clamped), E3's pitch range (labelled
median ±25%), and DR_VEC (< pitch/2; we used 4 vox at pitch 11.6).
Ridge extraction: find_peaks on a lightly smoothed radial brightness
profile, prominence ≥15 on 16-bit-scaled CT, height ≥ threshold.

One measured number you can hold against your own: merging table
crossings closer than 7 vox on the same ray (the split-label rate)
removes 30% of crossings — the same object as your 2.6-vs-4.6 radial
fill, seen from the table side.
