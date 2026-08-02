#!/usr/bin/env python3
"""
displacement_field.py -- Where the crush put each point of papyrus.

Diego C. V. (vesuvius-topological-grid) -- mode 10.

THE QUESTION
------------
Take the wound cylinder, mark points along the axial striations on its
surface, crush it, and ask where each point ended up. Because the sheet is
inextensible, arc length along a turn is conserved, so a point's position on
the SHEET is recoverable from the crushed shape alone: measure the boundary
r(theta) of a turn, integrate arc length around it, and the arc fraction of a
point is where it sat on the cylinder. The difference between that and its
polar angle in the crushed frame is the displacement.

    displacement(theta) = theta_polar - 360 * (arc length fraction)

This needs no model of the crush. It needs the measured shape of a turn, which
is what a per-ray crossing table provides.

WHAT IT MEASURED ON PHerc1218
-----------------------------
Run over the public per-ray crossing positions (1.39 M crossings, z 1000-11000
on the L1 grid), one ring at a time:

| ring | radius | max displacement | correlation with outer ring |
|------|--------|------------------|-----------------------------|
| 0    | 13.8mm | 16.5 deg         | 1.000                       |
| 16   | 10.5mm | 18.2 deg         | 0.991                       |
| 25   |  8.9mm | 19.0 deg         | 0.984                       |
| 45   |  5.7mm | 19.4 deg         | 0.959                       |

Two results, one confirming the twin and one correcting it.

CONFIRMED -- depth invariance. An arc-length-preserving crush onto ellipses
that scale with r gives a displacement depending only on the arc fraction and
the aspect ratio, identical at every depth. Measured: the profile holds at
r >= 0.959 across a factor 2.4 in radius, and at r = +0.956 between the lower
and upper halves of the scroll. That was a prediction and it survived.

OFF BY 40 % -- amplitude. The twin's 2:1 ellipse predicts a maximum of 12.3
deg at 54 deg from the crease axis. The measurement gives 16.5-19.4 deg with
maxima at 324 and 138-144 deg. The section is close to an ellipse but not one:
fitting the measured boundary gives a = 21.36 mm, b = 10.27 mm, ratio 2.08,
R^2 = 0.948, with a systematic hemispheric residual of about +-0.25 mm. That
2 % of shape asymmetry is too small to move the displacement by 40 %, so the
excess is not yet explained.

A USE, AND A WITHDRAWN CLAIM
----------------------------
The field transfers inward. Applying the outer ring's profile to inner rings
leaves a residual of 0.20-0.33 mm of arc, against a 4.0 mm amplitude -- so a
correction measured where segmentation is easy carries to where it is hard,
which is where the unread text sits.

**Withdrawn: the claim that this corrects an unwrapping error.** An earlier
version of this module argued that an unwrapping mapping by polar angle would
misplace text by two or three letters, and offered the field as the fix. Paul
(ScrollPrize) replied that their renders are flattened by minimising symmetric
Dirichlet energy and do not map by polar angle. The failure mode the argument
rested on does not exist in that pipeline, and minimising distortion over the
whole surface is a better solution than an arc-length lookup in any case. The
measurement stands as a description of the crush; it is not a correction
anyone needs.

WHAT ELSE THE RINGS SAY
-----------------------
- **No longitudinal compression.** If the roll had shortened, material would
  bulge outward where compressed and the section perimeter would track height.
  It does not: median 117.0 mm, correlation with height r = +0.143.
- **But the crush is not uniform along the roll.** Isoperimetric circularity
  of the outer ring runs 0.563 near 125-150 mm of height against 0.806 near
  175-200 mm. The section is markedly flatter in the middle than at the ends.
  (The absolute ratio implied by circularity is biased high by boundary
  roughness -- a jagged contour has extra perimeter for the same area -- so
  read the variation, not the value.)
- **Both ends have lost material rather than been compressed.** Crossings per
  ray run 42 at 0-25 mm of height and 44-48 at 175-225, against 81 in the
  middle. Fewer windings in a cross-section means material absent; axial
  compression would not reduce the count.

USAGE
-----
    python displacement_field.py field  --rings RINGS.npz
    python displacement_field.py rings  --rings RINGS.npz --plot rings3d.png
    python displacement_field.py test

RINGS.npz carries `theta_deg` (n_theta,) and `r_um` (n_z, n_theta, n_ring):
the measured boundary radius of each ring at each height. Build it from any
per-ray crossing table; `--from-csv` does it for the published PHerc1218
format (columns z, theta_deg, k, r_um).
"""

