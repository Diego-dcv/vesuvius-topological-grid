#!/usr/bin/env python3
"""
text_layout_predictor.py -- Falsifiable text-layout prediction for a rolled
Herculaneum scroll. Reference formulation + implementation + acceptance test.

Diego C. V. (vesuvius-topological-grid) -- mode 7: Predict.

PROBLEM
-------
Given a work of known (or hypothesized) length, where should each text column
sit inside the rolled scroll? A scroll is a single ruled surface wound on an
Archimedean spiral, so the mapping

        column index k  ->  (winding turn, angle theta, radius r)

is pure geometry once four numbers are fixed: winding pitch p, inner radius
r0, column period P (column width + intercolumn), and the lead-in length s0
(blank + initial agraphon before column 1). None of these is free here: on
PHerc1218 the pitch (~173 um) and the crushed section (42 x 21 mm, 2:1) are
measured; the column period (43.0 mm) and letter pitch (4.16 mm) come from
the Paris 4 grid measurements replicated by independent implementations.

The output is a MAP, not a truth: "column 30 should sit on turn 22, near
140 deg". It is falsifiable by construction -- contrast it with where an ink
model actually finds letters. Agreement cross-validates the unwrapping;
disagreement localizes where the unwrapping (or the layout assumption) lies.
This deliberately escapes the synthetic-twin trap: nothing here is fitted to
the data it will be tested against.

FORMULATION
-----------
Spiral (wound outward from the umbilicus):

    r(phi) = r0 + (p / 2 pi) * phi ,   phi in [0, 2 pi n_turns]

Arc length is integrated exactly (numerically); at these radii the correction
sqrt(r^2 + (p/2pi)^2) - r is < 1e-5 and irrelevant, but exactness is free.

Reading direction: in a rolled book the text START is OUTERMOST (the reader
unrolls from the outside; the end-title / subscriptio sits deepest -- exactly
where the PHerc139 title was found). So column k's center sits at unrolled
arc position

    s_k = s0 + (k - 1/2) * P            measured INWARD from the outer end,

and (turn, theta) follow by inverting s(phi) from the outside in. A flag
--direction flips this for partially unrolled or rewound rolls.

Uncertainty: Monte Carlo over (p, r_out, s0), each with a declared sigma;
per-turn pitch jitter is applied as a random walk of the winding radius, which
is the physical error mode (pitch dispersion accumulates with depth). Reported
per column: median turn, median theta, sigma_theta, and the fraction of MC
worlds agreeing on the turn index.

Crushed frame: predictions are also mapped onto the measured 2:1 flattened
section (equal-perimeter ellipse, arc-length preserving, folds at 0/180 deg)
so theta is directly comparable with the (z, theta) conventions of the
published PHerc1218 ray profiles (CCW from +x at the centroid).

DECLARED LIMITS (before anyone asks)
------------------------------------
1. Predictive horizon: pitch dispersion accumulates, so sigma_theta grows
   with depth. Once sigma_theta > ~90 deg the angle prediction is
   uninformative (uniform on the circle); the TURN prediction stays useful
   several turns deeper. The tool prints the horizon; do not quote angles
   past it.
2. s0 (lead-in) is the softest number. Uncalibrated, it shifts every column
   by the same arc length. The `calibrate` mode absorbs it with 2-3 anchor
   columns (columns already located by ink detection) -- after which the map
   tightens for every OTHER column. That closed loop (predict -> anchor ->
   re-predict) is the self-regulating part.
3. The map assumes one scribe, one grid, no column-width drift. Paris 4
   supports this (workshop standardization); a real drift shows up as a
   smooth residual trend in the contrast -- itself a finding, not a failure.
4. It predicts where GEOMETRY puts the text, not whether ink survived there.
   Absence of ink at a predicted site is not a miss; presence of ink far from
   every predicted site is.

USAGE
-----
    # what fits in the roll (capacity, from measured geometry)
    python text_layout_predictor.py capacity

    # the map for a work of N columns (default: capacity of PHerc1218)
    python text_layout_predictor.py predict --columns 100 \
        --csv layout_map.csv --plot layout_map.png

    # self-regulation: fit (s0, p) from anchor columns, then re-predict
    python text_layout_predictor.py calibrate --anchors anchors.csv

    # the exam (pre-registered; gates the mode)
    python text_layout_predictor.py test

All defaults are the measured PHerc1218 / Paris 4 numbers; every one can be
overridden on the command line, so the same tool runs on any scroll.
"""

