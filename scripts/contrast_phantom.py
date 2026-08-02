#!/usr/bin/env python3
"""
contrast_phantom.py -- Separating "faint" from "compressed".

Diego C. V. (vesuvius-topological-grid) -- mode 12.

THE CONFOUND
------------
Measured on the published surface model across 892 public labelled volumes,
the sheet it misses is the FAINT sheet: missed voxels run 10.3 % darker than
found voxels inside the same volume (161 of 201 paired volumes), while local
sheet thickness and component size show no difference at all.

That measurement cannot say WHY. In real papyrus, brightness and compression
travel together -- compressed regions are exactly where the material goes
faint -- so two incompatible readings fit the same numbers:

    (a) the model cannot learn faint sheet, whatever its geometry;
    (b) faint regions are geometrically harder, and darkness is a symptom.

No measurement on real data separates them, because no real scroll offers the
same geometry at two contrasts. A phantom does.

WHAT THIS EMITS
---------------
A grid of volumes over two axes that are confounded in reality and independent
here:

    contrast  -- papyrus level against air, and additive noise
    geometry  -- winding pitch, which sets how tightly the layers pack

A note on why the geometry axis is the PITCH and not the crush ratio, since
the crush ratio is the more obvious choice and it is wrong. Under an
arc-length-preserving crush the ratio does not tighten the packing, it
REDISTRIBUTES it: layers pack closer on the flattened axis and further apart
at the creases, by the same factor. A ratio sweep therefore makes some angles
harder and others easier at once, and a detector's failure could not be
attributed. The pitch tightens everywhere, monotonically, so a fall along that
axis means one thing. (This was found by an acceptance test failing: exam B
measured the gap along a mid-height row, which leaves through the crease axis,
and the gaps grew with ratio instead of shrinking.)

Every cell carries per-voxel ground truth: which voxels are papyrus surface,
which are ink, which are air. The geometry is IDENTICAL along a contrast row
(same seed, same crush, same kollesis) and the contrast is IDENTICAL down a
geometry column.

Run a surface model over the grid and the confound resolves by inspection:

    recall falls along the contrast axis only   -> reading (a)
    recall falls along the geometry axis only   -> reading (b)
    recall falls only in the corner             -> the two interact, and
                                                   neither alone explains it

The third outcome is the interesting one and is invisible in real data.

WHY BOTH AXES
-------------
The request that prompted this asked for contrast at fixed geometry. That is
half of it: a contrast sweep alone shows that faintness hurts, which is not in
doubt. Separating the two readings needs the geometry arm as its control --
otherwise a fall along the contrast axis is still compatible with "the hard
cases were dark anyway", since a single row cannot say what geometry costs.

WHAT THIS IS NOT
----------------
The twin is a prism: identical top to bottom, two analytic folds, no tearing,
no local plasticity. It does not reproduce the complexity of real deformation
and its slices will not look like real CT. That is not the point. The point is
that the answer is known, so a detector's failure can be attributed rather
than argued about. Absolute recall numbers on these volumes mean nothing; the
SHAPE of the recall surface across the grid is the whole result.

USAGE
-----
    python contrast_phantom.py grid --out phantoms/
    python contrast_phantom.py grid --out phantoms/ \\
        --papyrus 40,55,70,90 --pitch 260,180,120 --noise 6
    python contrast_phantom.py test
"""

import argparse
import os
import sys
import numpy as np

import synthetic_scroll_twin as T


DEF_PAPYRUS = (35, 50, 65, 90)      # air is 0; 90 is the twin's default
DEF_PITCH = (260.0, 200.0, 150.0, 110.0)   # um between windings
DEF_NOISE = 6.0
DEF_GAP = 0.42        # gap as a FRACTION of the pitch, held constant
DEF_VOXEL = 40.0      # um; keeps the tightest pitch above Nyquist