import argparse
import sys
import numpy as np


# ---------------------------------------------------------------------------
# Core: shape -> displacement
# ---------------------------------------------------------------------------
def arc_fraction(theta_deg, r):
    """Cumulative arc length around a closed polar curve, as a fraction.

    The curve is closed by repeating the first point. Segment lengths are
    chords, which under-reads a smooth curve by O(dtheta^2) -- at the 6 deg
    sampling of the published table that is 0.05 %, well below the effects
    measured here.
    """
    th = np.radians(np.asarray(theta_deg, float))
    r = np.asarray(r, float)
    thc = np.concatenate([th, th[:1]])
    rc = np.concatenate([r, r[:1]])
    x, y = rc * np.cos(thc), rc * np.sin(thc)
    seg = np.hypot(np.diff(x), np.diff(y))
    s = np.concatenate([[0.0], np.cumsum(seg)])
    return s[:-1] / s[-1], s[-1]


def displacement(theta_deg, r, centre=True):
    """Angular displacement of each material point, in degrees.

    Zero of the profile is arbitrary -- it depends where arc integration
    starts -- so the median is removed unless `centre` is False.
    """
    f, perim = arc_fraction(theta_deg, r)
    d = ((np.asarray(theta_deg, float) - 360.0 * f + 180.0) % 360.0) - 180.0
    if centre:
        d = d - np.median(d)
    return d, perim


def ellipse_axes(perim, ratio):
    """Semi-axes of the ellipse of given perimeter and aspect ratio."""
    h = ((ratio - 1) / (ratio + 1)) ** 2
    c = np.pi * (1 + 1 / ratio) * (1 + 3 * h / (10 + np.sqrt(4 - 3 * h)))
    a = perim / c
    return a, a / ratio


def analytic_profile(ratio, theta_deg, r_mm=10.0):
    """The twin's prediction: displacement on an equal-perimeter ellipse."""
    a, b = ellipse_axes(2 * np.pi * r_mm, ratio)
    t = np.linspace(0, 2 * np.pi, 200000)
    ds = np.sqrt((a * np.sin(t)) ** 2 + (b * np.cos(t)) ** 2)
    s = np.concatenate([[0.0], np.cumsum(0.5 * (ds[1:] + ds[:-1]) * np.diff(t))])
    f_tab = s / s[-1]
    f = np.asarray(theta_deg, float) / 360.0
    te = np.interp(f, f_tab, t)
    th_out = np.degrees(np.arctan2(b * np.sin(te), a * np.cos(te))) % 360.0
    d = ((th_out - 360.0 * f + 180.0) % 360.0) - 180.0
    return d - np.median(d)


def fit_ellipse(theta_deg, r):
    """Best symmetric ellipse to a measured boundary. Returns (a, b, phi, R2)."""
    th = np.radians(np.asarray(theta_deg, float))
    r = np.asarray(r, float)
    best = None
    for a in np.linspace(0.6 * r.max(), 1.4 * r.max(), 60):
        for ratio in np.linspace(1.05, 4.0, 60):
            b = a / ratio
            for phi in np.linspace(0, 180, 37):
                t = th - np.radians(phi)
                pred = a * b / np.sqrt((b * np.cos(t)) ** 2 + (a * np.sin(t)) ** 2)
                res = np.sum((r - pred) ** 2)
                if best is None or res < best[0]:
                    best = (res, a, b, phi)
    res, a, b, phi = best
    ss = np.sum((r - r.mean()) ** 2)
    return a, b, phi, 1 - res / ss


def transfer_residual(theta_deg, r_ref, r_target):
    """Error of applying one ring's profile to another, best scale allowed."""
    d0, _ = displacement(theta_deg, r_ref)
    d1, _ = displacement(theta_deg, r_target)
    k = np.sum(d1 * d0) / np.sum(d0 * d0)
    return float(np.sqrt(np.mean((d1 - k * d0) ** 2)))


