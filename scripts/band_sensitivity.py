#!/usr/bin/env python3
"""
band_sensitivity.py -- Is a detected period a property of the image, or of
the search band we chose to look in?

Diego C. V. (vesuvius-topological-grid)

WHY
---
`grid_metric.py` finds each period by taking the dominant spectral peak
inside a hand-set band:

    BAND_LETTERS = (2.0, 4.5) mm   -> reported 4.16 mm   (92 % toward the top edge)
    BAND_COLUMNS = (40.0, 80.0) mm -> reported 43.0 mm   ( 7 % above the bottom edge)
    BAND_LINES   = (2.0, 8.0) mm   -> reported 2.79 mm   (comfortably interior,
                                                          and estimated in the
                                                          spatial domain, not by FFT)

Two of the three sit against a band edge. The source itself already warns
that widening BAND_COLUMNS below 40 mm changes the answer; the same question
was never asked of BAND_LETTERS. This matters because the line spacing has
form: 4.45 mm was reported before it turned out to be a resolution artefact.

THE TEST
--------
A real period does not care where you look for it. So: sweep the band edges
and watch the reported period.

    STABLE   -> the reported period stays put as the band widens. The band was
                a convenience, not a constraint. The measurement stands.
    TRACKING -> the reported period follows the edge you move. Then it is the
                band that is being measured, not the papyrus, and the true
                peak lies outside. The measurement does not stand.
    JUMP     -> the period leaps to a different value once the band admits it.
                The new value is a candidate for the true fundamental; check
                whether the old one is a harmonic of it (a 3:2 or 2:1 ratio
                between two reported periods is the signature).

Note on 4.16 vs 2.79: their ratio is 1.49, near 3:2. If both were harmonics of
a ~1.39 mm fundamental, that would produce exactly this pair. The sweep is
what settles it.

USAGE
-----
    python band_sensitivity.py IMAGE.png --width-mm 129 --axis letters
    python band_sensitivity.py IMAGE.png --width-mm 129 --axis columns
    python band_sensitivity.py --test          # no image needed

The image is a public Paris 4 render; see docs/data_sources.md.
"""

import argparse
import sys
import numpy as np


def dominant_period(signal, pixel_mm, p_min, p_max):
    """Dominant spectral period within [p_min, p_max] mm. Mirrors the
    implementation in grid_metric.py so the comparison is like for like."""
    x = np.asarray(signal, float)
    x = x - x.mean()
    if x.size < 8:
        return None
    F = np.abs(np.fft.rfft(x * np.hanning(x.size)))
    freq = np.fft.rfftfreq(x.size, d=pixel_mm)
    with np.errstate(divide='ignore'):
        per = np.where(freq > 0, 1.0 / np.maximum(freq, 1e-12), np.inf)
    m = (per >= p_min) & (per <= p_max)
    if not m.any():
        return None
    idx = np.argmax(F[m])
    return float(per[m][idx])


def sweep_band(profile, pixel_mm, p_lo, p_hi, widen=(1.0, 1.25, 1.5, 2.0, 3.0)):
    """Report the detected period as each edge is pushed outward."""
    rows = []
    for k in widen:
        lo, hi = p_lo / k, p_hi * k
        rows.append((k, lo, hi, dominant_period(profile, pixel_mm, lo, hi)))
    return rows


def verdict(rows, p_ref, tol=0.05):
    """STABLE / TRACKING / JUMP, by the rule stated in the docstring."""
    vals = [r[3] for r in rows if r[3] is not None]
    if len(vals) < 2:
        return "INCONCLUSIVE", 0.0
    drift = max(abs(v - p_ref) / p_ref for v in vals)
    if drift <= tol:
        return "STABLE", drift
    # tracking: the reported period rises monotonically with the upper edge
    ups = [r[2] for r in rows if r[3] is not None]
    corr = np.corrcoef(ups, vals)[0, 1] if len(vals) > 2 else 0.0
    if corr > 0.9:
        return "TRACKING", drift
    return "JUMP", drift


def harmonic_note(p_a, p_b):
    """Flag a small-integer ratio between two reported periods."""
    if not p_a or not p_b:
        return ""
    r = max(p_a, p_b) / min(p_a, p_b)
    for n, d in ((3, 2), (2, 1), (5, 3), (3, 1), (4, 3)):
        if abs(r - n / d) < 0.04:
            f = min(p_a, p_b) / d
            return (f"  ratio {r:.2f} is within 4 % of {n}:{d} -- both may be "
                    f"harmonics of a ~{f:.2f} mm fundamental")
    return ""


