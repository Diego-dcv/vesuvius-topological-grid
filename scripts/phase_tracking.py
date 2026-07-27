#!/usr/bin/env python3
"""
phase_tracking.py -- Period-phase search and phase-glitch tracking.

Diego C. V. (vesuvius-topological-grid) -- mode 10.

WHAT THIS CLOSES
----------------
`epoch_folding_prototype.py` states its own limit in its docstring: line
centres are found on a clean image, and "on real raw data the algorithm must
SEARCH for the period and phase of the fold by maximizing the contrast of the
folded profile (period-phase search, as in pulsars), not assume them known.
That search is the natural next step."

This is that step. Two things follow from it, and the second was not obvious:

1. The search itself. Classic epoch folding: for each trial period, fold the
   profile and score it with the chi-square of the folded bins against a flat
   profile. The true period maximizes it. No peak-finding on a clean image,
   no assumed period, and it degrades gracefully with noise instead of
   collapsing.

2. Phase TRACKING, which the prototype threw away. `fold_lines` already walks
   the image in windows and computes line centres per window -- then averages
   every strip together, discarding where each window sat. That per-window
   phase is a signal in its own right: in an intact surface it drifts slowly
   and smoothly; a discontinuity in the underlying surface displaces the text
   and steps it. A phase glitch, in the pulsar-timing sense.

WHY A GLITCH IS NOT A DRIFT
---------------------------
The distinction is the whole tool, and it is the failure mode a naive version
would get wrong. Writing that sits slightly skew to the roll axis produces a
phase that drifts LINEARLY across the render -- large in total, and entirely
innocent. A surface discontinuity produces a STEP. Exam C exists to enforce
this: a pure linear drift, however steep, must raise zero glitches.

WHICH AXIS, AND WHAT IT MEANS
-----------------------------
    --axis lines    period along the roll axis (line spacing, ~2.79 mm)
    --axis columns  period along the unrolled arc (column period, ~43 mm)

For detecting a jump to a neighbouring winding, `columns` is the informative
one. A skip displaces the text along the arc by roughly one circumference,
which is not a multiple of the column period, so the column lattice steps.
The line lattice need NOT step: the scribe wrote on a flat sheet, so lines sit
at the same height on every winding, and only skew makes them move. Do not
read a clean line phase as evidence of an intact surface.

Practical note on sampling: a render carrying only ~10 column periods gives
the search very little to work with along that axis. With few periods,
locating the blank intercolumn bands directly and checking the sequence of
gap-to-gap distances is the more robust test, and needs none of this code.
This tool earns its place where the periods are many and the signal is buried
-- which is the raw-intensity case the prototype was always aimed at.

USAGE
-----
    python phase_tracking.py search IMAGE.png --width-mm 129 --axis lines
    python phase_tracking.py track IMAGE.png --width-mm 129 --axis lines \
        --csv phase.csv --plot phase.png
    python phase_tracking.py test
"""

import argparse
import sys
import numpy as np

BANDS_MM = {'lines': (1.0, 8.0), 'columns': (20.0, 90.0)}


# ---------------------------------------------------------------------------
# Period-phase search (epoch folding)
# ---------------------------------------------------------------------------
def fold_chi2(x, coord, period, n_bins=16):
    """Epoch-folding statistic: chi-square of the folded profile against a
    flat one. This is the pulsar-timing test for periodicity, and it is what
    replaces assuming the period.

    x     : signal samples
    coord : position of each sample, same units as period
    """
    x = np.asarray(x, float)
    var = x.var()
    if var <= 0:
        return 0.0
    ph = np.mod(coord / period, 1.0)
    idx = np.minimum((ph * n_bins).astype(int), n_bins - 1)
    total = 0.0
    mean = x.mean()
    for b in range(n_bins):
        m = idx == b
        n = int(m.sum())
        if n:
            total += n * (x[m].mean() - mean) ** 2
    return float(total / var)


def fold_phase(x, coord, period):
    """Phase of the fundamental, in [0, 1).

    Taken as the argument of the first Fourier harmonic rather than the peak
    of the folded profile: it is continuous, needs no binning, and does not
    jitter by a bin width when the profile is noisy.
    """
    x = np.asarray(x, float)
    x = x - x.mean()
    z = np.sum(x * np.exp(-2j * np.pi * coord / period))
    return float((np.angle(z) / (2 * np.pi)) % 1.0), float(np.abs(z))


