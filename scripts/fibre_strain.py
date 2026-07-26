#!/usr/bin/env python3
"""
fibre_strain.py -- Where does the papyrus crack when the roll is crushed?

Diego C. V. (vesuvius-topological-grid) -- mode 9.

THE OBSERVATION THIS IMPLEMENTS
-------------------------------
Crushing does not load the sheet evenly. Curvature of the flattened section
is extreme at the two fold ends and gentle along the flattened sides, so the
bending strain -- and therefore the lateral separation of fibres -- is
concentrated at the folds and negligible in the middle of the flat.

That is a prediction with an angular signature, and it is complementary to
one we already had: layers MERGE on the flattened axis (where the crush packs
them below the nominal winding pitch) and the sheet CRACKS on the fold axis
(where the curvature change is largest). Two different pathologies at two
different angles, from one geometry.

WHICH FACE, AND WHY THE VERTICAL FIBRES
---------------------------------------
Papyrus is a two-ply cross laminate: recto fibres run along the roll's length
(the writing direction), verso fibres run along the roll's axis. Herculaneum
rolls are wound with the written recto inward, so at a fold the verso is the
CONVEX face and takes the tension, while the recto is compressed.

The tension at a fold acts circumferentially -- along the arc. The recto
fibres lie along that direction and resist it in the way fibres are strong:
along their own axis. The verso fibres lie ACROSS it, so they carry no load
in that direction and the only thing that can give is the bond between them.
They separate laterally. That is why it is the vertical fibres that open up,
and it is a consequence of the laminate structure, not an assumption.

THE REFERENCE STATE MATTERS, AND IT IS NOT FLAT
-----------------------------------------------
A first version of this calculation used absolute curvature and reported a
fold/flat strain ratio of exactly (a/b)^3 = 8 for a 2:1 crush. That is the
ratio you get if the sheet is stress-free when FLAT -- true of fresh papyrus
being wound for the first time, false here.

These rolls stood wound for decades and then carbonized in that shape. The
stress-free reference is the WOUND state, not the flat sheet, so what
produces strain is the CHANGE in curvature from 1/r:

    eps(theta) = (t / 2) * | kappa_crushed(theta) - 1/r |

Under that model the picture changes in an interesting way. At the fold the
sheet is sharpened (kappa 1/r -> 3.084/r); along the flat it is UNBENT
(kappa 1/r -> 0.386/r) -- and unbending strains the material too. So the
flat sides are not unloaded, merely less loaded, and the ratio falls from
8.0x to **3.39x**. Both models are implemented; `--reference flat` reproduces
the earlier number so the two can be compared. `wound` is the default because
it is the defensible one.

WHAT IS DERIVED AND WHAT IS ASSUMED
-----------------------------------
Derived, needing no calibration: the curvature field of an equal-perimeter
2:1 ellipse, the fold/flat ratio, and the radial gradient (strain scales as
1/r, so the innermost turns are worst). These follow from the measured 2:1
section alone.

Assumed, and dominating the absolute numbers: sheet thickness (0.150 mm) and
the failure strain of carbonized papyrus. Carbonized papyrus is brittle and
fails at strains far below those of fresh papyrus, but no number for it is
adopted here as fact -- `--failure-strain` is a knob, and the tool reports
the threshold crossing for whatever you set. The MAP is the result; the
absolute percentages are provisional.

USAGE
-----
    python fibre_strain.py map                      # strain vs angle and turn
    python fibre_strain.py map --plot fibre.png
    python fibre_strain.py map --reference flat     # the earlier 8x model
    python fibre_strain.py test
"""

import argparse
import sys
import numpy as np

SHEET_MM = 0.150         # assumed
RATIO = 2.0              # measured crush, PHerc1218
R0_MM = 4.1              # assumed umbilicus
PITCH_MM = 0.173         # contested; see docs/data_sources.md
N_TURNS = 70
FAILURE_STRAIN = 0.01    # 1 %, a placeholder -- see the docstring


def ellipse_semi_axes(r_mm, ratio=RATIO):
    """Semi-axes of the equal-perimeter ellipse for a winding at radius r."""
    h = ((ratio - 1) / (ratio + 1)) ** 2
    c = np.pi * (1 + 1 / ratio) * (1 + 3 * h / (10 + np.sqrt(4 - 3 * h)))
    a = 2 * np.pi * r_mm / c
    return a, a / ratio