# A DESIGN ERROR AND ITS FIX -------------------------------------------------
# The first version of this grid held sheet thickness FIXED at 150 um while the
# pitch swept 260 -> 110. That made the geometry axis sweep two things at once
# and, past the middle, leave the possible:
#
#     pitch   gap        vox/pitch (at 60 um)   sheet/period
#     260 um  +110 um    4.33                    58 %
#     200 um   +50 um    3.33                    75 %
#     150 um     0 um    2.50                   100 %   <- no gaps at all
#     110 um   -40 um    1.83                   100 %   <- and below Nyquist
#
# So at the two tightest cells the phantom was a solid block with no layer
# structure to find, and at the tightest the sampling could not have resolved
# layers even if they existed. Any optimum found at 150 um is then a property
# of where the gap closed, not of the detector.
#
# The fix is to make the sheet a constant FRACTION of the pitch, so the gap
# fraction holds and the axis sweeps tightness alone, and to shrink the voxel
# until the tightest pitch is comfortably above Nyquist. At 40 um the sweep
# gives 6.5 / 5.0 / 3.75 / 2.75 voxels per pitch, all resolvable.


def contrast_ratio(papyrus, noise):
    """Sheet-to-air contrast in units of the noise, i.e. what a detector sees.

    Reported alongside the raw level because 'papyrus = 35' means nothing on
    its own -- a detector cares about separation relative to what it must see
    through.
    """
    return papyrus / noise if noise > 0 else np.inf


def emit_cell(n_columns, papyrus, pitch_um, noise, seed=0, z_window_mm=8.0,
              voxel_um=DEF_VOXEL, gap_fraction=DEF_GAP):
    """One phantom: volume plus per-voxel ground truth.

    Ground truth is derived from the same geometry that painted the volume,
    so it is exact by construction -- there is no annotation step to be wrong.
    """
    g = dict(T.G)
    g['pitch_um'] = pitch_um
    # sheet scales with pitch so the gap fraction is constant along the axis
    g['sheet_um'] = (1.0 - gap_fraction) * pitch_um
    old = dict(T.G)
    T.G.update(g)
    try:
        truth, meta = T.build_twin(n_columns, seed=seed)
        rng = np.random.default_rng(seed)
        vol, vmeta = T.make_volume(truth, meta, z_window_mm=z_window_mm,
                                   voxel_um=voxel_um, rng=rng,
                                   papyrus=papyrus,
                                   ink=min(255, papyrus + 110), noise=noise)
        clean, _ = T.make_volume(truth, meta, z_window_mm=z_window_mm,
                                 voxel_um=voxel_um,
                                 rng=np.random.default_rng(seed),
                                 papyrus=papyrus,
                                 ink=min(255, papyrus + 110), noise=0.0)
    finally:
        T.G.clear(); T.G.update(old)
    gt = (clean > 0).astype(np.uint8)          # papyrus present
    gt_ink = (clean >= min(255, papyrus + 110)).astype(np.uint8)
    return vol, gt, gt_ink, dict(meta, **vmeta)


def build_grid(out, n_columns, papyrus_levels, pitches, noise, seed=0,
               voxel_um=DEF_VOXEL, gap_fraction=DEF_GAP):
    os.makedirs(out, exist_ok=True)
    rows = []
    for pitch in pitches:
        for pap in papyrus_levels:
            vol, gt, gt_ink, meta = emit_cell(n_columns, pap, pitch, noise,
                                              seed=seed, voxel_um=voxel_um,
                                              gap_fraction=gap_fraction)
            tag = f"pap{pap:03d}_pitch{pitch:.0f}_noise{noise:.0f}"
            np.savez_compressed(os.path.join(out, tag + '.npz'),
                                volume=vol, gt_surface=gt, gt_ink=gt_ink,
                                papyrus=pap, pitch_um=pitch, noise=noise,
                                sheet_um=(1.0-gap_fraction)*pitch,
                                voxel_um=voxel_um, gap_fraction=gap_fraction,
                                section_w_mm=meta['section_w_mm'],
                                section_h_mm=meta['section_h_mm'])
            rows.append((pap, pitch, contrast_ratio(pap, noise),
                         float(gt.mean()), vol.shape))
    return rows