def period_search(profile, pixel_mm, p_min, p_max, n_trials=1200, n_bins=16,
                  reject_harmonics=True):
    """Scan trial periods and return the chi-square maximum.

    Harmonic rejection: epoch folding scores a true period P and its
    multiples 2P, 3P... almost as highly, because a profile folded at 2P
    simply shows the pattern twice. Left alone, the search can settle on a
    multiple and report a period that is really two lines, or two columns.
    When the best candidate has a sub-multiple within the band scoring above
    `harmonic_keep` of its chi-square, the sub-multiple is preferred -- the
    fundamental, not its echo.
    """
    x = np.asarray(profile, float)
    coord = np.arange(x.size) * pixel_mm
    periods = np.linspace(p_min, p_max, n_trials)
    chi2 = np.array([fold_chi2(x, coord, p, n_bins) for p in periods])
    best = int(np.argmax(chi2))
    p_best, c_best = float(periods[best]), float(chi2[best])

    if reject_harmonics:
        harmonic_keep = 0.60
        for k in (5, 4, 3, 2):
            p_sub = p_best / k
            if p_sub < p_min:
                continue
            j = int(np.argmin(np.abs(periods - p_sub)))
            # take the local maximum near the sub-multiple, not one sample
            lo, hi = max(0, j - 6), min(len(periods), j + 7)
            jj = lo + int(np.argmax(chi2[lo:hi]))
            if chi2[jj] > harmonic_keep * c_best:
                p_best, c_best = float(periods[jj]), float(chi2[jj])
                break

    ph, amp = fold_phase(x, coord, p_best)
    return dict(period_mm=p_best, chi2=c_best, phase=ph, amplitude=amp,
                periods=periods, chi2_curve=chi2)


# ---------------------------------------------------------------------------
# Phase tracking and glitch detection
# ---------------------------------------------------------------------------
def axis_profile(img, axis):
    """lines -> period runs down the rows; columns -> across the columns."""
    return img.sum(axis=1) if axis == 'lines' else img.sum(axis=0)


def track_phase(img, pixel_mm, period_mm, axis='lines', win_mm=None,
                step_mm=None):
    """Phase of the lattice in each window along the OTHER axis.

    For `lines`, windows walk across the arc and the phase is measured down
    the rows; for `columns`, the reverse.

    Window sizing is in the WALKING direction and must not be derived from
    the lattice period, which runs along the perpendicular axis -- a first
    version tied it to 12 periods and, for line spacing on a narrow render,
    that came out wider than the whole image, so exactly one window fitted
    and no track existed to glitch. The window trades localization against
    the signal summed into each phase estimate; a twenty-fifth of the walking
    extent keeps both usable.
    """
    long_axis = 0 if axis == 'lines' else 1
    walk_axis = 1 - long_axis
    n_walk = img.shape[walk_axis]
    walk_extent_mm = n_walk * pixel_mm
    win_mm = win_mm or max(walk_extent_mm / 25.0, 6 * pixel_mm)
    step_mm = step_mm or win_mm / 3.0
    win = max(4, int(win_mm / pixel_mm))
    step = max(1, int(step_mm / pixel_mm))

    xs, phases, amps = [], [], []
    for a in range(0, max(1, n_walk - win), step):
        sl = [slice(None), slice(None)]
        sl[walk_axis] = slice(a, a + win)
        block = img[tuple(sl)]
        prof = block.sum(axis=walk_axis)
        coord = np.arange(prof.size) * pixel_mm
        ph, amp = fold_phase(prof, coord, period_mm)
        xs.append((a + win / 2) * pixel_mm)
        phases.append(ph)
        amps.append(amp)
    return np.array(xs), np.array(phases), np.array(amps)


def unwrap_phase(ph):
    """Phases are circular; a drift past 1.0 must not read as a step."""
    return np.unwrap(np.asarray(ph) * 2 * np.pi) / (2 * np.pi)


def find_glitches(x_mm, phase, n_sigma=4.0, min_step=0.15):
    """Steps in the phase track, after removing any smooth linear drift.

    A linear drift is what skew writing produces and is innocent, so it is
    fitted and subtracted before anything is called a glitch. The residual
    step is measured in units of the lattice period: `min_step` is a floor in
    those units, so a statistically clear but physically trivial wobble does
    not get reported.
    """
    u = unwrap_phase(phase)
    if u.size < 5:
        return [], u, np.zeros_like(u)
    A = np.vstack([x_mm, np.ones_like(x_mm)]).T
    coef, *_ = np.linalg.lstsq(A, u, rcond=None)
    resid = u - A @ coef
    d = np.diff(resid)
    sd = 1.4826 * np.median(np.abs(d - np.median(d))) + 1e-12  # robust
    out = []
    for i, di in enumerate(d):
        if abs(di) > max(n_sigma * sd, min_step):
            out.append(dict(x_mm=float(0.5 * (x_mm[i] + x_mm[i + 1])),
                            step=float(di),
                            sigma=float(abs(di) / sd)))
    return out, u, resid


