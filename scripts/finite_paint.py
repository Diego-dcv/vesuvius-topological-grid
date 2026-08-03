#!/usr/bin/env python3
"""
finite_paint.py -- Finite-thickness, instance-labelled painting of the twin.

Companion to synthetic_scroll_twin.py; it changes nothing there and imports
the geometry (build_twin, ellipse_axes_for_perimeter, G) unchanged.

WHY THIS EXISTS
---------------
Issue #1 reported two properties of make_volume that voxel tools cannot work
with: each turn is painted as a zero-thickness curve trace (half_t is
computed and never used), and --fuse maps the welded sector's coordinates
onto the target ellipse, so the source turns land coincident with the target
where CT would show a stack. Both are fine for the crossing-count use the
volume mode was written for. Tools that measure thickness, follow material
runs along rays, or need sheets in contact see a wireframe instead of a
scroll. This script paints the thickness the parameters declare and labels
every material voxel with the winding turn it belongs to, which is the
ground truth an instance-level instrument scores against.

WHAT IT EMITS
-------------
    volume      uint8 (z, y, x)  papyrus / ink / air, same intensity
                                 convention as make_volume
    turn_id     int16 (z, y, x)  1-based winding-turn instance labels; 0 = air
    gt_surface  uint8            (turn_id > 0), exact by construction
    gt_ink      uint8            ink marks, exact by construction

HOW IT PAINTS
-------------
Each turn's crushed ellipse is sampled densely, rasterized, and a 2D
Euclidean distance transform of the raster gives every voxel its distance to
the turn midline. The distance is refined to the subvoxel sample position
inside the nearest raster cell, so the painted run is not quantized to the
raster. Material is the ring within half the sheet thickness of the midline.
Two design choices:

1. NEAREST MIDLINE where rings overlap. At the default geometry the crushed
   minor-axis spacing (~112 um) is below the 150 um sheet, so the flattened
   sides of the section are in natural contact; each voxel takes the id of
   the nearest turn midline, which keeps sheets touching and the labels a
   partition of the material.
2. PER-TURN STACKING in fuse. --fuse ti,tj,a0,a1 places each source turn
   ti..tj-1 at its own multiple of the sheet thickness outside the target
   ellipse (centre separation 2*half_t per layer) over the angle range, so a
   k-sheet weld is k distinct touching sheets with their own ids, not one
   coincident shell. That is the double-thickness column a fused region
   shows in CT, with ground truth attached.

Ink is placed at each letter's parametric angle on the PAINTED midline of
its turn rather than at the raw truth coordinates; on partial turns the
truth ellipse (built from the mean winding radius) sits up to a fraction of
a pitch off the painted one, and placing by angle keeps every mark inside
its sheet. Fibers and kollesis bands are not painted here; the volume mode
remains the tool for those.

PHYSICAL-ARM USE
----------------
paint_cell(...) takes the same parameter surface contrast_phantom.emit_cell
uses for its physical arm and returns the same four values, so wiring it in
is three lines at the top of emit_cell's physical branch (see the paint_cell
docstring). The per-cell .npz then carries exact gt_surface and int16
turn_id, which is what scoring fusion rate against true turn ids needs.

USAGE
-----
    python finite_paint.py volume --columns 24 --voxel-um 20 \\
        --fuse 20,22,150,210 --out twin_cell.npz
    python finite_paint.py test                    # the exam
"""

import argparse
import sys
import numpy as np
from scipy import ndimage as ndi

import synthetic_scroll_twin as T

N_SAMPLES = 20000    # parametric samples per turn; keeps the raster gap-free
PAD_MM = 1.0         # air margin around the crushed section


def _turn_curve(t, g, fuse, t_hi, ang):
    """Midline sample points of turn t, with the fuse sector stacked.

    Source turns ti..tj-1 in the welded angle range are moved onto the
    target turn tj's ellipse and pushed outward along the position vector by
    2*half_t per layer, so consecutive sheets sit at contact separation.
    """
    p = g['pitch_um'] / 1000.0
    half_t = g['sheet_um'] / 2000.0
    r_t = g['r0_mm'] + (t + 0.5) * p
    a, b = T.ellipse_axes_for_perimeter(2 * np.pi * r_t, g['ratio'])
    xs, ys = a * np.cos(t_hi), b * np.sin(t_hi)
    if fuse and fuse[0] <= t < fuse[1]:
        a2, b2 = T.ellipse_axes_for_perimeter(
            2 * np.pi * (g['r0_mm'] + (fuse[1] + 0.5) * p), g['ratio'])
        rr = np.hypot(a2 * np.cos(t_hi), b2 * np.sin(t_hi))
        sc = (rr + 2 * half_t * (fuse[1] - t)) / rr
        sel = (ang >= fuse[2]) & (ang <= fuse[3])
        xs = np.where(sel, a2 * np.cos(t_hi) * sc, xs)
        ys = np.where(sel, b2 * np.sin(t_hi) * sc, ys)
    return xs, ys