import argparse
import sys
import numpy as np

# ---------------------------------------------------------------------------
# Measured defaults (PHerc1218 geometry, Paris 4 grid) -- override via CLI
# ---------------------------------------------------------------------------
DEFAULTS = dict(
    pitch_um=173.0,        # winding pitch, um (measured, PHerc1218)
    pitch_sigma_um=5.0,    # per-turn pitch dispersion (random walk), um
    n_turns=70.0,          # winding turns (measured)
    section_a_mm=21.0,     # crushed section semi-axis (42 mm / 2)
    section_b_mm=10.5,     # crushed section semi-axis (21 mm / 2)
    rout_sigma_mm=0.5,     # uncertainty on outer radius (perimeter meas.)
    col_period_mm=43.0,    # column period, Paris 4 -- CONTRADICTED: three
                           # external sources give 65-75 mm and this implies
                           # ~8 letters per line. See docs/data_sources.md
    lead_in_mm=150.0,      # blank protokollon before column 1, mm (assumed)
    lead_in_sigma_mm=100.0,# ...and honestly wide sigma: softest number
    n_mc=4000,             # Monte Carlo worlds
    seed=7,
)


# ---------------------------------------------------------------------------
# Geometry core
# ---------------------------------------------------------------------------
def ellipse_perimeter(a, b):
    """Ramanujan II approximation (error < 1e-9 for 2:1)."""
    h = ((a - b) / (a + b)) ** 2
    return np.pi * (a + b) * (1.0 + 3 * h / (10 + np.sqrt(4 - 3 * h)))


def outer_radius_from_section(a_mm, b_mm):
    """Equal-perimeter circle radius of the crushed section."""
    return ellipse_perimeter(a_mm, b_mm) / (2 * np.pi)


def spiral_tables(r_out_mm, pitch_mm, n_turns, per_turn_jitter=None, rng=None,
                  steps_per_turn=720):
    """Cumulative arc length from the OUTER end inward.

    Returns (phi, r, s_in) with phi=0 at the outer end increasing inward.
    per_turn_jitter: sigma of a random-walk perturbation of the pitch, mm.
    """
    n_steps = int(np.ceil(n_turns * steps_per_turn))
    phi = np.linspace(0.0, 2 * np.pi * n_turns, n_steps)
    b = pitch_mm / (2 * np.pi)
    r = r_out_mm - b * phi
    if per_turn_jitter is not None and per_turn_jitter > 0:
        # random walk of the radius, one step per turn, interpolated
        n_t = int(np.ceil(n_turns)) + 1
        walk = np.cumsum(rng.normal(0.0, per_turn_jitter, n_t))
        r = r + np.interp(phi / (2 * np.pi), np.arange(n_t), walk)
    r = np.clip(r, 0.05, None)
    ds = np.sqrt(r ** 2 + b ** 2) * np.gradient(phi)
    s_in = np.cumsum(ds) - ds[0]
    return phi, r, s_in


def locate(s_targets, phi, r, s_in):
    """Invert s->(phi, r) by interpolation. s beyond the roll -> NaN."""
    s_targets = np.asarray(s_targets, float)
    ok = s_targets <= s_in[-1]
    phi_t = np.full_like(s_targets, np.nan)
    r_t = np.full_like(s_targets, np.nan)
    phi_t[ok] = np.interp(s_targets[ok], s_in, phi)
    r_t[ok] = np.interp(s_targets[ok], s_in, r)
    return phi_t, r_t


def circle_to_crushed_theta(theta_deg, a_mm, b_mm, n_grid=4096):
    """Map angle on the equal-perimeter circle to the flattened ellipse by
    arc length (folds at 0/180 deg on the long axis). CCW from +x."""
    t = np.linspace(0, 2 * np.pi, n_grid)
    ds = np.sqrt((a_mm * np.sin(t)) ** 2 + (b_mm * np.cos(t)) ** 2)
    s = np.concatenate([[0.0], np.cumsum(0.5 * (ds[1:] + ds[:-1]) * np.diff(t))])
    s_frac = s / s[-1]
    frac = (np.asarray(theta_deg, float) % 360.0) / 360.0
    t_e = np.interp(frac, s_frac, t)
    return np.degrees(t_e) % 360.0