def curvature(a, b, theta_rad):
    """Curvature of the ellipse at the parametric angle t.

    kappa = a b / (a^2 sin^2 t + b^2 cos^2 t)^{3/2}
    Maximum at t=0, pi (the fold ends of the long axis), minimum at
    t=pi/2, 3pi/2 (the middle of the flattened sides).
    """
    s, c = np.sin(theta_rad), np.cos(theta_rad)
    return a * b / (a ** 2 * s ** 2 + b ** 2 * c ** 2) ** 1.5


def strain(r_mm, theta_rad, sheet_mm=SHEET_MM, ratio=RATIO,
           reference='wound'):
    """Surface bending strain from the change in curvature.

    reference='wound' : stress-free at the winding curvature 1/r (defensible)
    reference='flat'  : stress-free flat (reproduces the earlier 8x ratio)
    """
    a, b = ellipse_semi_axes(r_mm, ratio)
    k = curvature(a, b, theta_rad)
    k_ref = (1.0 / r_mm) if reference == 'wound' else 0.0
    return (sheet_mm / 2.0) * np.abs(k - k_ref)


def neutral_angle_deg(ratio=RATIO, n=200000):
    """The angle at which the crushed curvature equals the winding curvature.

    Between the sharpened fold and the unbent flat, kappa passes through 1/r.
    There the crush leaves the sheet exactly as it was: unstrained. Four such
    angles per section, symmetric about both axes.

    It is SCALE INVARIANT -- a and b both scale with r, so kappa*r depends
    only on theta and the aspect ratio. The same angle at every depth. That
    makes it invertible: measuring where the pristine sectors lie measures the
    crush ratio, independently of pitch, umbilicus, thickness and grid.
    """
    th = np.linspace(1e-6, np.pi / 2, n)
    a, b = ellipse_semi_axes(1.0, ratio)
    k = curvature(a, b, th)
    return float(np.degrees(th[np.argmin(np.abs(k - 1.0))]))


def ratio_from_neutral_angle(angle_deg, lo=1.05, hi=6.0, n=4000):
    """Invert the above: a measured pristine angle gives the crush ratio."""
    grid = np.linspace(lo, hi, n)
    ang = np.array([neutral_angle_deg(R, n=4000) for R in grid])
    return float(grid[np.argmin(np.abs(ang - angle_deg))])


def fold_flat_ratio(ratio=RATIO, reference='wound'):
    """Closed form at the two vertices. Independent of r and of thickness."""
    a, b = ellipse_semi_axes(1.0, ratio)      # r = 1
    k_fold, k_flat = a / b ** 2, b / a ** 2
    k_ref = 1.0 if reference == 'wound' else 0.0
    return abs(k_fold - k_ref) / abs(k_flat - k_ref)


def strain_map(reference='wound', sheet_mm=SHEET_MM, ratio=RATIO,
               r0=R0_MM, pitch=PITCH_MM, n_turns=N_TURNS, n_theta=360):
    turns = np.arange(n_turns)
    r = r0 + (turns + 0.5) * pitch
    th = np.radians(np.arange(n_theta))
    E = np.empty((n_turns, n_theta))
    for i, ri in enumerate(r):
        E[i] = strain(ri, th, sheet_mm, ratio, reference)
    return turns, r, np.degrees(th), E