def paint_labels(meta, g=None, voxel_um=60.0, fuse=None):
    """int16 turn-id labels on one xy slice of the crushed section.

    Returns (labels2d, frame) where frame records the grid geometry. Labels
    are 1-based turn ids; 0 is air. Where two turns' rings claim the same
    voxel, the nearest midline wins.
    """
    g = T.G if g is None else g
    vox = voxel_um / 1000.0
    half_vox = g['sheet_um'] / 2000.0 / vox
    a_out, b_out = meta['section_w_mm'] / 2, meta['section_h_mm'] / 2
    nx = int((2 * a_out + 2 * PAD_MM) / vox)
    ny = int((2 * b_out + 2 * PAD_MM) / vox)
    n_turns = int(np.ceil(meta['n_turns']))
    t_hi = np.linspace(0, 2 * np.pi, N_SAMPLES)
    ang = np.degrees(t_hi) % 360.0
    gy, gx = np.mgrid[0:ny, 0:nx]
    labels = np.zeros((ny, nx), np.int16)
    dist_best = np.full((ny, nx), np.inf, np.float32)
    for t in range(n_turns):
        xs, ys = _turn_curve(t, g, fuse, t_hi, ang)
        fx = np.clip((xs + a_out + PAD_MM) / vox, 0, nx - 1e-6)
        fy = np.clip((ys + b_out + PAD_MM) / vox, 0, ny - 1e-6)
        ix, iy = fx.astype(int), fy.astype(int)
        curve = np.zeros((ny, nx), bool)
        curve[iy, ix] = True
        # subvoxel midline position per raster cell (mean of the samples
        # that landed in it); voxel centres sit at integer+0.5 in fx units
        cnt = np.zeros((ny, nx), np.float32)
        sx = np.zeros((ny, nx), np.float32)
        sy = np.zeros((ny, nx), np.float32)
        np.add.at(cnt, (iy, ix), 1.0)
        np.add.at(sx, (iy, ix), (fx - 0.5).astype(np.float32))
        np.add.at(sy, (iy, ix), (fy - 0.5).astype(np.float32))
        cnt = np.maximum(cnt, 1.0)
        ex, ey = sx / cnt, sy / cnt
        _, (niy, nix) = ndi.distance_transform_edt(~curve,
                                                   return_indices=True)
        d = np.hypot(ey[niy, nix] - gy, ex[niy, nix] - gx).astype(np.float32)
        take = (d <= half_vox) & (d < dist_best)
        labels[take] = t + 1
        dist_best[take] = d[take]
    frame = dict(nx=nx, ny=ny, a_out=a_out, b_out=b_out, vox=vox,
                 half_vox=half_vox, n_turns=n_turns)
    return labels, frame