# ---------------------------------------------------------------------------
def acceptance_test(verbose=True):
    """Pre-registered.

    A. ARC INTEGRATION AGAINST THE CLOSED FORM. Build an exact 2.08:1
       ellipse, sample it at the 6 deg grid of the published table, and compare
       the chord-based arc fraction against the exact elliptic arc fraction at
       the same polar angles.
       PASS: max deviation < 0.002 of a turn (0.7 deg of arc position).
       A first version of this exam compared the measured displacement profile
       against the analytic one pointwise and failed at 2.75 deg. That was the
       exam's error, not the code's: the two are inverse functions -- one maps
       arc fraction to polar angle, the other polar angle to arc fraction -- so
       evaluating both on the same numeric grid compares different material
       points. Testing the arc integration directly avoids the confusion and
       is what the claim actually rests on.

    B. DEPTH INVARIANCE IS EXACT FOR NESTED ELLIPSES. The twin's claim is
       that an arc-length-preserving crush gives the same displacement at
       every depth. On synthetic nested ellipses this must hold to numerical
       precision -- it is the prediction the real data then confirmed at
       r >= 0.959.
       PASS: profiles at r = 5, 10 and 16 mm agree to < 0.01 deg.

    C. AMPLITUDE SCALES WITH THE CRUSH. The maximum displacement must grow
       monotonically with the aspect ratio and vanish as the section becomes
       circular.
       PASS: monotone over 1.1 to 4.0, and < 0.2 deg at ratio 1.001. The
       second half matters: a method that reported displacement on an
       uncrushed roll would be measuring its own discretisation.

    D. TRANSFER IS BETTER THAN NOTHING, AND THE TEST SAYS BY HOW MUCH. Apply
       a 2.08:1 profile to a 2.6:1 ring -- a deliberately worse mismatch than
       anything in the real scroll.
       PASS: the residual after transfer is below a third of the target's own
       amplitude. Stated as a ratio rather than an absolute so the exam does
       not silently pass by shrinking the signal.
    """
    res = {}
    th = np.arange(0, 360, 6.0)

    def ellipse_r(ratio, r_mm):
        a, b = ellipse_axes(2 * np.pi * r_mm, ratio)
        t = np.radians(th)
        return a * b / np.sqrt((b * np.cos(t)) ** 2 + (a * np.sin(t)) ** 2)

    # A -- chord-based arc fraction vs the exact elliptic one
    R0 = 2.08
    a, b = ellipse_axes(2 * np.pi * 10.0, R0)
    f_chord, _ = arc_fraction(th, ellipse_r(R0, 10.0))
    t = np.linspace(0, 2 * np.pi, 400000)
    ds = np.sqrt((a * np.sin(t)) ** 2 + (b * np.cos(t)) ** 2)
    s_cum = np.concatenate([[0.0], np.cumsum(0.5*(ds[1:]+ds[:-1])*np.diff(t))])
    # parametric angle at each sampled polar angle
    t_of_th = np.arctan2(a * np.sin(np.radians(th)), b * np.cos(np.radians(th)))
    t_of_th = np.mod(t_of_th, 2 * np.pi)
    f_exact = np.interp(t_of_th, t, s_cum / s_cum[-1])
    # both start their integration at theta = 0, so remove the common offset
    dev = float(np.max(np.abs(((f_chord - f_exact) + 0.5) % 1.0 - 0.5)))
    res['A_arc_integration'] = dict(max_dev=dev, passed=bool(dev < 0.002))

    # B
    profs = [displacement(th, ellipse_r(2.08, r))[0] for r in (5.0, 10.0, 16.0)]
    spread = float(max(np.max(np.abs(profs[i] - profs[0])) for i in (1, 2)))
    res['B_depth_invariance'] = dict(spread=spread, passed=bool(spread < 0.01))

    # C
    amps = [float(np.max(np.abs(displacement(th, ellipse_r(R, 10.0))[0])))
            for R in (1.1, 1.5, 2.08, 3.0, 4.0)]
    flat = float(np.max(np.abs(displacement(th, ellipse_r(1.001, 10.0))[0])))
    okC = all(amps[i] < amps[i + 1] for i in range(4)) and flat < 0.2
    res['C_scaling'] = dict(amps=amps, circular=flat, passed=bool(okC))

    # D
    r_ref, r_tgt = ellipse_r(2.08, 10.0), ellipse_r(2.6, 10.0)
    resid = transfer_residual(th, r_ref, r_tgt)
    amp_t = float(np.max(np.abs(displacement(th, r_tgt)[0])))
    ratio = resid / amp_t
    res['D_transfer'] = dict(residual=resid, amplitude=amp_t, ratio=ratio,
                             passed=bool(ratio < 0.33))

    if verbose:
        print("=" * 70)
        print("ACCEPTANCE TEST -- displacement_field (pre-registered)")
        print("=" * 70)
        A = res['A_arc_integration']
        print(f"A arc integration   max dev from exact elliptic arc "
              f"{A['max_dev']:.2e} of a turn ({360*A['max_dev']:.3f} deg) "
              f"(<0.002) -> {'PASS' if A['passed'] else 'FAIL'}")
        B = res['B_depth_invariance']
        print(f"B depth invariance  r=5/10/16 mm agree to {B['spread']:.2e} deg "
              f"(<0.01) -> {'PASS' if B['passed'] else 'FAIL'}")
        C = res['C_scaling']
        print(f"C amplitude scales  "
              + " < ".join(f"{a:.1f}" for a in C['amps'])
              + f" deg; circular gives {C['circular']:.3f} (<0.2) -> "
              f"{'PASS' if C['passed'] else 'FAIL'}")
        D = res['D_transfer']
        print(f"D transfer          residual {D['residual']:.2f} of amplitude "
              f"{D['amplitude']:.2f} deg = {100*D['ratio']:.0f} % (<33) -> "
              f"{'PASS' if D['passed'] else 'FAIL'}")
        print("-" * 70)
        print("OVERALL:", "PASS" if all(v['passed'] for v in res.values())
              else "FAIL")
    return res