# ---------------------------------------------------------------------------
# Acceptance test (pre-registered)
# ---------------------------------------------------------------------------
def acceptance_test(verbose=True):
    """Four exams, criteria fixed before running.

    A. PERIOD RECOVERY UNDER NOISE. A sinusoidal lattice of known period
       buried in noise at SNR 0.3, i.e. where peak-finding on the raw profile
       is hopeless. This is the exam the prototype could not have passed:
       its centres were found on a clean image.
       PASS: recovered period within 2 % of truth.

    B. GLITCH LOCALIZATION. A lattice whose phase steps by 0.4 of a period at
       a known position.
       PASS: exactly one glitch, within one window of the true position, and
       a clean control raises none.

    C. DRIFT IS NOT A GLITCH. A lattice whose phase drifts linearly by three
       whole periods across the image -- what skew writing does, and the most
       likely false positive there is.
       PASS: zero glitches. If this fails the tool reports skew as damage.

    D. HARMONIC REJECTION. Alternate lines modulated in intensity, so that
       2P is a genuine period of the signal and epoch folding scores it
       ABOVE the fundamental -- the case where the search reports two lines
       as one. A first version of this exam used a plain second harmonic and
       was vacuous: the search returned the right answer with the rejection
       switched off, so it could not fail. It now checks both.
       PASS: the fundamental is recovered with rejection on, AND the search
       demonstrably picks the double with it off. The second half is what
       makes this an exam rather than a formality.
    """
    rng = np.random.default_rng(11)
    px = 0.05          # mm/px
    P = 2.79           # mm, the line spacing
    H, W = 900, 700
    y = np.arange(H) * px
    res = {}

    def lattice(phase_of_x, amp=1.0, harmonic=0.0):
        img = np.empty((H, W))
        for j in range(W):
            ph = phase_of_x(j)
            s = amp * np.cos(2 * np.pi * (y / P - ph))
            if harmonic:
                s = s + harmonic * np.cos(2 * np.pi * (2 * y / P - 2 * ph))
            img[:, j] = s
        return img

    # ---- A: period recovery under noise ----------------------------------
    img = lattice(lambda j: 0.0) + rng.normal(0, 1 / 0.3, (H, W))
    prof = axis_profile(img, 'lines')
    r = period_search(prof, px, *BANDS_MM['lines'])
    errA = abs(r['period_mm'] - P) / P
    res['A_period'] = dict(recovered=r['period_mm'], truth=P, rel_err=errA,
                           passed=bool(errA < 0.02))

    # ---- B: glitch localization ------------------------------------------
    j_step = 420
    img = lattice(lambda j: 0.0 if j < j_step else 0.4) \
        + rng.normal(0, 1.0, (H, W))
    x, ph, _ = track_phase(img, px, P, 'lines')
    g, _, _ = find_glitches(x, ph)
    x_true = j_step * px
    hit = (len(g) == 1 and abs(g[0]['x_mm'] - x_true) < 3 * P)
    ctrl = lattice(lambda j: 0.0) + rng.normal(0, 1.0, (H, W))
    xc, phc, _ = track_phase(ctrl, px, P, 'lines')
    gc, _, _ = find_glitches(xc, phc)
    res['B_glitch'] = dict(n_found=len(g),
                           x_found=(g[0]['x_mm'] if g else None),
                           x_true=x_true, n_control=len(gc),
                           passed=bool(hit and not gc))

    # ---- C: drift is not a glitch ----------------------------------------
    img = lattice(lambda j: 3.0 * j / W) + rng.normal(0, 1.0, (H, W))
    x, ph, _ = track_phase(img, px, P, 'lines')
    g, u, _ = find_glitches(x, ph)
    res['C_drift'] = dict(total_drift_periods=float(u[-1] - u[0]),
                          n_glitches=len(g), passed=bool(len(g) == 0))

    # ---- D: harmonic rejection -------------------------------------------
    sig = (1 + 0.6 * np.cos(np.pi * y / P)) * np.cos(2 * np.pi * y / P)
    img = np.tile(sig[:, None], (1, W)) + rng.normal(0, 1.0, (H, W))
    prof = axis_profile(img, 'lines')
    r = period_search(prof, px, *BANDS_MM['lines'])
    r_no = period_search(prof, px, *BANDS_MM['lines'], reject_harmonics=False)
    errD = abs(r['period_mm'] - P) / P
    fooled = abs(r_no['period_mm'] - 2 * P) / (2 * P) < 0.05
    res['D_harmonic'] = dict(recovered=r['period_mm'],
                             without_rejection=r_no['period_mm'], truth=P,
                             rejection_matters=bool(fooled),
                             passed=bool(errD < 0.02 and fooled))

    if verbose:
        print("=" * 70)
        print("ACCEPTANCE TEST -- phase_tracking (pre-registered)")
        print("=" * 70)
        A = res['A_period']
        print(f"A period @ SNR 0.3    {A['recovered']:.3f} mm vs {A['truth']:.2f} "
              f"({100*A['rel_err']:.1f} % err, <2) -> "
              f"{'PASS' if A['passed'] else 'FAIL'}")
        B = res['B_glitch']
        where = 'none' if B['x_found'] is None else f"{B['x_found']:.1f} mm"
        print(f"B glitch localized    {B['n_found']} found at {where} vs "
              f"{B['x_true']:.1f} mm true; control {B['n_control']} -> "
              f"{'PASS' if B['passed'] else 'FAIL'}")
        C = res['C_drift']
        print(f"C drift not a glitch  {C['total_drift_periods']:.1f} periods of "
              f"drift -> {C['n_glitches']} glitches (must be 0) -> "
              f"{'PASS' if C['passed'] else 'FAIL'}")
        D = res['D_harmonic']
        print(f"D harmonic rejected   {D['recovered']:.3f} mm vs {D['truth']:.2f} "
              f"truth; with rejection OFF it picks {D['without_rejection']:.3f} "
              f"({'2P -- the exam bites' if D['rejection_matters'] else 'no double, exam vacuous'}) "
              f"-> {'PASS' if D['passed'] else 'FAIL'}")
        print("-" * 70)
        print("OVERALL:", "PASS" if all(v['passed'] for v in res.values())
              else "FAIL")
    return res