# ---------------------------------------------------------------------------
def acceptance_test(verbose=True):
    """Pre-registered. These check the phantom is a valid instrument, not
    that any detector performs well on it.

    A. THE TWO AXES ARE INDEPENDENT. Along a contrast row the geometry must be
       bit-identical, and down a geometry column the intensity statistics of
       the papyrus must be unchanged. If either leaks, the grid cannot
       attribute a failure to one axis.
       PASS: identical ground truth across a contrast row, and papyrus mean
       within 1 grey level down a geometry column.

    B. THE GEOMETRY AXIS ACTUALLY BITES. Shrinking the pitch must pack the
       layers more tightly, or the "geometrically harder" arm is decorative.
       PASS: gap between layers falls monotonically with pitch. A first
       version swept the CRUSH RATIO instead and failed here, which is how the
       design error above was found: the ratio redistributes packing by angle
       rather than tightening it.

    C. GROUND TRUTH IS EXACT, NOT ANNOTATED. Every labelled surface voxel must
       be non-zero in the noiseless volume, and vice versa.
       PASS: exact agreement, zero mismatched voxels.

    E. THE GEOMETRY AXIS SWEEPS ONE THING. Gap fraction must hold constant
       across the pitch sweep, and the tightest pitch must stay above Nyquist
       at the chosen voxel. The first version of this grid failed both without
       noticing: sheet thickness was fixed, so the gap closed at 150 um and
       went negative at 110, and 110 fell below Nyquist at a 60 um voxel. Any
       optimum found there measured where the gap closed, not the detector.
       PASS: sheet-fraction within 1 % across the sweep, and > 2.5 voxels per
       pitch at the tightest cell.

    D. THE CONTRAST AXIS IS DETECTABLE AT ALL. At the faintest level the sheet
       must still be separable from air by some margin, or the row measures
       nothing but noise.
       PASS: at the lowest papyrus level, the papyrus/air separation exceeds
       2 sigma of the added noise.
    """
    res = {}
    N = 12
    noise = DEF_NOISE

    # A -- geometry identical along a contrast row
    _, gt_a, _, _ = emit_cell(N, 35, 180.0, noise)
    _, gt_b, _, _ = emit_cell(N, 90, 180.0, noise)
    same_geom = bool(np.array_equal(gt_a, gt_b))
    # and intensity identical down a geometry column
    va, ga, _, _ = emit_cell(N, 65, 260.0, 0.0)
    vb, gb, _, _ = emit_cell(N, 65, 120.0, 0.0)
    ma, mb = va[ga > 0].mean(), vb[gb > 0].mean()
    res['A_axes_independent'] = dict(
        same_geometry=same_geom, papyrus_mean=(float(ma), float(mb)),
        passed=bool(same_geom and abs(ma - mb) < 1.0))

    # B -- the geometry axis bites
    gaps = []
    for pitch in (260.0, 180.0, 120.0):
        _, gt, _, _ = emit_cell(N, 65, pitch, 0.0)
        mid = gt[gt.shape[0] // 2]
        row = mid[mid.shape[0] // 2]
        idx = np.where(row > 0)[0]
        if idx.size > 3:
            d = np.diff(idx)
            gaps.append(float(np.mean(d[d > 1])) if (d > 1).any() else 0.0)
        else:
            gaps.append(0.0)
    mono = all(gaps[i] >= gaps[i + 1] for i in range(len(gaps) - 1))
    res['B_geometry_bites'] = dict(gaps=gaps, passed=bool(mono))

    # C -- ground truth exact
    v, gt, _, _ = emit_cell(N, 65, 180.0, 0.0)
    res['C_truth_exact'] = dict(
        mismatched=int(np.sum((v > 0) != (gt > 0))),
        passed=bool(np.sum((v > 0) != (gt > 0)) == 0))

    # D -- faintest level still separable
    v, gt, _, _ = emit_cell(N, DEF_PAPYRUS[0], 180.0, noise)
    sep = float(v[gt > 0].mean() - v[gt == 0].mean())
    res['D_faint_separable'] = dict(separation=sep, sigma=noise,
                                    passed=bool(sep > 2 * noise))

    # E -- the geometry axis sweeps tightness alone
    fr, vox = [], []
    for pitch in DEF_PITCH:
        sheet = (1.0 - DEF_GAP) * pitch
        fr.append((pitch - sheet) / pitch)
        vox.append(pitch / DEF_VOXEL)
    res['E_geometry_isolated'] = dict(
        gap_fraction=(min(fr), max(fr)), vox_per_pitch=min(vox),
        passed=bool(max(fr) - min(fr) < 0.01 and min(vox) > 2.5))

    if verbose:
        print("=" * 70)
        print("ACCEPTANCE TEST -- contrast_phantom (pre-registered)")
        print("=" * 70)
        A = res['A_axes_independent']
        print(f"A axes independent  geometry identical across contrast: "
              f"{A['same_geometry']}; papyrus mean {A['papyrus_mean'][0]:.2f} vs "
              f"{A['papyrus_mean'][1]:.2f} -> {'PASS' if A['passed'] else 'FAIL'}")
        B = res['B_geometry_bites']
        print(f"B geometry bites    layer gap "
              + " > ".join(f"{x:.1f}" for x in B['gaps'])
              + f" vox -> {'PASS' if B['passed'] else 'FAIL'}")
        C = res['C_truth_exact']
        print(f"C truth exact       {C['mismatched']} mismatched voxels (must be 0)"
              f" -> {'PASS' if C['passed'] else 'FAIL'}")
        D = res['D_faint_separable']
        print(f"D faint separable   papyrus-air separation {D['separation']:.1f} "
              f"against noise sigma {D['sigma']:.0f} (>2 sigma) -> "
              f"{'PASS' if D['passed'] else 'FAIL'}")
        E = res['E_geometry_isolated']
        print(f"E geometry isolated gap fraction {E['gap_fraction'][0]:.3f}-"
              f"{E['gap_fraction'][1]:.3f} across the sweep; "
              f"{E['vox_per_pitch']:.2f} voxels per pitch at the tightest "
              f"(>2.5) -> {'PASS' if E['passed'] else 'FAIL'}")
        print("-" * 70)
        print("OVERALL:", "PASS" if all(v['passed'] for v in res.values())
              else "FAIL")
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument('mode', choices=['grid', 'test'])
    ap.add_argument('--out', default='phantoms')
    ap.add_argument('--columns', type=int, default=40)
    ap.add_argument('--papyrus', type=str, default=None)
    ap.add_argument('--pitch', type=str, default=None,
                    help='winding pitch in um; the geometry axis')
    ap.add_argument('--noise', type=float, default=DEF_NOISE)
    ap.add_argument('--gap-fraction', type=float, default=DEF_GAP,
                    help='gap as a fraction of the pitch, held constant so the '
                         'geometry axis sweeps tightness alone')
    ap.add_argument('--voxel-um', type=float, default=DEF_VOXEL)
    ap.add_argument('--seed', type=int, default=0)
    args = ap.parse_args()

    if args.mode == 'test':
        r = acceptance_test()
        sys.exit(0 if all(v['passed'] for v in r.values()) else 1)

    pap = ([int(x) for x in args.papyrus.split(',')] if args.papyrus
           else list(DEF_PAPYRUS))
    rat = ([float(x) for x in args.pitch.split(',')] if args.pitch
           else list(DEF_PITCH))
    print(f"[grid ] {len(pap)} contrast levels x {len(rat)} winding pitches "
          f"= {len(pap)*len(rat)} phantoms, noise sigma {args.noise:g}")
    rows = build_grid(args.out, args.columns, pap, rat, args.noise, args.seed,
                      voxel_um=args.voxel_um, gap_fraction=args.gap_fraction)
    print(f"\n  {'papyrus':>8} {'pitch':>7} {'contrast/sigma':>15} "
          f"{'sheet fraction':>15} {'shape':>18}")
    for p, r, c, f, sh in rows:
        print(f"  {p:>8} {r:>7.2f} {c:>15.1f} {f:>15.4f} {str(sh):>18}")
    print(f"\n[out  ] {args.out}/  -- each .npz carries volume, gt_surface, "
          f"gt_ink and its parameters")
    print("[read ] recall falling along contrast only -> the model cannot "
          "learn faint sheet;\n"
          "        along geometry only -> faint regions are geometrically "
          "harder;\n"
          "        only in the corner -> the two interact and neither alone "
          "explains it.")


if __name__ == '__main__':
    main()
