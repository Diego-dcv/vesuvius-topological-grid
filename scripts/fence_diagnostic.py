#!/usr/bin/env python3
"""
fence_diagnostic.py -- provenance for the two fence numbers of mode 13.

Two different runs produced two different widths, and a thread comment
conflated them; this script pins each to its definition so both are
reproducible.

  159.5 +- 0.8 mm  THE FITTER IN ISOLATION. The fence fitted over the TRUE
                   join positions of the twin -- winding known from the
                   kollesis table, arc position from the certified inversion.
                   Validates the fitting step alone, as an upper bound on
                   what any pipeline can achieve.

  165 mm           THE BLIND PIPELINE. Detector flags -> radius-based winding
                   assignment from the painting origin -> fence fit, no
                   ground truth anywhere. This is the operational number and
                   the one the kollesis_detector docstring and README record.

    python scripts/fence_diagnostic.py test

PASS: isolated fitter within 2 mm of the true 160 with residual < 2 mm.
"""

import sys
import numpy as np
import synthetic_scroll_twin as T


def true_join_arcs(m, g):
    p = g['pitch_um'] / 1000.0
    n_t = int(np.ceil(m['n_turns']))
    AB = [T.ellipse_axes_for_perimeter(2 * np.pi * (g['r0_mm'] + (k + 0.5) * p),
                                       g['ratio']) for k in range(n_t)]
    TAB = [T.ellipse_arc_table(a, b) for a, b in AB]
    CUM = np.concatenate([[0], np.cumsum([tab[2] for tab in TAB])])
    S = []
    for r_k, th_k in zip(m['kollesis']['r_mm'], m['kollesis']['theta_deg']):
        k = int(round((float(r_k) - g['r0_mm']) / p - 0.5))
        a, b = AB[k]
        tt, ff, per = TAB[k]
        te = (np.arctan2(a * np.sin(np.radians(float(th_k))),
                         b * np.cos(np.radians(float(th_k)))) % (2 * np.pi))
        S.append(CUM[k] + np.interp(te, tt, ff) * per)
    return np.array(sorted(S))


def fit_fence(S, w_lo=120.0, w_hi=201.0):
    best = None
    for W in np.arange(w_lo, w_hi, 0.5):
        for o in np.arange(0.0, W, 2.0):
            r = np.abs(((S - o + W / 2) % W) - W / 2)
            c = r.mean()
            if best is None or c < best[0]:
                best = (c, W, o)
    return best  # (mean residual mm, width mm, offset mm)


def acceptance_test(verbose=True):
    oldG = dict(T.G)
    try:
        T.G['pitch_um'] = 300.0
        T.G['sheet_um'] = 150.0
        t, m = T.build_twin(20, seed=0)
        S = true_join_arcs(m, T.G)
        res, W, off = fit_fence(S)
        gaps = np.diff(S)
        ok = abs(W - T.G['kollesis_mm']) <= 2.0 and res < 2.0
        if verbose:
            print("=" * 70)
            print("FENCE DIAGNOSTIC -- the fitter in isolation "
                  "(true joins, known windings)")
            print("=" * 70)
            print(f"true join arcs (mm): "
                  + " ".join(f"{x:.0f}" for x in S))
            print(f"gaps: " + " ".join(f"{d:.0f}" for d in gaps))
            print(f"fitted fence: {W:.1f} mm (true "
                  f"{T.G['kollesis_mm']:.0f}), mean residual {res:.1f} mm")
            print(f"-> {'PASS' if ok else 'FAIL'} "
                  f"(|W-160| <= 2 mm and residual < 2 mm)")
            print()
            print("The blind-pipeline number (flags -> winding by radius -> "
                  "fit) is 165 mm; see kollesis_detector.py exam C.")
        return dict(width=W, residual=res, passed=bool(ok))
    finally:
        T.G.clear()
        T.G.update(oldG)


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'test'
    r = acceptance_test()
    sys.exit(0 if r['passed'] else 1)