def paint_volume(truth, meta, g=None, z0=None, z_window_mm=8.0, voxel_um=60.0,
                 fuse=None, rng=None, papyrus=90, ink=200, noise=0.0):
    """Finite-thickness counterpart of make_volume.

    Shares make_volume's parameter surface for z0, z_window_mm, voxel_um,
    fuse, rng, papyrus, ink and noise, and adds nothing else. Returns
    (volume, turn_id, gt_ink, vmeta): the uint8 volume, the int16 instance
    labels, the exact ink mask, and a dict with the frame metadata.
    """
    g = T.G if g is None else g
    rng = rng or np.random.default_rng(0)
    if fuse is not None:
        fuse = (int(fuse[0]), int(fuse[1]), float(fuse[2]), float(fuse[3]))
    labels2d, fr = paint_labels(meta, g=g, voxel_um=voxel_um, fuse=fuse)
    nz = max(int(z_window_mm * 1000 / voxel_um), 1)
    z0 = z0 if z0 is not None else g['page_mm'] / 2 - z_window_mm / 2
    turn_id = np.repeat(labels2d[None, :, :], nz, axis=0)
    vol = np.where(turn_id > 0, papyrus, 0).astype(np.uint8)
    gt_ink = np.zeros_like(vol)

    # ink: each letter at its parametric angle on the painted midline of its
    # turn (see module docstring), fuse-shifted with its sheet
    p = g['pitch_um'] / 1000.0
    half_t = g['sheet_um'] / 2000.0
    inz = (truth['z_mm'] >= z0) & (truth['z_mm'] < z0 + z_window_mm)
    tt = truth['turn'][inz].astype(int)
    x_c, y_c = truth['x_crushed'][inz], truth['y_crushed'][inz]
    r_in, z_in = truth['r_mm'][inz], truth['z_mm'][inz]
    xs, ys = np.empty_like(x_c), np.empty_like(y_c)
    for t in np.unique(tt):
        m = tt == t
        at, bt = T.ellipse_axes_for_perimeter(2 * np.pi * np.mean(r_in[m]),
                                              g['ratio'])
        t_e = np.arctan2(y_c[m] / bt, x_c[m] / at) % (2 * np.pi)
        ap, bp = T.ellipse_axes_for_perimeter(
            2 * np.pi * (g['r0_mm'] + (t + 0.5) * p), g['ratio'])
        px, py = ap * np.cos(t_e), bp * np.sin(t_e)
        if fuse and fuse[0] <= t < fuse[1]:
            a2, b2 = T.ellipse_axes_for_perimeter(
                2 * np.pi * (g['r0_mm'] + (fuse[1] + 0.5) * p), g['ratio'])
            rr = np.hypot(a2 * np.cos(t_e), b2 * np.sin(t_e))
            sc = (rr + 2 * half_t * (fuse[1] - t)) / rr
            adeg = np.degrees(t_e)
            sel = (adeg >= fuse[2]) & (adeg <= fuse[3])
            px = np.where(sel, a2 * np.cos(t_e) * sc, px)
            py = np.where(sel, b2 * np.sin(t_e) * sc, py)
        xs[m], ys[m] = px, py
    ix = np.clip((xs + fr['a_out'] + PAD_MM) / fr['vox'],
                 0, fr['nx'] - 1e-6).astype(int)
    iy = np.clip((ys + fr['b_out'] + PAD_MM) / fr['vox'],
                 0, fr['ny'] - 1e-6).astype(int)
    iz = np.clip((z_in - z0) * 1000 / voxel_um, 0, nz - 1e-6).astype(int)
    on_mat = labels2d[iy, ix] > 0
    vol[iz[on_mat], iy[on_mat], ix[on_mat]] = ink
    gt_ink[iz[on_mat], iy[on_mat], ix[on_mat]] = 1
    ink_dropped = int((~on_mat).sum())

    if noise > 0:
        v = vol.astype(np.float32) + rng.normal(0.0, noise, vol.shape)
        vol = np.clip(v, 0, 255).astype(np.uint8)
    vmeta = dict(z0_mm=z0, voxel_um=voxel_um, shape=vol.shape,
                 half_t_vox=float(fr['half_vox']), n_turns=fr['n_turns'],
                 n_ink=int(on_mat.sum()), ink_dropped=ink_dropped,
                 fuse=list(fuse) if fuse else None)
    return vol, turn_id, gt_ink, vmeta


def paint_cell(n_columns, papyrus, pitch_um, noise, seed=0, z_window_mm=8.0,
               voxel_um=30.0, sheet_um=150.0, fuse=None):
    """One physical-arm phantom with finite thickness and instance labels.

    Same parameter surface as contrast_phantom.emit_cell uses for its
    physical arm: the sheet is held at sheet_um and the gap closes as the
    pitch drops, which is what a crushed scroll does. Returns
    (volume, gt_surface, gt_ink, meta); meta['turn_id'] holds the int16
    label volume, and gt_surface is (turn_id > 0) with no second render,
    exact because the intensity is derived from the labels.

    Wiring into contrast_phantom is three lines at the top of emit_cell's
    physical branch:

        if arm == 'physical':
            import finite_paint
            return finite_paint.paint_cell(n_columns, papyrus, pitch_um,
                                           noise, seed=seed,
                                           z_window_mm=z_window_mm,
                                           voxel_um=voxel_um,
                                           sheet_um=sheet_um)

    build_grid unpacks the same four values unchanged; to carry the labels
    into the per-cell .npz add turn_id=meta['turn_id'] to its savez call.
    """
    g = dict(T.G)
    g['pitch_um'] = pitch_um
    g['sheet_um'] = sheet_um
    old = dict(T.G)
    T.G.update(g)
    try:
        truth, meta = T.build_twin(n_columns, seed=seed)
        vol, turn_id, gt_ink, vmeta = paint_volume(
            truth, meta, g=T.G, z_window_mm=z_window_mm, voxel_um=voxel_um,
            fuse=fuse, rng=np.random.default_rng(seed), papyrus=papyrus,
            ink=min(255, papyrus + 110), noise=noise)
    finally:
        T.G.clear()
        T.G.update(old)
    gt = (turn_id > 0).astype(np.uint8)
    out = dict(meta, **vmeta)
    out['turn_id'] = turn_id
    return vol, gt, gt_ink, out