# --------------------------------------------------------------------------
def acceptance_test(verbose=True):
    """Pre-registered.

    A. NO CRUSH, NO STRAIN. With ratio = 1 the section is a circle of the
       same perimeter, so the curvature is unchanged everywhere and the
       wound-reference strain must vanish.
       PASS: max strain < 1e-12 at ratio 1.0. This is the exam that tests
       whether the reference state is implemented correctly; the flat-
       reference model FAILS it by construction, which is the point.
    B. CLOSED FORM AT THE VERTICES. The numeric map's maximum and minimum
       over theta must match the analytic fold/flat values.
       PASS: both within 0.1 %, and the ratio equals 3.39 (wound) /
       8.00 (flat) within 0.5 %.
    C. RADIAL GRADIENT. Strain scales as 1/r, so the innermost turn must be
       strained more than the outermost by exactly r_out / r_in.
       PASS: within 0.1 %.
    """
    res = {}

    # A
    _, _, _, E1 = strain_map(reference='wound', ratio=1.0, n_turns=5)
    _, _, _, E1f = strain_map(reference='flat', ratio=1.0, n_turns=5)
    okA = float(np.max(E1)) < 1e-12 and float(np.max(E1f)) > 1e-6
    res['A_no_crush'] = dict(max_wound=float(np.max(E1)),
                             max_flat=float(np.max(E1f)), passed=bool(okA))

    # B
    turns, r, th, E = strain_map(reference='wound')
    i = len(turns) // 2
    # compare at the VERTICES, not max/min over theta: the profile passes
    # through ZERO at the neutral angle, so min(theta) is that zero, not the
    # flat-vertex value. Finding this is what the exam is for.
    num_fold, num_flat = float(E[i][0]), float(E[i][90])
    num_ratio = num_fold / num_flat
    ana_ratio = fold_flat_ratio(reference='wound')
    a, b = ellipse_semi_axes(r[i])
    ana_fold = (SHEET_MM / 2) * abs(a / b ** 2 - 1 / r[i])
    ana_flat = (SHEET_MM / 2) * abs(b / a ** 2 - 1 / r[i])
    okB = (abs(num_fold - ana_fold) / ana_fold < 1e-3 and
           abs(num_flat - ana_flat) / ana_flat < 1e-3 and
           abs(num_ratio - 3.39) / 3.39 < 5e-3 and
           abs(fold_flat_ratio(reference='flat') - 8.0) / 8.0 < 5e-3)
    res['B_closed_form'] = dict(numeric_ratio=num_ratio,
                                analytic_ratio=float(ana_ratio),
                                flat_model_ratio=float(
                                    fold_flat_ratio(reference='flat')),
                                passed=bool(okB))

    # D -- neutral angle: invariant, and invertible
    angs = [neutral_angle_deg(RATIO)]
    inner = strain_map(reference='wound', n_turns=3)[3]
    outer = strain_map(reference='wound', n_turns=70)[3]
    # the map is sampled at 1 deg per column, so argmin IS the angle in deg
    a_in = float(np.argmin(inner[0][:90]))
    a_out = float(np.argmin(outer[-1][:90]))
    back = ratio_from_neutral_angle(angs[0])
    okD = (abs(a_in - a_out) < 1.0 and abs(back - RATIO) / RATIO < 0.02)
    res['D_neutral'] = dict(angle_deg=angs[0], inner=a_in, outer=a_out,
                            ratio_recovered=back, passed=bool(okD))

    # C
    grad = float(E[0][0] / E[-1][0])
    expect = float(r[-1] / r[0])
    okC = abs(grad - expect) / expect < 1e-3
    res['C_radial'] = dict(measured=grad, expected=expect, passed=bool(okC))

    if verbose:
        print("=" * 70)
        print("ACCEPTANCE TEST -- fibre_strain (pre-registered)")
        print("=" * 70)
        A = res['A_no_crush']
        print(f"A no crush no strain  ratio 1:1 -> wound model "
              f"{A['max_wound']:.1e} (must vanish), flat model "
              f"{A['max_flat']:.2e} (must not) -> "
              f"{'PASS' if A['passed'] else 'FAIL'}")
        B = res['B_closed_form']
        print(f"B closed form         fold/flat = {B['numeric_ratio']:.3f} "
              f"numeric vs {B['analytic_ratio']:.3f} analytic; flat-reference "
              f"model gives {B['flat_model_ratio']:.2f} -> "
              f"{'PASS' if B['passed'] else 'FAIL'}")
        D = res['D_neutral']
        print(f"D neutral angle       {D['angle_deg']:.2f} deg, same at turn 0 "
              f"({D['inner']:.0f}) and turn 69 ({D['outer']:.0f}); inverts to "
              f"ratio {D['ratio_recovered']:.2f} -> "
              f"{'PASS' if D['passed'] else 'FAIL'}")
        C = res['C_radial']
        print(f"C radial gradient     inner/outer = {C['measured']:.4f} vs "
              f"r_out/r_in = {C['expected']:.4f} -> "
              f"{'PASS' if C['passed'] else 'FAIL'}")
        print("-" * 70)
        print("OVERALL:", "PASS" if all(v['passed'] for v in res.values())
              else "FAIL")
    return res


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument('mode', choices=['map', 'test'])
    ap.add_argument('--reference', choices=['wound', 'flat'], default='wound')
    ap.add_argument('--sheet-um', type=float, default=SHEET_MM * 1000)
    ap.add_argument('--ratio', type=float, default=RATIO)
    ap.add_argument('--failure-strain', type=float, default=FAILURE_STRAIN)
    ap.add_argument('--plot', type=str, default=None)
    ap.add_argument('--csv', type=str, default=None)
    args = ap.parse_args()

    if args.mode == 'test':
        r = acceptance_test()
        sys.exit(0 if all(v['passed'] for v in r.values()) else 1)

    t_mm = args.sheet_um / 1000.0
    turns, r, th, E = strain_map(args.reference, t_mm, args.ratio)
    ratio_ff = fold_flat_ratio(args.ratio, args.reference)

    print(f"Reference state: {args.reference}"
          + ("  (stress-free when wound -- the defensible one)"
             if args.reference == 'wound'
             else "  (stress-free flat -- reproduces the earlier 8x figure)"))
    print(f"Crush {args.ratio:.0f}:1, sheet {args.sheet_um:.0f} um, "
          f"failure strain {100*args.failure_strain:.2f} % (assumed)\n")
    na = neutral_angle_deg(args.ratio)
    print(f"  fold / flat strain ratio = {ratio_ff:.2f}x  "
          f"-- independent of radius and of thickness")
    print(f"  neutral angle = {na:.2f} deg from the fold axis, i.e. pristine "
          f"sectors at\n  {na:.0f}, {180-na:.0f}, {180+na:.0f}, {360-na:.0f} "
          f"deg -- where the crush leaves the sheet EXACTLY as it")
    print(f"  was wound, so it is neither cracked nor unbent. Scale invariant:")
    print(f"  the same angle at every depth, which makes it invertible --")
    print(f"  measuring where the intact sectors lie measures the crush ratio,")
    print(f"  with no dependence on pitch, umbilicus, thickness or grid.\n")
    print(f"  {'turn':>5} {'radius':>8} {'fold 0/180':>11} {'flat 90/270':>12} "
          f"{'cracks?':>9}")
    print("  " + "-" * 50)
    for i in (0, 4, 19, 39, 59, len(turns) - 1):
        # at the VERTICES: min over theta is the neutral-angle zero, not the
        # flattened-axis value
        fold, flat = E[i][0], E[i][90]
        flag = ('fold only' if fold > args.failure_strain >= flat
                else 'everywhere' if flat > args.failure_strain else 'no')
        print(f"  {turns[i]:>5d} {r[i]:>7.2f}m {100*fold:>10.2f}% "
              f"{100*flat:>11.2f}% {flag:>9}")

    over = E > args.failure_strain
    frac = float(over.mean())
    if over.any():
        cols = np.where(over.any(axis=0))[0]          # columns ARE degrees
        # report the two fold sectors, not a single span across the whole disc
        w = len(cols) / 2.0
        print(f"\n  {100*frac:.0f} % of the sheet surface exceeds the assumed "
              f"failure strain,")
        print(f"  in two sectors of about {w:.0f} deg centred on 0 and 180 "
              f"deg, and worst\n  toward the core.")
    else:
        print(f"\n  nothing exceeds the assumed failure strain.")

    print(f"\n  The MAP is the result. The absolute percentages depend on the")
    print(f"  sheet thickness and on a failure strain for carbonized papyrus")
    print(f"  that is not established -- both are knobs. What is derived, and")
    print(f"  needs no calibration, is the {ratio_ff:.2f}x fold/flat contrast and the")
    print(f"  1/r gradient: cracking should concentrate at 0/180 deg and grow")
    print(f"  toward the umbilicus. Merging, by contrast, concentrates on the")
    print(f"  FLATTENED axis. Two pathologies, two angles, one geometry.")

    if args.csv:
        np.savetxt(args.csv, E, delimiter=',',
                   header='rows=turns 0..%d, cols=theta 0..359 deg, strain'
                          % (len(turns) - 1), comments='')
        print(f"\n[csv] {args.csv}")

    if args.plot:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.5))
        ax = axes[0]
        for i in (0, 19, 39, len(turns) - 1):
            ax.plot(th, 100 * E[i], label=f'turn {turns[i]}  (r={r[i]:.1f} mm)')
        ax.axhline(100 * args.failure_strain, color='r', ls='--', lw=1,
                   label='assumed failure strain')
        ax.set_xlabel('angle (deg, 0 and 180 are the folds)')
        ax.set_ylabel('surface bending strain (%)')
        ax.set_xticks([0, 90, 180, 270, 360])
        ax.set_title(f'Strain concentrates at the folds\n'
                     f'({ratio_ff:.2f}x contrast, {args.reference} reference)')
        ax.legend(fontsize=8)
        im = axes[1].imshow(100 * E, aspect='auto', origin='lower',
                            extent=[0, 360, 0, len(turns)], cmap='inferno')
        fig.colorbar(im, ax=axes[1], label='strain (%)')
        axes[1].set_xlabel('angle (deg)'); axes[1].set_ylabel('winding turn')
        axes[1].set_xticks([0, 90, 180, 270, 360])
        axes[1].set_title('Where the verso fibres should separate\n'
                          '(worst at the folds, worst toward the core)')
        fig.tight_layout(); fig.savefig(args.plot, dpi=150)
        print(f"[plot] {args.plot}")


if __name__ == '__main__':
    main()