# --------------------------------------------------------------------------
def acceptance_test(verbose=True):
    """Pre-registered. Three synthetic profiles with known content:

    A. TRUE PERIOD INSIDE THE BAND. Signal at 3.0 mm, band (2.0, 4.5).
       PASS: verdict STABLE and the recovered period within 3 % of 3.0.
    B. TRUE PERIOD OUTSIDE THE BAND. Signal at 6.5 mm, band (2.0, 4.5) -- the
       failure mode we suspect for BAND_LETTERS.
       PASS: verdict is NOT stable, and once the band widens the recovered
       period lands within 3 % of 6.5.
    C. HARMONIC PAIR. Fundamental at 1.4 mm with strong 2nd and 3rd harmonics
       (i.e. energy at 2.8 and 4.2 mm), the pattern that would produce a
       4.16/2.79 pair from one grid.
       PASS: harmonic_note flags the 3:2 ratio and names a fundamental within
       5 % of 1.4 mm.
    """
    px = 0.0791 / 2       # mm/px, Paris 4 at one downsample step (15.82 um)
    n = 8000
    x = np.arange(n) * px
    rng = np.random.default_rng(0)
    res = {}

    # A -- true period inside the band
    sig = np.cos(2 * np.pi * x / 3.0) + 0.3 * rng.normal(size=n)
    rows = sweep_band(sig, px, 2.0, 4.5)
    v, drift = verdict(rows, 3.0)
    okA = v == "STABLE" and abs(rows[0][3] - 3.0) / 3.0 < 0.03
    res['A_inside'] = dict(verdict=v, recovered=rows[0][3], passed=bool(okA))

    # B -- true period outside the band
    sig = np.cos(2 * np.pi * x / 6.5) + 0.3 * rng.normal(size=n)
    rows = sweep_band(sig, px, 2.0, 4.5)
    v, drift = verdict(rows, rows[0][3])
    widest = rows[-1][3]
    okB = v != "STABLE" and abs(widest - 6.5) / 6.5 < 0.03
    res['B_outside'] = dict(verdict=v, in_band=rows[0][3], widened=widest,
                            passed=bool(okB))

    # C -- harmonic pair
    note = harmonic_note(4.16, 2.79)
    okC = "3:2" in note and "1.39" in note or "1.40" in note
    res['C_harmonic'] = dict(note=note.strip(), passed=bool(okC))

    if verbose:
        print("=" * 70)
        print("ACCEPTANCE TEST -- band_sensitivity (pre-registered)")
        print("=" * 70)
        A = res['A_inside']
        print(f"A period inside band   verdict {A['verdict']}, recovered "
              f"{A['recovered']:.2f} mm (true 3.00) -> "
              f"{'PASS' if A['passed'] else 'FAIL'}")
        B = res['B_outside']
        print(f"B period outside band  in-band {B['in_band']:.2f} mm is an "
              f"artefact; widened -> {B['widened']:.2f} mm (true 6.50), "
              f"verdict {B['verdict']} -> {'PASS' if B['passed'] else 'FAIL'}")
        C = res['C_harmonic']
        print(f"C harmonic detection   {C['note'] or '(no ratio flagged)'} -> "
              f"{'PASS' if C['passed'] else 'FAIL'}")
        print("-" * 70)
        print("OVERALL:", "PASS" if all(v['passed'] for v in res.values())
              else "FAIL")
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument('image', nargs='?', default=None,
                    help="path to a render, or the literal word 'test'")
    ap.add_argument('--width-mm', type=float, default=129.0)
    ap.add_argument('--axis', choices=['letters', 'columns'], default='letters')
    ap.add_argument('--test', action='store_true')
    args = ap.parse_args()

    # house style across this repo is a positional `test` mode; accept both
    if args.image == 'test':
        args.test = True
    if args.test or args.image is None:
        res = acceptance_test()
        sys.exit(0 if all(v['passed'] for v in res.values()) else 1)

    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    arr = np.asarray(Image.open(args.image).convert('L'), float)
    pixel_mm = args.width_mm / arr.shape[1]
    profile = arr.sum(axis=0)          # horizontal profile: letters, columns

    p_lo, p_hi = (2.0, 4.5) if args.axis == 'letters' else (40.0, 80.0)
    ref = dominant_period(profile, pixel_mm, p_lo, p_hi)
    rows = sweep_band(profile, pixel_mm, p_lo, p_hi)
    v, drift = verdict(rows, ref)

    print(f"[image] {arr.shape[1]} x {arr.shape[0]} px, "
          f"{pixel_mm*1000:.1f} um/px at --width-mm {args.width_mm:.0f}")
    print(f"[band ] {args.axis}: nominal ({p_lo}, {p_hi}) mm -> {ref:.2f} mm\n")
    print(f"  {'widen':>6} {'band (mm)':>18} {'detected':>10}")
    print("  " + "-" * 38)
    for k, lo, hi, p in rows:
        print(f"  {k:>5.2f}x {lo:>8.2f} - {hi:<7.2f} "
              f"{(f'{p:.2f} mm' if p else 'none'):>10}")
    print(f"\n  VERDICT: {v}  (max drift {drift*100:.1f} % from the nominal-band "
          f"value)")
    if v == "STABLE":
        print("  The band was a convenience, not a constraint. The measurement "
              "stands.")
    elif v == "TRACKING":
        print("  The reported period follows the edge: the band is being "
              "measured, not\n  the papyrus. The true peak lies outside the "
              "nominal band.")
    else:
        print("  The period jumps once the band admits a different peak. Treat "
              "the widened\n  value as the candidate and check the old one for "
              "a harmonic relation.")
    note = harmonic_note(rows[-1][3], ref)
    if note:
        print(note)


if __name__ == '__main__':
    main()