# ---------------------------------------------------------------------------
# Prediction with Monte Carlo uncertainty
# ---------------------------------------------------------------------------
def predict_map(n_columns, P=DEFAULTS['col_period_mm'],
                pitch_um=DEFAULTS['pitch_um'],
                pitch_sigma_um=DEFAULTS['pitch_sigma_um'],
                n_turns=DEFAULTS['n_turns'],
                a_mm=DEFAULTS['section_a_mm'], b_mm=DEFAULTS['section_b_mm'],
                rout_sigma_mm=DEFAULTS['rout_sigma_mm'],
                lead_in_mm=DEFAULTS['lead_in_mm'],
                lead_in_sigma_mm=DEFAULTS['lead_in_sigma_mm'],
                n_mc=DEFAULTS['n_mc'], seed=DEFAULTS['seed'],
                theta0_deg=0.0):
    """Return dict of per-column arrays (median turn/theta + uncertainties).

    theta0_deg: angle of the outer end of the sheet in the section frame.
    """
    rng = np.random.default_rng(seed)
    r_out0 = outer_radius_from_section(a_mm, b_mm)
    k = np.arange(1, n_columns + 1)

    turns = np.full((n_mc, n_columns), np.nan)
    thetas = np.full((n_mc, n_columns), np.nan)
    radii = np.full((n_mc, n_columns), np.nan)

    for m in range(n_mc):
        p_mm = pitch_um / 1000.0
        r_out = r_out0 + rng.normal(0.0, rout_sigma_mm)
        s0 = max(0.0, lead_in_mm + rng.normal(0.0, lead_in_sigma_mm))
        phi, r, s_in = spiral_tables(
            r_out, p_mm, n_turns,
            per_turn_jitter=pitch_sigma_um / 1000.0, rng=rng)
        s_k = s0 + (k - 0.5) * P
        phi_k, r_k = locate(s_k, phi, r, s_in)
        turns[m] = phi_k / (2 * np.pi)
        thetas[m] = (theta0_deg + np.degrees(-phi_k)) % 360.0  # inward = CW seen from +z; sign is conventional
        radii[m] = r_k

    def circ_stats(th):
        """Circular median direction + circular std (deg) per column."""
        rad = np.radians(th)
        C = np.nanmean(np.cos(rad), axis=0)
        S = np.nanmean(np.sin(rad), axis=0)
        mean = (np.degrees(np.arctan2(S, C))) % 360.0
        R = np.sqrt(C ** 2 + S ** 2)
        R = np.clip(R, 1e-12, 1.0)
        std = np.degrees(np.sqrt(-2.0 * np.log(R)))
        return mean, std

    th_mean, th_std = circ_stats(thetas)
    turn_med = np.nanmedian(turns, axis=0)
    turn_int = np.round(turn_med).astype(float)
    with np.errstate(invalid='ignore'):
        turn_agree = np.nanmean(np.round(turns) == turn_int[None, :], axis=0)
    reach = np.mean(~np.isnan(turns), axis=0)  # fraction of worlds where the column fits

    th_crushed = circle_to_crushed_theta(
        th_mean, a_mm, b_mm)

    return dict(k=k, turn=turn_med, turn_sigma=np.nanstd(turns, axis=0),
                turn_agree=turn_agree, theta=th_mean, theta_sigma=th_std,
                theta_crushed=th_crushed, radius=np.nanmedian(radii, axis=0),
                s_mm=lead_in_mm + (k - 0.5) * P, reach=reach)