# ---------------------------------------------------------------------------
def load_rings(path):
    z = np.load(path)
    return z['theta_deg'], z['r_um']


def rings_from_csv(path, ring_idx=(0, 4, 9, 16), z_lo=1000, z_hi=11000):
    """Build the ring array from a per-ray crossing table (gzip csv ok)."""
    import csv, gzip
    from collections import defaultdict
    op = gzip.open if str(path).endswith('.gz') else open
    d = defaultdict(list)
    with op(path, 'rt') as f:
        for x in csv.DictReader(f):
            zz = float(x['z'])
            if z_lo < zz < z_hi:
                d[(zz, float(x['theta_deg']))].append(float(x['r_um']))
    zs = sorted({k[0] for k in d})
    ths = np.array(sorted({k[1] for k in d}))
    R = np.full((len(zs), len(ths), len(ring_idx)), np.nan)
    for iz, zz in enumerate(zs):
        for it, t in enumerate(ths):
            v = d.get((zz, t))
            if not v:
                continue
            v = sorted(v)[::-1]
            for ir, j in enumerate(ring_idx):
                if len(v) > j:
                    R[iz, it, ir] = v[j]
    return ths, R


def flat_sheet(th, R, n_samp=120):
    """Every winding, every height, straightened into a strip.

    READING ORIENTATION. A book roll is stored with the START of the text on
    the OUTSIDE: the reader holds the roll in the right hand, draws the free
    end leftwards, and winds the read portion onto the left. So the outermost
    winding is the first column and the core is the end -- which is why
    Herculaneum end-titles survive, sitting at the protected core, and why
    outer loss costs the OPENING of a work rather than its close.

    The ink is on the inward-facing side. Papyrus is written on the recto,
    horizontal fibres, and the roll is wound recto-inward, so the text faces
    the core and the blank verso takes the outside. It is never exposed --
    the same recto-inward assumption the fibre-strain work of mode 8 rests on.

    So the sheet below runs first column at ring 0 to last at the innermost
    resolved winding. One honest caveat on the horizontal axis: the winding
    SENSE is not firmly established for PHerc1218 (its author set it from a
    single multi-turn instance and noted the constraints are mirror-symmetric),
    so a wrong sense mirrors the arc axis and the text would read reversed.
    """
    nz, nth, nring = R.shape
    L = np.full((nz, nring), np.nan)
    D = np.full((nz, nring, n_samp), np.nan)
    g = np.linspace(0, 1, n_samp, endpoint=False)
    for iz in range(nz):
        for j in range(nring):
            r = R[iz, :, j]
            if not np.isfinite(r).all():
                continue
            f, per = arc_fraction(th, r)
            d = ((np.asarray(th, float) - 360.0 * f + 180.0) % 360.0) - 180.0
            d = d - np.median(d)
            L[iz, j] = per
            D[iz, j] = np.interp(g, np.append(f, 1.0), np.append(d, d[0]))
    return L, D


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument('mode', choices=['field', 'rings', 'sheet', 'test'])
    ap.add_argument('--rings', type=str, default=None)
    ap.add_argument('--from-csv', type=str, default=None)
    ap.add_argument('--plot', type=str, default=None)
    ap.add_argument('--n-heights', type=int, default=9)
    ap.add_argument('--n-rings', type=int, default=46,
                    help='how deep to peel; beyond ~45 the spiral fit degrades')
    ap.add_argument('--rows', type=int, default=5,
                    help='how many runs to cut the flat sheet into')
    args = ap.parse_args()

    if args.mode == 'test':
        r = acceptance_test()
        sys.exit(0 if all(v['passed'] for v in r.values()) else 1)

    if args.from_csv:
        th, R = rings_from_csv(args.from_csv)
    elif args.rings:
        th, R = load_rings(args.rings)
    else:
        sys.exit("field/rings need --rings or --from-csv")

    n_ring = R.shape[2]
    print(f"[data] {R.shape[0]} heights x {len(th)} angles x {n_ring} rings")
    print(f"\n  {'ring':>5} {'radius':>9} {'|disp| max':>11} {'r vs outer':>11} "
          f"{'transfer resid':>15}")
    prof0 = None
    for ir in range(n_ring):
        acc = [displacement(th, R[iz, :, ir])[0]
               for iz in range(R.shape[0]) if np.isfinite(R[iz, :, ir]).all()]
        if len(acc) < 10:
            continue
        p = np.median(acc, axis=0)
        rm = np.nanmedian(R[:, :, ir]) / 1000
        if prof0 is None:
            prof0, r0 = p, rm
            print(f"  {ir:>5} {rm:>8.1f}mm {np.abs(p).max():>10.1f}d "
                  f"{1.0:>11.3f} {'--':>15}")
        else:
            cc = np.corrcoef(prof0, p)[0, 1]
            k = np.sum(p * prof0) / np.sum(prof0 * prof0)
            resid = np.sqrt(np.mean((p - k * prof0) ** 2))
            print(f"  {ir:>5} {rm:>8.1f}mm {np.abs(p).max():>10.1f}d "
                  f"{cc:>11.3f} {np.radians(resid)*rm:>13.2f}mm")

    # section shape of the outer ring
    ok = [iz for iz in range(R.shape[0]) if np.isfinite(R[iz, :, 0]).all()]
    r_med = np.median(R[ok, :, 0], axis=0) / 1000
    a, b, phi, r2 = fit_ellipse(th, r_med)
    print(f"\n[shape] best symmetric ellipse a={a:.2f} b={b:.2f} mm, "
          f"ratio {a/b:.2f}, tilt {phi:.0f} deg, R2={r2:.3f}")
    pred = a * b / np.sqrt((b*np.cos(np.radians(th-phi)))**2
                           + (a*np.sin(np.radians(th-phi)))**2)
    h1 = np.mean((r_med - pred)[th < 180]); h2 = np.mean((r_med - pred)[th >= 180])
    print(f"        hemispheric residual {h1:+.2f} / {h2:+.2f} mm "
          f"-- {abs(h1-h2)/a*100:.1f} % of the semi-major axis")
    print(f"        twin prediction at this ratio: "
          f"{np.abs(analytic_profile(a/b, th)).max():.1f} deg max")

    if args.mode == 'field':
        return

    if args.mode == 'sheet':
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        L, D = flat_sheet(th, R)
        # ACCUMULATE PER HEIGHT, not from a median perimeter. An earlier
        # version used the median and it sheared the sheet badly: measured on
        # PHerc1218 the cumulative arc position after 46 windings varies by
        # 1779 mm between heights -- 44 % of the sheet length -- so a column
        # drawn against median cuts drifts by ~180 mm top to bottom, four
        # column widths. The variation accumulates rather than drifting (the
        # correlation with height is only +0.146), because each winding's
        # perimeter varies ~9.8 % between heights and the errors add.
        C = np.nancumsum(np.where(np.isfinite(L), L, 0.0), axis=1)
        Lm = np.nanmedian(L, axis=0)          # kept only for the row layout
        edges = np.concatenate([[0], np.cumsum(Lm)])
        total, NS = edges[-1], D.shape[2]
        spread = np.nanmax(C[:, -1]) - np.nanmin(C[:, -1])
        print(f"[shear ] cumulative position after {L.shape[1]} windings varies "
              f"{spread:.0f} mm between heights ({100*spread/np.nanmedian(C[:,-1]):.0f} % "
              f"of sheet length)")
        print(f"[limit ] much of that is segmentation, not papyrus: a winding "
              f"cannot change length by 9 % over a few mm of height. Following "
              f"each winding as a continuous object through z -- rather than "
              f"per-slice -- needs surface tracking, which is not in this repo.")
        zmm = np.arange(R.shape[0], dtype=float)
        print(f"[sheet ] {L.shape[1]} windings x {L.shape[0]} heights x {NS} "
              f"points = {total/1000:.2f} m of sheet, "
              f"{100*np.isfinite(L).mean():.0f} % of cells measured")
        print(f"[order ] ring 0 is the OUTERMOST winding, i.e. the FIRST column: "
              f"a roll is stored start-outward. The core is the end of the work.")
        per_row = total / args.rows
        fig, axes = plt.subplots(args.rows, 1, figsize=(15.5, 2.1*args.rows),
                                 sharex=True)
        vm = np.nanpercentile(np.abs(D), 98)
        for row, ax in enumerate(np.atleast_1d(axes)):
            x0, x1 = row*per_row, (row+1)*per_row
            for j in range(L.shape[1]):
                a, b = edges[j], edges[j+1]
                if b < x0 or a > x1:
                    continue
                xs = np.linspace(a, b, NS, endpoint=False)
                m = (xs >= x0) & (xs < x1)
                if not m.any():
                    continue
                # NOTE: the row layout uses median cuts, so this figure shows
                # the deformation field and the coverage, NOT metric position.
                # Per-height cumulative arc is in C above; see the shear warning.
                ax.pcolormesh(xs[m]-x0, zmm, D[:, j, :][:, m], cmap='coolwarm',
                              vmin=-vm, vmax=vm, shading='nearest',
                              rasterized=True)
                ax.axvline(a-x0, color='k', lw=.45, alpha=.5)
            ax.set_xlim(0, per_row)
            ax.set_ylabel(f'{x0/1000:.2f}-{x1/1000:.2f} m', fontsize=8)
        np.atleast_1d(axes)[-1].set_xlabel('arc position within each run (mm) '
                                           '-- reading runs left to right, '
                                           'outermost winding first')
        sm = plt.cm.ScalarMappable(cmap='coolwarm',
                                   norm=plt.Normalize(-vm, vm))
        cb = fig.colorbar(sm, ax=np.atleast_1d(axes).tolist(), shrink=.6, pad=.012)
        cb.set_label('crush displacement (deg)')
        out = args.plot or 'sheet.png'
        fig.savefig(out, dpi=140, bbox_inches='tight')
        print(f"[plot  ] {out}")
        return

    # --- 3D comparison figure -------------------------------------------
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
    sel = np.linspace(0, R.shape[0] - 1, args.n_heights).astype(int)
    thr = np.radians(th)
    fig = plt.figure(figsize=(15.5, 7.6))
    for panel, (title, mode) in enumerate(
            [('BEFORE -- cylinder reconstructed by arc length', 'ini'),
             ('AFTER -- measured shape', 'fin')]):
        ax = fig.add_subplot(1, 2, panel + 1, projection='3d')
        for ir, lw in zip(range(n_ring), np.linspace(1.9, 0.9, n_ring)):
            for iz in sel:
                r = R[iz, :, ir]
                if not np.isfinite(r).all():
                    continue
                f, perim = arc_fraction(th, r)
                if mode == 'ini':
                    rc = perim / (2 * np.pi)
                    X, Y = rc*np.cos(2*np.pi*f)/1000, rc*np.sin(2*np.pi*f)/1000
                else:
                    X, Y = r*np.cos(thr)/1000, r*np.sin(thr)/1000
                Z = np.full_like(X, iz * 1.0)
                ax.plot(np.append(X, X[0]), np.append(Y, Y[0]),
                        np.append(Z, Z[0]), color='0.55', lw=lw*0.45, zorder=1)
                ax.scatter(X, Y, Z, c=f, cmap='twilight', s=7*lw,
                           vmin=0, vmax=1, depthshade=False, zorder=3)
        ax.set_title(title, fontsize=11, pad=2)
        ax.set_xlabel('mm'); ax.set_ylabel('mm'); ax.set_zlabel('height index')
        ax.view_init(elev=22, azim=-58)
    sm = plt.cm.ScalarMappable(cmap='twilight', norm=plt.Normalize(0, 1))
    cb = fig.colorbar(sm, ax=fig.axes, shrink=.55, pad=.04)
    cb.set_label('position of the material point on the sheet (arc fraction)')
    fig.suptitle('Material points before and after the crush -- '
                 'colour is the SAME papyrus in both panels', fontsize=12.5, y=.97)
    out = args.plot or 'rings3d.png'
    fig.savefig(out, dpi=150, bbox_inches='tight')
    print(f"[plot] {out}")


if __name__ == '__main__':
    main()