# ---------------------------------------------------------------------------
def load_image(path):
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    return np.asarray(Image.open(path).convert('L'), float)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument('mode', choices=['search', 'track', 'test'])
    ap.add_argument('image', nargs='?', default=None)
    ap.add_argument('--width-mm', type=float, default=129.0)
    ap.add_argument('--axis', choices=['lines', 'columns'], default='lines')
    ap.add_argument('--period-mm', type=float, default=None,
                    help='skip the search and track at this period')
    ap.add_argument('--csv', type=str, default=None)
    ap.add_argument('--plot', type=str, default=None)
    args = ap.parse_args()

    if args.mode == 'test' or args.image is None:
        r = acceptance_test()
        sys.exit(0 if all(v['passed'] for v in r.values()) else 1)

    img = load_image(args.image)
    pixel_mm = args.width_mm / img.shape[1]
    p_min, p_max = BANDS_MM[args.axis]
    print(f"[image] {img.shape[1]} x {img.shape[0]} px, "
          f"{pixel_mm*1000:.1f} um/px")

    if args.period_mm:
        P = args.period_mm
        print(f"[period] {P:.3f} mm (given, search skipped)")
    else:
        prof = axis_profile(img, args.axis)
        r = period_search(prof, pixel_mm, p_min, p_max)
        P = r['period_mm']
        n_per = (img.shape[0 if args.axis == 'lines' else 1] * pixel_mm) / P
        print(f"[period] {P:.3f} mm  (chi2 {r['chi2']:.0f}, phase "
              f"{r['phase']:.3f}, {n_per:.0f} periods in the image)")
        if n_per < 12:
            print(f"[warning] only {n_per:.0f} periods along this axis. The "
                  f"search is weak here; locating\n          the bands "
                  f"directly is more robust than folding them.")

    if args.mode == 'search':
        return

    x, ph, amp = track_phase(img, pixel_mm, P, args.axis)
    g, u, resid = find_glitches(x, ph)
    print(f"[track ] {len(x)} windows, total drift "
          f"{u[-1]-u[0]:+.2f} periods (skew is innocent and is fitted out)")
    if g:
        print(f"[glitch] {len(g)} step(s) beyond the drift:")
        for gg in g:
            print(f"           {gg['x_mm']:8.1f} mm   step "
                  f"{gg['step']:+.3f} periods ({gg['sigma']:.1f} sigma)")
    else:
        print("[glitch] none: the phase is consistent with a smooth drift")

    if args.csv:
        np.savetxt(args.csv,
                   np.column_stack([x, ph, u, resid, amp]), delimiter=',',
                   header='x_mm,phase,unwrapped,residual,amplitude',
                   comments='', fmt='%.5f')
        print(f"[csv] {args.csv}")

    if args.plot:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
        axes[0].plot(x, u, '.-', ms=3, lw=0.8)
        axes[0].set_ylabel('unwrapped phase (periods)')
        axes[0].set_title(f'Phase track at {P:.3f} mm ({args.axis})')
        axes[1].plot(x, resid, '.-', ms=3, lw=0.8, color='0.3')
        for gg in g:
            for a in axes:
                a.axvline(gg['x_mm'], color='r', ls='--', lw=1)
        axes[1].set_ylabel('residual after removing drift')
        axes[1].set_xlabel('position (mm)')
        axes[1].set_title('A drift is skew; a step is a discontinuity')
        fig.tight_layout(); fig.savefig(args.plot, dpi=150)
        print(f"[plot] {args.plot}")


if __name__ == '__main__':
    main()