def _runs(line):
    """Run-length encode a 1-D label line: list of (start, length, ids).

    ids is the set of labels in the run; the empty set marks an air run.
    """
    fg = line > 0
    change = np.flatnonzero(np.diff(fg.astype(np.int8))) + 1
    starts = np.concatenate([[0], change])
    ends = np.concatenate([change, [len(line)]])
    return [(int(s), int(e - s), set(int(v) for v in np.unique(line[s:e]))
             if fg[s] else set())
            for s, e in zip(starts, ends)]


# ---------------------------------------------------------------------------
# Acceptance test (pre-registered)
# ---------------------------------------------------------------------------
def acceptance_test(verbose=True):
    """Four exams, criteria fixed before running. They check that the
    painter puts the declared material where the geometry says, not that any
    detector performs well on it.

    A. THICKNESS IS THE DECLARED THICKNESS. On an unfused build, material
       run lengths along the major axis (where the ray crosses each sheet
       normally) must average the nominal sheet thickness.
       PASS: |mean run - sheet_um / voxel_um| <= 0.5 voxels, at 20 um and
       at 40 um voxels.

    B. THE GAP HAS THE RIGHT SIZE AND SIGN. Physical-arm sweep, sheet fixed
       at 150 um, pitches 300/250/200/160. Along the major axis the
       inter-sheet air gap must fall monotonically and match the predicted
       (layer spacing - sheet) within one voxel. Along the minor axis the
       predicted gap changes sign inside this sweep (+45 um at 300 down to
       -46 um at 160): air must be present where the prediction exceeds one
       voxel and absent where the prediction is negative (contact by the
       nearest-midline rule). Predictions below one voxel are not scored;
       the lattice cannot resolve them.
       PASS: all three conditions.

    C. FUSE MEANS STACKED, NOT COINCIDENT. Build with --fuse 4,6,150,210.
       At the mid-sector angle the connected material run through the target
       turn's radius must contain all three weld ids, distinct, with no air
       inside the run; the same build without the fuse must show the target
       turn isolated at that radius; and no turn id may vanish from the
       fused volume.
       PASS: all three conditions.

    D. LABELS PARTITION THE MATERIAL. On the fused build, the noiseless
       volume's foreground must equal (turn_id > 0) voxel for voxel, every
       ink mark must sit on labelled material, none may be dropped, and the
       z window must actually contain ink.
       PASS: zero mismatched voxels, zero dropped marks, n_ink > 0.
    """
    res = {}
    N = 8
    SHEET = 150.0

    # ---- A ------------------------------------------------------------
    means = {}
    for vox in (20.0, 40.0):
        _, gt, _, meta = paint_cell(N, 90, 300.0, 0.0, z_window_mm=0.1,
                                    voxel_um=vox, sheet_um=SHEET)
        lab = meta['turn_id'][0]
        row = lab[lab.shape[0] // 2]
        lens = [ln for _, ln, ids in _runs(row) if ids]
        means[vox] = float(np.mean(lens))
    errs = {v: abs(means[v] - SHEET / v) for v in means}
    ok_A = all(e <= 0.5 for e in errs.values())
    res['A_thickness'] = dict(mean_runs=means,
                              nominal={v: SHEET / v for v in means},
                              errors_vox=errs, passed=bool(ok_A))

    # ---- B ------------------------------------------------------------
    vox = 30.0
    pitches = (300.0, 250.0, 200.0, 160.0)
    major, minor, pred_major, pred_minor = [], [], [], []
    for p_um in pitches:
        _, gt, _, meta = paint_cell(N, 90, p_um, 0.0, z_window_mm=0.1,
                                    voxel_um=vox, sheet_um=SHEET)
        lab = meta['turn_id'][0]
        cy, cx = lab.shape[0] // 2, lab.shape[1] // 2
        g2 = dict(T.G, pitch_um=p_um, sheet_um=SHEET)
        p_mm = p_um / 1000.0
        a1, b1 = T.ellipse_axes_for_perimeter(
            2 * np.pi * (g2['r0_mm'] + 0.5 * p_mm), g2['ratio'])
        a2, b2 = T.ellipse_axes_for_perimeter(
            2 * np.pi * (g2['r0_mm'] + 1.5 * p_mm), g2['ratio'])
        vox_mm = vox / 1000.0
        pred_major.append(((a2 - a1) - SHEET / 1000.0) / vox_mm)
        pred_minor.append(((b2 - b1) - SHEET / 1000.0) / vox_mm)
        runs_r = _runs(lab[cy, cx:])
        gaps = [ln for _, ln, ids in runs_r[1:-1] if not ids]
        major.append(float(np.mean(gaps)))
        runs_c = _runs(lab[cy:, cx])
        minor.append(sum(ln for _, ln, ids in runs_c[1:-1] if not ids))
    mono = all(major[i] > major[i + 1] for i in range(len(major) - 1))
    close = all(abs(m - pr) <= 1.0 for m, pr in zip(major, pred_major))
    signs = all((mi > 0) if pr > 1.0 else (mi == 0) if pr < 0 else True
                for mi, pr in zip(minor, pred_minor))
    ok_B = mono and close and signs
    res['B_gap_sign'] = dict(pitches=list(pitches), major_gap_vox=major,
                             major_pred_vox=pred_major,
                             minor_air_vox=minor, minor_pred_vox=pred_minor,
                             passed=bool(ok_B))

    # ---- C ------------------------------------------------------------
    fuse = (4, 6, 150.0, 210.0)
    want = {5, 6, 7}                       # ids of turns 4, 5, 6
    vox = 40.0
    _, _, _, mf = paint_cell(N, 90, 173.0, 0.0, z_window_mm=2.9,
                             voxel_um=vox, sheet_um=SHEET, fuse=fuse)
    _, _, _, mu = paint_cell(N, 90, 173.0, 0.0, z_window_mm=0.1,
                             voxel_um=vox, sheet_um=SHEET)
    g2 = dict(T.G, sheet_um=SHEET)
    a_t, _ = T.ellipse_axes_for_perimeter(
        2 * np.pi * (g2['r0_mm'] + (fuse[1] + 0.5) * g2['pitch_um'] / 1000.0),
        g2['ratio'])

    def run_at_target(meta):
        lab = meta['turn_id'][0]
        cy = lab.shape[0] // 2
        row = lab[cy]
        a_out = (lab.shape[1] * vox / 1000.0) / 2
        ixt = int((-a_t + a_out) / (vox / 1000.0))    # mid-sector: 180 deg
        for s, ln, ids in _runs(row):
            if ids and s <= ixt < s + ln:
                return ids
        return set()

    ids_f = run_at_target(mf)
    ids_u = run_at_target(mu)
    n_ids = len(np.unique(mf['turn_id'][mf['turn_id'] > 0]))
    ok_C = want <= ids_f and ids_u == {7} and n_ids == mf['n_turns']
    res['C_fuse_stack'] = dict(fused_run_ids=sorted(ids_f),
                               unfused_run_ids=sorted(ids_u),
                               distinct_ids=n_ids,
                               n_turns=mf['n_turns'], passed=bool(ok_C))

    # ---- D ------------------------------------------------------------
    vol, gt, gt_ink, meta = paint_cell(N, 90, 173.0, 0.0, z_window_mm=2.9,
                                       voxel_um=40.0, sheet_um=SHEET,
                                       fuse=fuse)
    mism = int(np.sum((vol > 0) != (meta['turn_id'] > 0)))
    ink_off = int(np.sum((gt_ink > 0) & (meta['turn_id'] == 0)))
    ok_D = (mism == 0 and ink_off == 0 and meta['ink_dropped'] == 0
            and meta['n_ink'] > 0)
    res['D_partition'] = dict(mismatched=mism, ink_off_material=ink_off,
                              ink_dropped=meta['ink_dropped'],
                              n_ink=meta['n_ink'], passed=bool(ok_D))

    if verbose:
        print("=" * 70)
        print("ACCEPTANCE TEST -- finite_paint (pre-registered)")
        print("=" * 70)
        A = res['A_thickness']
        print("A thickness      "
              + ", ".join(f"{v:.0f} um: run {A['mean_runs'][v]:.2f} vs "
                          f"nominal {A['nominal'][v]:.2f} vox"
                          for v in sorted(A['mean_runs']))
              + f" (each within 0.5) -> {'PASS' if A['passed'] else 'FAIL'}")
        B = res['B_gap_sign']
        print("B gap sign       major-axis gap "
              + " > ".join(f"{x:.2f}" for x in B['major_gap_vox'])
              + " vox, predicted "
              + " / ".join(f"{x:.2f}" for x in B['major_pred_vox'])
              + f"; minor-axis air {B['minor_air_vox']} "
              f"-> {'PASS' if B['passed'] else 'FAIL'}")
        C = res['C_fuse_stack']
        print(f"C fuse stack     welded run carries ids {C['fused_run_ids']} "
              f"(need 5,6,7 touching), unfused run {C['unfused_run_ids']}, "
              f"{C['distinct_ids']}/{C['n_turns']} ids survive -> "
              f"{'PASS' if C['passed'] else 'FAIL'}")
        D = res['D_partition']
        print(f"D partition      {D['mismatched']} mismatched voxels, "
              f"{D['ink_dropped']} dropped ink marks, "
              f"{D['n_ink']} ink voxels on material -> "
              f"{'PASS' if D['passed'] else 'FAIL'}")
        print("-" * 70)
        print("OVERALL:", "PASS" if all(v['passed'] for v in res.values())
              else "FAIL")
    return res


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument('mode', choices=['volume', 'test'])
    ap.add_argument('--columns', type=int, default=24)
    ap.add_argument('--voxel-um', type=float, default=20.0)
    ap.add_argument('--z-window', type=float, default=8.0)
    ap.add_argument('--pitch-um', type=float, default=T.G['pitch_um'])
    ap.add_argument('--sheet-um', type=float, default=T.G['sheet_um'])
    ap.add_argument('--papyrus', type=int, default=90)
    ap.add_argument('--noise', type=float, default=0.0)
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--fuse', type=str, default=None,
                    help='ti,tj,ang0,ang1 -- stack turns ti..tj-1 onto tj '
                         'at contact over the angle range')
    ap.add_argument('--out', type=str, default='twin_cell.npz')
    args = ap.parse_args()

    if args.mode == 'test':
        r = acceptance_test()
        sys.exit(0 if all(v['passed'] for v in r.values()) else 1)

    fuse = (tuple(float(x) for x in args.fuse.split(','))
            if args.fuse else None)
    vol, gt, gt_ink, meta = paint_cell(args.columns, args.papyrus,
                                       args.pitch_um, args.noise,
                                       seed=args.seed,
                                       z_window_mm=args.z_window,
                                       voxel_um=args.voxel_um,
                                       sheet_um=args.sheet_um, fuse=fuse)
    turn_id = meta['turn_id']
    np.savez_compressed(args.out, volume=vol, gt_surface=gt, gt_ink=gt_ink,
                        turn_id=turn_id, papyrus=args.papyrus,
                        pitch_um=args.pitch_um, sheet_um=args.sheet_um,
                        noise=args.noise, voxel_um=args.voxel_um,
                        seed=args.seed,
                        fuse=(list(fuse) if fuse else []),
                        section_w_mm=meta['section_w_mm'],
                        section_h_mm=meta['section_h_mm'],
                        z0_mm=meta['z0_mm'])
    n_inst = len(np.unique(turn_id[turn_id > 0]))
    fg = float((turn_id[0] > 0).mean())
    print(f"[cell ] {args.out} shape {vol.shape} "
          f"({(vol.nbytes + turn_id.nbytes) / 1e6:.0f} MB in memory), "
          f"{n_inst} turn instances, fg {100 * fg:.1f} % per slice, "
          f"half thickness {meta['half_t_vox']:.2f} vox"
          + (f", fused turns {args.fuse}" if fuse else ""))
    if meta['ink_dropped']:
        print(f"[warn ] {meta['ink_dropped']} ink marks fell outside "
              f"material")


if __name__ == '__main__':
    main()
