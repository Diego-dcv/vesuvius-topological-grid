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
DEF_SHEET = 150.0     # um; real papyrus, for the physical arm
PHYS_PITCH = (300.0, 250.0, 200.0, 160.0)   # gaps 150/100/50/10 um, never < 0
PHYS_VOXEL = 30.0     # um; >5 voxels per pitch even at the tightest


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
              voxel_um=DEF_VOXEL, gap_fraction=DEF_GAP, arm='attribution',
              sheet_um=DEF_SHEET, kollesis=True):
    """One phantom: volume plus per-voxel ground truth.

    Ground truth is derived from the same geometry that painted the volume,
    so it is exact by construction -- there is no annotation step to be wrong.
    """
    g = dict(T.G)
    g['pitch_um'] = pitch_um
    if arm == 'physical':
        # Real papyrus is 100-200 um and does NOT thin because a roll is wound
        # tighter. Sheet is held fixed and the gap closes as the pitch drops --
        # which is what a crushed scroll actually does: on PHerc1218's
        # flattened axis the measured pitch is 147 um against ~150 um sheets.
        g['sheet_um'] = sheet_um
    else:
        # Attribution arm. Gap fraction held constant so the axis varies
        # tightness alone and a failure can be attributed to it. The price is
        # that sheet thickness then scales with pitch, which papyrus does not
        # do -- this arm is a probe, not a model of a scroll.
        g['sheet_um'] = (1.0 - gap_fraction) * pitch_um
    old = dict(T.G)
    T.G.update(g)
    try:
        truth, meta = T.build_twin(n_columns, seed=seed)
        rng = np.random.default_rng(seed)
        vol, vmeta = T.make_volume(truth, meta, z_window_mm=z_window_mm,
                                   voxel_um=voxel_um, rng=rng,
                                   papyrus=papyrus, kollesis=kollesis,
                                   ink=min(255, papyrus + 110), noise=noise)
        clean, _ = T.make_volume(truth, meta, z_window_mm=z_window_mm,
                                 voxel_um=voxel_um,
                                 rng=np.random.default_rng(seed),
                                 papyrus=papyrus, kollesis=kollesis,
                                 ink=min(255, papyrus + 110), noise=0.0)
    finally:
        T.G.clear(); T.G.update(old)
    gt = (clean > 0).astype(np.uint8)          # papyrus present
    gt_ink = (clean >= min(255, papyrus + 110)).astype(np.uint8)
    return vol, gt, gt_ink, dict(meta, **vmeta)


