#!/usr/bin/env python3
"""
orient_acceptance_test.py -- Acceptance test for grid_metric.py `orient` mode.

WHAT IS BEING TESTED
--------------------
`orient` claims to recover the local tilt of the writing baseline by rotating
the analysis axis and finding the orientation of maximum grid coherence.

The test that matters is NOT "does it output a number" but "does it recover a
KNOWN rotation". The subtlety that broke the first attempt: every window
already has its own baseline tilt (the papyrus surface undulates), so a raw
comparison against the imposed angle shows a constant offset and looks like a
bug. The correct test measures each window's baseline first, then imposes a
rotation, and checks

        recovered - baseline  ==  imposed

PASS CRITERIA (pre-registered)
------------------------------
  * median |error| < 1.0 deg across all windows and imposed angles
  * max    |error| < 2.0 deg
  * no systematic bias: |mean error| < 0.5 deg

KNOWN LIMIT (documented, not hidden): the estimator searches +-span_deg around
zero and saturates beyond it. The search must exceed |baseline tilt| +
|imposed|, and must stay well inside +-45 deg, where a rotation swaps the roles
of the letter and line components.

Usage:
    python orient_acceptance_test.py SURFACE.png --width-mm 129 \
        [--letters-mm 4.16 --lines-mm 2.79]
"""
import argparse
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, ".")
from grid_metric import orientation_at, load_surface  # noqa: E402

Image.MAX_IMAGE_PIXELS = None

IMPOSED = [-8.0, -4.0, -2.0, 0.0, 2.0, 4.0, 8.0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--width-mm", type=float, required=True)
    ap.add_argument("--letters-mm", type=float, default=4.16)
    ap.add_argument("--lines-mm", type=float, default=2.79)
    ap.add_argument("--win-w-mm", type=float, default=35.0)
    ap.add_argument("--n-windows", type=int, default=4)
    ap.add_argument("--span-deg", type=float, default=25.0,
                    help="search half-range; must exceed |baseline tilt| + |imposed| or the estimator saturates")
    a = ap.parse_args()

    arr, pixel_mm = load_surface(a.image, a.width_mm)
    periods = {"letters": a.letters_mm, "lines": a.lines_mm}
    win_w = int(a.win_w_mm / pixel_mm)
    starts = np.linspace(0, max(1, arr.shape[1] - win_w - 1), a.n_windows).astype(int)

    print(f"surface {arr.shape[1]}x{arr.shape[0]} px, {pixel_mm*1000:.1f} um/px")
    print(f"reference periods: letters {a.letters_mm} mm, lines {a.lines_mm} mm")
    print(f"{a.n_windows} windows of {a.win_w_mm:.0f} mm, imposed angles {IMPOSED}\n")

    errors = []
    print(f"{'window':>8} {'baseline':>9} {'imposed':>8} {'recovered':>10} {'error':>7}")
    for x0 in starts:
        win = arr[:, x0:x0 + win_w]
        base, _ = orientation_at(win, pixel_mm, periods, span_deg=a.span_deg)
        for imp in IMPOSED:
            rot = ndimage.rotate(win, imp, reshape=False, mode="reflect", order=1)
            rec, _ = orientation_at(rot, pixel_mm, periods, span_deg=a.span_deg)
            err = (rec - base) - imp
            errors.append(err)
            print(f"{x0*pixel_mm:8.0f} {base:9.2f} {imp:8.1f} {rec:10.2f} {err:+7.2f}")

    e = np.array(errors)
    med, mx, bias = np.median(np.abs(e)), np.max(np.abs(e)), np.mean(e)
    print(f"\nmedian |error| = {med:.2f} deg   (criterion < 1.00)")
    print(f"max    |error| = {mx:.2f} deg   (criterion < 2.00)")
    print(f"mean    error  = {bias:+.2f} deg   (criterion |bias| < 0.50)")
    ok = med < 1.0 and mx < 2.0 and abs(bias) < 0.5
    print(f"\nACCEPTANCE TEST: {'PASSED' if ok else 'FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