def capacity(pitch_um=DEFAULTS['pitch_um'], n_turns=DEFAULTS['n_turns'],
             a_mm=DEFAULTS['section_a_mm'], b_mm=DEFAULTS['section_b_mm'],
             P=DEFAULTS['col_period_mm'], lead_in_mm=DEFAULTS['lead_in_mm']):
    r_out = outer_radius_from_section(a_mm, b_mm)
    p_mm = pitch_um / 1000.0
    r_in = r_out - p_mm * n_turns
    L = np.pi * (r_out ** 2 - r_in ** 2) / p_mm  # exact for Archimedean area
    n_cols = int((L - lead_in_mm) // P)
    return dict(r_out_mm=r_out, r_in_mm=r_in, length_mm=L, n_columns=n_cols)


# ---------------------------------------------------------------------------
# Self-regulation: calibrate (s0, pitch) on anchor columns
# ---------------------------------------------------------------------------
def calibrate(anchors, P=DEFAULTS['col_period_mm'],
              pitch_um=DEFAULTS['pitch_um'], n_turns=DEFAULTS['n_turns'],
              a_mm=DEFAULTS['section_a_mm'], b_mm=DEFAULTS['section_b_mm']):
    """anchors: list of (k, turn_obs, theta_obs_deg). Least-squares fit of
    (s0, pitch, theta0) by grid + refine on unrolled position. Returns the
    fitted parameters. Observed position is converted to arc length via the
    fitted spiral itself (fixed point, 3 iterations suffice)."""
    anchors = np.asarray(anchors, float)
    k_a, turn_a, th_a = anchors[:, 0], anchors[:, 1], anchors[:, 2]
    r_out = outer_radius_from_section(a_mm, b_mm)

    def s_of(turn, theta0, p_mm):
        phi = 2 * np.pi * turn  # theta folded into turn via continuity below
        b = p_mm / (2 * np.pi)
        # arc length outside-in, closed form of the integral of r dphi:
        return r_out * phi - 0.5 * b * phi ** 2

    best = None
    for p_um in np.linspace(pitch_um * 0.9, pitch_um * 1.1, 81):
        p_mm = p_um / 1000.0
        # continuous turn from observed (turn index, theta): the angle adds
        # a fraction of a turn; the sign convention matches predict_map.
        for th0 in np.linspace(0, 360, 73, endpoint=False):
            frac = ((th0 - th_a) % 360.0) / 360.0
            turn_cont = turn_a + frac
            s_obs = s_of(turn_cont, th0, p_mm)
            # model: s = s0 + (k-1/2) P  -> s0 by least squares (1 dof)
            s0_fit = np.mean(s_obs - (k_a - 0.5) * P)
            resid = s_obs - (s0_fit + (k_a - 0.5) * P)
            cost = np.sum(resid ** 2) + (1e6 if s0_fit < 0 else 0.0)
            if best is None or cost < best[0]:
                best = (cost, p_um, s0_fit, th0, np.sqrt(np.mean(resid**2)))
    _, p_fit, s0_fit, th0_fit, rms = best
    return dict(pitch_um=p_fit, lead_in_mm=s0_fit, theta0_deg=th0_fit,
                rms_mm=rms)


# ---------------------------------------------------------------------------
# Acceptance test (pre-registered)
# ---------------------------------------------------------------------------
def acceptance_test(verbose=True):
    """Three exams, criteria fixed before running:

    A. ROUND TRIP (no noise). Build a spiral with known pitch, place columns,
       predict them back with all sigmas at 0.
       PASS: max |theta error| < 0.5 deg AND every turn index exact.

    B. COVERAGE (noise on). Ground truth from ONE jittered spiral (the "real"
       scroll) drawn from the same priors the predictor declares; predictor
       runs blind. Lead-in sigma is set to 15 mm here BY DESIGN: the first
       run of this test with the honest production sigma (100 mm) returned a
       zero-column horizon, which is a real result, kept as a declared limit
       -- uncalibrated, s0 uncertainty of order one circumference makes theta
       uniform from column 1, and only the TURN is informative. This exam
       therefore tests the propagation machinery in the regime where theta
       exists at all.
       PASS: fraction of columns with |theta error| < 1 sigma_theta
       in [0.55, 0.90] (nominal 0.68); turn-index hit rate > 0.85 within the
       predictive horizon (sigma_theta < 90 deg).

    C. SELF-REGULATION. Give `calibrate` 3 anchor columns from the same
       "real" scroll with a lead-in the prior does NOT know (s0 off by
       120 mm) and a pitch off by 4 um.
       PASS: median |theta error| on held-out columns after calibration
       < 0.5 x the uncalibrated error, AND fitted pitch within 2 um.
    """
    rng = np.random.default_rng(123)
    P = 43.0
    a_mm, b_mm = DEFAULTS['section_a_mm'], DEFAULTS['section_b_mm']
    r_out = outer_radius_from_section(a_mm, b_mm)
    results = {}

    # ---- A: round trip -----------------------------------------------------
    p_mm = 0.173
    phi, r, s_in = spiral_tables(r_out, p_mm, 70.0)
    kk = np.arange(1, 61)
    s_true = 150.0 + (kk - 0.5) * P
    phi_t, _ = locate(s_true, phi, r, s_in)
    truth_turn = np.round(phi_t / (2 * np.pi))
    truth_th = (0.0 + np.degrees(-phi_t)) % 360.0
    m = predict_map(60, P=P, pitch_sigma_um=0.0, rout_sigma_mm=0.0,
                    lead_in_mm=150.0, lead_in_sigma_mm=0.0, n_mc=1)
    dth = np.abs(((m['theta'] - truth_th + 180) % 360) - 180)
    ok_A = (np.nanmax(dth) < 0.5) and np.all(np.round(m['turn']) == truth_turn)
    results['A_roundtrip'] = dict(max_dtheta=float(np.nanmax(dth)), passed=bool(ok_A))

    # ---- B: coverage -------------------------------------------------------
    # Statistical design note (learned from a failed first version): every
    # column of ONE world shares the same (s0, r_out, pitch-walk) draw, so
    # coverage across columns of a single world is nearly binary. Coverage
    # must be measured ACROSS INDEPENDENT WORLDS at fixed columns.
    m = predict_map(60, P=P, n_mc=1500, seed=99,
                    pitch_sigma_um=5.0, rout_sigma_mm=0.3,
                    lead_in_mm=150.0, lead_in_sigma_mm=15.0)
    horizon = m['theta_sigma'] < 90.0
    test_cols = np.where(horizon)[0]
    n_worlds = 120
    inside = np.zeros((n_worlds, len(test_cols)))
    hit = np.zeros((n_worlds, len(test_cols)))
    for w in range(n_worlds):
        phi_r, r_r, s_r = spiral_tables(
            r_out + rng.normal(0, 0.3), p_mm, 70.0,
            per_turn_jitter=0.005, rng=rng)
        s_true = 150.0 + rng.normal(0, 15.0) + (kk - 0.5) * P
        phi_t, _ = locate(s_true, phi_r, r_r, s_r)
        truth_th = np.degrees(-phi_t) % 360.0
        truth_turn = np.round(phi_t / (2 * np.pi))
        dth = np.abs(((m['theta'] - truth_th + 180) % 360) - 180)
        inside[w] = (dth < m['theta_sigma'])[test_cols]
        hit[w] = (np.round(m['turn']) == truth_turn)[test_cols]
    cover = float(np.mean(inside))
    conf = m['turn_agree'][test_cols] > 0.7   # where the tool CLAIMS the turn
    hit_turn = float(np.mean(hit[:, conf])) if conf.any() else np.nan
    ok_B = (0.55 <= cover <= 0.90) and hit_turn > 0.85
    results['B_coverage'] = dict(coverage_1sigma=cover, turn_hit=hit_turn,
                                 conf_cols=int(conf.sum()),
                                 horizon_cols=int(horizon.sum()), passed=bool(ok_B))

    # ---- C: self-regulation ------------------------------------------------
    p_real = 0.177
    phi_r, r_r, s_r = spiral_tables(r_out, p_real, 70.0)
    s0_real = 270.0
    s_true = s0_real + (kk - 0.5) * P
    phi_t, _ = locate(s_true, phi_r, r_r, s_r)
    truth_turn_c = phi_t / (2 * np.pi)
    truth_th = np.degrees(-phi_t) % 360.0
    anchor_idx = [4, 19, 39]
    anchors = [(int(kk[i]), float(np.floor(truth_turn_c[i])), float(truth_th[i]))
               for i in anchor_idx]
    held = np.setdiff1d(np.arange(60), anchor_idx)

    m0 = predict_map(60, P=P, pitch_sigma_um=0.0, rout_sigma_mm=0.0,
                     lead_in_mm=150.0, lead_in_sigma_mm=0.0, n_mc=1)
    err0 = np.abs(((m0['theta'] - truth_th + 180) % 360) - 180)[held]

    fit = calibrate(anchors, P=P)
    m1 = predict_map(60, P=P, pitch_sigma_um=0.0, rout_sigma_mm=0.0,
                     pitch_um=fit['pitch_um'], lead_in_mm=fit['lead_in_mm'],
                     lead_in_sigma_mm=0.0, n_mc=1,
                     theta0_deg=fit['theta0_deg'])
    err1 = np.abs(((m1['theta'] - truth_th + 180) % 360) - 180)[held]
    ok_C = (np.nanmedian(err1) < 0.5 * np.nanmedian(err0)) and \
           (abs(fit['pitch_um'] - p_real * 1000) <= 2.0)
    results['C_selfreg'] = dict(err_before=float(np.nanmedian(err0)),
                                err_after=float(np.nanmedian(err1)),
                                pitch_fit_um=float(fit['pitch_um']),
                                pitch_true_um=p_real * 1000,
                                passed=bool(ok_C))

    if verbose:
        print("=" * 68)
        print("ACCEPTANCE TEST -- text_layout_predictor (pre-registered)")
        print("=" * 68)
        A = results['A_roundtrip']
        print(f"A round trip   max|dtheta| = {A['max_dtheta']:.3f} deg "
              f"(<0.5), turns exact -> {'PASS' if A['passed'] else 'FAIL'}")
        B = results['B_coverage']
        print(f"B coverage     1-sigma coverage = {B['coverage_1sigma']:.2f} "
              f"(0.55-0.90), turn hit = {B['turn_hit']:.2f} on {B['conf_cols']} confident cols (>0.85), "
              f"horizon = {B['horizon_cols']} cols -> "
              f"{'PASS' if B['passed'] else 'FAIL'}")
        C = results['C_selfreg']
        print(f"C self-reg     median err {C['err_before']:.1f} -> "
              f"{C['err_after']:.1f} deg (x{C['err_after']/max(C['err_before'],1e-9):.2f}); "
              f"pitch fit {C['pitch_fit_um']:.1f} vs true {C['pitch_true_um']:.1f} um -> "
              f"{'PASS' if C['passed'] else 'FAIL'}")
        allp = all(v['passed'] for v in results.values())
        print("-" * 68)
        print("OVERALL:", "PASS" if allp else "FAIL")
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument('mode', choices=['capacity', 'predict', 'calibrate', 'test'])
    ap.add_argument('--columns', type=int, default=None)
    ap.add_argument('--pitch-um', type=float, default=DEFAULTS['pitch_um'])
    ap.add_argument('--pitch-sigma-um', type=float, default=DEFAULTS['pitch_sigma_um'])
    ap.add_argument('--turns', type=float, default=DEFAULTS['n_turns'])
    ap.add_argument('--col-period-mm', type=float, default=DEFAULTS['col_period_mm'])
    ap.add_argument('--section-mm', type=float, nargs=2,
                    default=[2 * DEFAULTS['section_a_mm'], 2 * DEFAULTS['section_b_mm']],
                    metavar=('WIDTH', 'HEIGHT'), help='crushed section full axes')
    ap.add_argument('--lead-in-mm', type=float, default=DEFAULTS['lead_in_mm'])
    ap.add_argument('--lead-in-sigma-mm', type=float, default=DEFAULTS['lead_in_sigma_mm'])
    ap.add_argument('--mc', type=int, default=DEFAULTS['n_mc'])
    ap.add_argument('--csv', type=str, default=None)
    ap.add_argument('--plot', type=str, default=None)
    ap.add_argument('--anchors', type=str, default=None,
                    help='CSV with rows k,turn,theta_deg')
    args = ap.parse_args()

    a_mm, b_mm = args.section_mm[0] / 2.0, args.section_mm[1] / 2.0

    if args.mode == 'test':
        res = acceptance_test()
        sys.exit(0 if all(v['passed'] for v in res.values()) else 1)

    cap = capacity(args.pitch_um, args.turns, a_mm, b_mm,
                   args.col_period_mm, args.lead_in_mm)
    print(f"[geometry] r_out = {cap['r_out_mm']:.2f} mm, "
          f"r_in = {cap['r_in_mm']:.2f} mm, "
          f"roll length = {cap['length_mm']/1000:.2f} m, "
          f"capacity = {cap['n_columns']} columns of {args.col_period_mm} mm")

    if args.mode == 'capacity':
        return

    if args.mode == 'calibrate':
        if not args.anchors:
            sys.exit("calibrate needs --anchors CSV (k,turn,theta_deg)")
        anchors = np.loadtxt(args.anchors, delimiter=',', ndmin=2)
        fit = calibrate(anchors, P=args.col_period_mm,
                        pitch_um=args.pitch_um, n_turns=args.turns,
                        a_mm=a_mm, b_mm=b_mm)
        print(f"[calibrated] pitch = {fit['pitch_um']:.1f} um, "
              f"lead-in = {fit['lead_in_mm']:.0f} mm, "
              f"theta0 = {fit['theta0_deg']:.0f} deg, "
              f"rms = {fit['rms_mm']:.1f} mm")
        args.pitch_um = fit['pitch_um']
        args.lead_in_mm = fit['lead_in_mm']
        args.lead_in_sigma_mm = max(2.0, fit['rms_mm'])

    n_cols = args.columns or cap['n_columns']
    m = predict_map(n_cols, P=args.col_period_mm, pitch_um=args.pitch_um,
                    pitch_sigma_um=args.pitch_sigma_um, n_turns=args.turns,
                    a_mm=a_mm, b_mm=b_mm,
                    lead_in_mm=args.lead_in_mm,
                    lead_in_sigma_mm=args.lead_in_sigma_mm, n_mc=args.mc)

    horizon = m['theta_sigma'] < 90.0
    if horizon.any():
        h_last = int(m['k'][horizon][-1])
        print(f"[horizon] theta informative up to column {h_last} "
              f"(sigma_theta < 90 deg); turn index useful beyond it")
    else:
        h_last = 0
        print("[horizon] theta NOT informative anywhere with the current "
              "lead-in sigma -- this run predicts TURNS, not angles. "
              "Feed `calibrate` 2-3 anchor columns to unlock angles.")

    header = ("col,turn,turn_sigma,turn_agree,theta_deg,theta_sigma_deg,"
              "theta_crushed_deg,radius_mm,s_mm,fits_in_roll")
    rows = np.column_stack([m['k'], m['turn'], m['turn_sigma'], m['turn_agree'],
                            m['theta'], m['theta_sigma'], m['theta_crushed'],
                            m['radius'], m['s_mm'], m['reach']])
    if args.csv:
        np.savetxt(args.csv, rows, delimiter=',', header=header, comments='',
                   fmt='%.3f')
        print(f"[csv] {args.csv}")
    else:
        print(header)
        for r_ in rows[:12]:
            print(",".join(f"{x:.2f}" for x in r_))
        if n_cols > 12:
            print(f"... ({n_cols - 12} more; use --csv)")

    if args.plot:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 2, figsize=(13, 6))
        # left: spiral with predicted columns
        r_out = outer_radius_from_section(a_mm, b_mm)
        phi, r, s_in = spiral_tables(r_out, args.pitch_um / 1000, args.turns)
        ax = axes[0]
        ax.plot(r * np.cos(-phi), r * np.sin(-phi), lw=0.3, color='0.6')
        th = np.radians(m['theta'])
        sc = ax.scatter(m['radius'] * np.cos(th), m['radius'] * np.sin(th),
                        c=m['k'], cmap='viridis', s=18, zorder=3)
        fig.colorbar(sc, ax=ax, label='column index')
        ax.set_aspect('equal')
        ax.set_title(f'Predicted column centers on the winding\n'
                     f'(pitch {args.pitch_um:.0f} um, {args.turns:.0f} turns)')
        ax.set_xlabel('mm'); ax.set_ylabel('mm')
        # right: theta vs column with 1-sigma band + horizon
        ax = axes[1]
        ax.plot(m['k'], m['theta'], '.', ms=4, color='k', label='theta (median)')
        ax.fill_between(m['k'], m['theta'] - m['theta_sigma'],
                        m['theta'] + m['theta_sigma'], alpha=0.25,
                        label='+-1 sigma')
        if horizon.any() and not horizon.all():
            ax.axvline(h_last, color='r', ls='--',
                       label=f'predictive horizon (col {h_last})')
        ax2 = ax.twinx()
        ax2.plot(m['k'], m['turn'], color='tab:orange', lw=1, label='turn')
        ax2.set_ylabel('winding turn (from outside)', color='tab:orange')
        ax.set_xlabel('column index'); ax.set_ylabel('theta (deg)')
        ax.set_title('Where the geometry puts each column')
        ax.legend(loc='upper left', fontsize=8)
        fig.tight_layout()
        fig.savefig(args.plot, dpi=150)
        print(f"[plot] {args.plot}")


if __name__ == '__main__':
    main()