def build_grid(out, n_columns, papyrus_levels, pitches, noise, seed=0,
               voxel_um=DEF_VOXEL, gap_fraction=DEF_GAP, arm='attribution',
               sheet_um=DEF_SHEET, kollesis=True):
    os.makedirs(out, exist_ok=True)
    rows = []
    for pitch in pitches:
        for pap in papyrus_levels:
            vol, gt, gt_ink, meta = emit_cell(n_columns, pap, pitch, noise,
                                              seed=seed, voxel_um=voxel_um,
                                              gap_fraction=gap_fraction,
                                              arm=arm, sheet_um=sheet_um,
                                              kollesis=kollesis)
            tag = f"{arm[:4]}_pap{pap:03d}_pitch{pitch:.0f}_noise{noise:.0f}"
            np.savez_compressed(os.path.join(out, tag + '.npz'),
                                volume=vol, gt_surface=gt, gt_ink=gt_ink,
                                # int16, 0 = air, turn t -> t+1. Two-dimensional
                                # (ny, nx): the twin is a prism, so turn
                                # identity is z-invariant by construction --
                                # broadcast over z to match `volume` if your
                                # reader wants three dimensions.
                                turn_id=meta['turn_id'],
                                # bool (ny, nx), z-invariant like turn_id:
                                # footprint of the kollesis double-thickness
                                # joins -- ground truth for join detectors.
                                kollesis_mask=meta['kollesis_mask'],
                                papyrus=pap, pitch_um=pitch, noise=noise,
                                arm=arm, kollesis=kollesis,
                                sheet_um=(sheet_um if arm == 'physical'
                                          else (1.0-gap_fraction)*pitch),
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

    G. KOLLESIS JOINS ARE PAINTED AT DOUBLE THICKNESS AND LABELLED. The
       joins had the same wireframe defect the turns had (two one-voxel
       traces); they are now finite-thickness overlap bands with an exported
       per-voxel mask. Identify each join's crossing by the mask, the same
       winding away from the band by turn_id, and compare thickness.
       PASS: median join/non-join thickness ratio in [1.5, 3.2] over the
       measurable joins, and an empty mask when kollesis is off.

    F. SHEET THICKNESS IS ACTUALLY PAINTED. The defect this guards against
       shipped: half_t was computed and never used, every turn was a one-voxel
       curve trace, and sweeping sheet_um 60 -> 400 um left the material
       fraction unchanged at 10.7 % (found by Jinhojeong, issue #1, confirmed
       by aviad12g). Guard on both symptoms: the material fraction must GROW
       with declared thickness at fixed pitch, and the measured crossing
       width on the fold axis must track the declaration to within about one
       voxel of discretisation.
       PASS: fraction(sheet=120) / fraction(sheet=60) > 1.4, and measured
       thickness within [sheet, sheet + 2 voxels] for both.

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
    N = 8                      # exam cells are small: the checks are about
    ZW = 2.0                   # geometry and painting, not statistics
    noise = DEF_NOISE

    # A -- geometry identical along a contrast row
    _, gt_a, _, _ = emit_cell(N, 35, 180.0, noise, z_window_mm=ZW)
    _, gt_b, _, _ = emit_cell(N, 90, 180.0, noise, z_window_mm=ZW)
    same_geom = bool(np.array_equal(gt_a, gt_b))
    # and intensity identical down a geometry column
    va, ga, _, _ = emit_cell(N, 65, 260.0, 0.0, z_window_mm=ZW)
    vb, gb, _, _ = emit_cell(N, 65, 120.0, 0.0, z_window_mm=ZW)
    ma, mb = va[ga > 0].mean(), vb[gb > 0].mean()
    res['A_axes_independent'] = dict(
        same_geometry=same_geom, papyrus_mean=(float(ma), float(mb)),
        passed=bool(same_geom and abs(ma - mb) < 1.0))

    # B -- the geometry axis bites
    gaps = []
    for pitch in (260.0, 180.0, 120.0):
        _, gt, _, _ = emit_cell(N, 65, pitch, 0.0, z_window_mm=ZW)
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
    v, gt, _, _ = emit_cell(N, 65, 180.0, 0.0, z_window_mm=ZW)
    res['C_truth_exact'] = dict(
        mismatched=int(np.sum((v > 0) != (gt > 0))),
        passed=bool(np.sum((v > 0) != (gt > 0)) == 0))

    # D -- faintest level still separable
    v, gt, _, _ = emit_cell(N, DEF_PAPYRUS[0], 180.0, noise, z_window_mm=ZW)
    sep = float(v[gt > 0].mean() - v[gt == 0].mean())
    res['D_faint_separable'] = dict(separation=sep, sigma=noise,
                                    passed=bool(sep > 2 * noise))

    # E -- each arm must satisfy its own condition, and BOTH must stay
    #      physically possible and above Nyquist. The published version of this
    #      grid failed on both counts at its tightest cell: gap -40 um (sheets
    #      overlapping) and 1.83 voxels per pitch.
    fr = [((1.0-DEF_GAP)*p, p) for p in DEF_PITCH]
    gapfrac = [(p-s)/p for s, p in fr]
    vox_a = min(p/DEF_VOXEL for p in DEF_PITCH)
    gap_p = [p - DEF_SHEET for p in PHYS_PITCH]
    vox_p = min(p/PHYS_VOXEL for p in PHYS_PITCH)
    res['E_geometry_isolated'] = dict(
        attribution_gap_fraction=(min(gapfrac), max(gapfrac)),
        attribution_vox=vox_a,
        physical_min_gap_um=min(gap_p), physical_vox=vox_p,
        passed=bool(max(gapfrac)-min(gapfrac) < 0.01 and vox_a > 2.5
                    and min(gap_p) > 0 and vox_p > 2.5))

    # F -- thickness is painted
    import synthetic_scroll_twin as T
    oldG = dict(T.G)
    fr2, th2 = {}, {}
    try:
        T.G['pitch_um'] = 300.0
        for sheet in (60.0, 120.0):
            T.G['sheet_um'] = sheet
            t, m = T.build_twin(8)
            v, _ = T.make_volume(t, m, z_window_mm=2.0, voxel_um=30.0,
                                 kollesis=False)
            fr2[sheet] = float((v > 0).mean())
            mid = v[v.shape[0] // 2]
            cy = int(np.array(np.nonzero(mid > 0)).mean(1)[0])
            row = (mid[cy, :] > 0).astype(np.int8)
            d2 = np.diff(row)
            st = np.nonzero(d2 == 1)[0]; en = np.nonzero(d2 == -1)[0]
            if en.size and st.size and en[0] < st[0]:
                en = en[1:]
            k = min(len(st), len(en))
            th2[sheet] = float(np.median((en[:k] - st[:k]) * 30.0))
    finally:
        T.G.clear(); T.G.update(oldG)
    okF = (fr2[120.0] / fr2[60.0] > 1.4
           and all(s0 <= th2[s0] <= s0 + 60.0 for s0 in (60.0, 120.0)))
    res['F_thickness_painted'] = dict(
        fraction_ratio=fr2[120.0] / fr2[60.0],
        measured_um={int(k): v for k, v in th2.items()}, passed=bool(okF))

    # G -- kollesis painted at double thickness, with ground-truth mask
    oldG2 = dict(T.G)
    try:
        T.G['pitch_um'] = 300.0; T.G['sheet_um'] = 150.0
        t, m = T.build_twin(20, seed=0)
        v, vmt = T.make_volume(t, m, z_window_mm=1.5, voxel_um=30.0,
                               kollesis=True)
        km, tidv = vmt['kollesis_mask'], vmt['turn_id']
        voff = T.make_volume(t, m, z_window_mm=1.5, voxel_um=30.0,
                             kollesis=False)[1]
        mid = (v[v.shape[0] // 2] > 0)
        cy, cx = np.array(np.nonzero(mid)).mean(1)
        Rm = int(min(cy, cx, mid.shape[0] - cy, mid.shape[1] - cx)) - 2
        pr = np.arange(Rm)
        ko = m['kollesis']

        def runs_at(ang):
            aa = np.radians(ang)
            yy = (cy + pr * np.sin(aa)).astype(int)
            xx = (cx + pr * np.cos(aa)).astype(int)
            col = mid[yy, xx].astype(np.int8); d2 = np.diff(col)
            st = np.nonzero(d2 == 1)[0] + 1; en = np.nonzero(d2 == -1)[0] + 1
            if en.size and st.size and en[0] < st[0]:
                en = en[1:]
            out = []
            for s0, e0 in zip(st, en):
                sl = slice(s0, e0)
                ids = tidv[yy[sl], xx[sl]]; ids = ids[ids > 0]
                out.append((int((e0 - s0) * 30),
                            bool(km[yy[sl], xx[sl]].any()),
                            int(np.bincount(ids).argmax()) if ids.size else 0))
            return out

        ratios = []
        for i in range(len(ko['r_mm'])):
            tk = float(ko['theta_deg'][i]); rk = float(ko['r_mm'][i])
            a2, b2 = T.ellipse_axes_for_perimeter(2 * np.pi * rk, T.G['ratio'])
            per2 = T.ellipse_arc_table(a2, b2)[2]
            hd = 0.5 * T.G['kollesis_ov_mm'] / per2 * 360
            rj = [r for r in runs_at(tk) if r[1]]
            if not rj:
                continue
            um_j, _, tj = min(rj, key=lambda r: r[0])
            ref = [r[0] for sgn in (+1, -1)
                   for r in runs_at((tk + sgn * (hd + 12)) % 360)
                   if r[2] == tj and not r[1]]
            if ref:
                ratios.append(um_j / np.mean(ref))
        ratio_med = float(np.median(ratios)) if ratios else 0.0
        okG = (len(ratios) >= 3 and 1.5 <= ratio_med <= 3.2
               and vmt['kollesis_mask'].sum() > 0
               and int(np.count_nonzero(voff['kollesis_mask'])) == 0)
        res['G_kollesis_painted'] = dict(
            joins_measured=len(ratios), ratio_median=ratio_med,
            passed=bool(okG))
    finally:
        T.G.clear(); T.G.update(oldG2)

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
        print(f"E geometry valid    attribution: gap fraction "
              f"{E['attribution_gap_fraction'][0]:.3f}-"
              f"{E['attribution_gap_fraction'][1]:.3f}, "
              f"{E['attribution_vox']:.2f} vox/pitch | physical: min gap "
              f"{E['physical_min_gap_um']:.0f} um (>0), {E['physical_vox']:.2f} "
              f"vox/pitch -> {'PASS' if E['passed'] else 'FAIL'}")
        Gk = res['G_kollesis_painted']
        print(f"G kollesis painted  {Gk['joins_measured']} joins measured; "
              f"median join/non-join thickness ratio "
              f"{Gk['ratio_median']:.2f} (in [1.5, 3.2]); mask empty when off "
              f"-> {'PASS' if Gk['passed'] else 'FAIL'}")
        F = res['F_thickness_painted']
        print(f"F thickness painted fraction(120)/fraction(60) = "
              f"{F['fraction_ratio']:.2f} (>1.4); measured "
              f"{F['measured_um'][60]:.0f} um at 60, {F['measured_um'][120]:.0f} "
              f"um at 120 (each within [sheet, sheet+2 vox]) -> "
              f"{'PASS' if F['passed'] else 'FAIL'}")
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
    ap.add_argument('--voxel-um', type=float, default=None)
    ap.add_argument('--arm', choices=['physical', 'attribution', 'both'],
                    default='both',
                    help="physical: sheet fixed at real thickness, gap closes "
                         "as pitch drops, as a crushed scroll does. "
                         "attribution: gap fraction held constant so the axis "
                         "varies tightness alone. They answer different "
                         "questions and neither replaces the other.")
    ap.add_argument('--sheet-um', type=float, default=DEF_SHEET)
    ap.add_argument('--no-kollesis', action='store_true',
                    help='omit the double-layer sheet joins. For single-sheet '
                         'CONTROL cells: the join is painted one sheet inward '
                         'of its turn, so with kollesis on, ~9 %% of sites '
                         'carry own-turn material at ~150 um -- inside a 360 '
                         'um reader span -- and a false-split control reads '
                         'locally thickened sheet. Measured at pitch 700: '
                         'min centre spacing 135 um with joins, 450 without.')
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
    arms = (['physical', 'attribution'] if args.arm == 'both' else [args.arm])
    rows = []
    for arm in arms:
        pitches = (list(PHYS_PITCH) if (arm == 'physical' and not args.pitch)
                   else rat)
        vox = args.voxel_um or (PHYS_VOXEL if arm == 'physical' else DEF_VOXEL)
        print(f"\n[arm   ] {arm}: {len(pap)}x{len(pitches)} cells, "
              f"voxel {vox:g} um, "
              + (f"sheet fixed at {args.sheet_um:g} um (gap closes with pitch)"
                 if arm == 'physical'
                 else f"gap fixed at {100*args.gap_fraction:.0f} % of pitch "
                      f"(sheet thins with pitch -- not papyrus-like)"))
        rows += build_grid(args.out, args.columns, pap, pitches, args.noise,
                           args.seed, voxel_um=vox,
                           gap_fraction=args.gap_fraction, arm=arm,
                           sheet_um=args.sheet_um,
                           kollesis=not args.no_kollesis)
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
