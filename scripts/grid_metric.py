#!/usr/bin/env python3
"""
grid_metric.py -- Structural grid metric for Herculaneum rendered surfaces (v3.1).

Ancient writing has a grid: equally spaced lines, regular letter pitch, columns on a
module. This tool measures that grid and uses it two ways:

  ANALYZE one surface:   calibrate the scribe's signature (letter pitch, column
                         period via FFT along X; line spacing spatially, per column)
                         and map the windowed structural score.
  COMPARE two surfaces:  same region, two ink-detection models -> consensus map
                         (both see structure) and divergence map (they disagree),
                         a prioritized review queue for hallucination auditing.

The score measures text-LIKENESS, not truth. Divergence tells a reviewer where to
look first, not which model is right.

v3.1 corrections (see archives/ for the history):
  * CYCLE GATING: a component only enters a window's score if the window holds
    >= MIN_CYCLES of its period. On 30x8 mm windows only letter pitch qualifies;
    column period is assessed globally; line spacing is measured spatially per
    column (FFT line-spacing on a ~13 mm strip is a resolution-bin artifact).
  * Line spacing = median gap between spatially detected line centers, reported
    with IQR: on short strips the dispersion is part of the result.

Usage:
  python grid_metric.py analyze  IMAGE --width-mm 129
  python grid_metric.py compare  IMAGE_A IMAGE_B --width-mm 129 \
         --label-a "Model A" --label-b "Model B"

Outputs (PNG + CSV) are written next to the input, prefixed with its stem.
Requires: numpy scipy matplotlib pillow
"""
import argparse
import csv
import os
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks

Image.MAX_IMAGE_PIXELS = None

MIN_CYCLES = 3.0          # minimum cycles of a target period inside a window
WINDOW_W_MM = 30.0
WINDOW_H_MM = 8.0
STEP_MM = 3.0

BAND_LETTERS = (2.0, 4.5)     # mm
BAND_COLUMNS = (40.0, 80.0)   # mm -- band edges are a CALIBRATION CHOICE: a strong ~8 mm
                              # peak of unknown origin has a ~32 mm relative at lower freq;
                              # widening the band below 40 mm changes the detected period.
BAND_LINES = (2.0, 8.0)       # mm (spatial-domain estimation)


# ----------------------------- loading ------------------------------------
def load_surface(path, width_mm, downsample=1):
    img = Image.open(path).convert("L")
    if downsample > 1:
        w, h = img.size
        img = img.resize((w // downsample, h // downsample), Image.LANCZOS)
    arr = np.asarray(img, dtype=np.float32) / 255.0
    if arr.mean() > 0.5:          # want ink-positive (bright = ink)
        arr = 1.0 - arr
    pixel_mm = width_mm / arr.shape[1]
    return arr, pixel_mm


def match_sizes(a, b):
    if a.shape == b.shape:
        return a, b
    print(f"  sizes differ (A={a.shape}, B={b.shape}); rescaling B to A")
    im = Image.fromarray((b * 255).astype(np.uint8))
    im = im.resize((a.shape[1], a.shape[0]), Image.LANCZOS)
    return a, np.asarray(im, dtype=np.float32) / 255.0


# --------------------------- spectral tools --------------------------------
def dominant_period(signal, pixel_mm, p_min, p_max):
    """Dominant FFT period in [p_min, p_max] mm, or None."""
    s = signal - gaussian_filter1d(signal, sigma=max(2, len(signal) / 20))
    s = s * np.hanning(len(s))
    F = np.abs(np.fft.rfft(s))
    freq = np.fft.rfftfreq(len(s), d=pixel_mm)
    with np.errstate(divide="ignore"):
        per = np.where(freq > 0, 1.0 / freq, np.inf)
    m = (per >= p_min) & (per <= p_max) & np.isfinite(per)
    if not m.any():
        return None
    return float(per[np.where(m)[0][np.argmax(F[m])]])


def peak_prominence(signal, pixel_mm, p_obj, tol=0.20):
    """Prominence of the expected peak over the local spectral background."""
    if p_obj is None or len(signal) < 16:
        return 0.0
    s = signal - gaussian_filter1d(signal, sigma=max(2, len(signal) / 10))
    s = s * np.hanning(len(s))
    F = np.abs(np.fft.rfft(s))
    freq = np.fft.rfftfreq(len(s), d=pixel_mm)
    with np.errstate(divide="ignore"):
        per = np.where(freq > 0, 1.0 / freq, np.inf)
    m_peak = (per >= p_obj * (1 - tol)) & (per <= p_obj * (1 + tol))
    if not m_peak.any():
        return 0.0
    h_peak = F[m_peak].max()
    m_bg = (per >= p_obj * (1 - 3 * tol)) & (per <= p_obj * (1 + 3 * tol)) & ~m_peak
    if not m_bg.any() or h_peak == 0:
        return 0.0
    h_bg = np.median(F[m_bg]) + 1e-9
    return float(max(0.0, (h_peak - h_bg) / h_bg))


# ------------------- line spacing: spatial, per column ----------------------
def local_line_gaps(win, pixel_mm, p_min=BAND_LINES[0], p_max=BAND_LINES[1]):
    prof = win.sum(axis=1)
    if prof.std() < 1e-6:
        return []
    base = gaussian_filter1d(prof, sigma=max(3, int(p_max / pixel_mm)))
    p2 = gaussian_filter1d(prof - base, sigma=max(1, int(0.25 / pixel_mm)))
    peaks, _ = find_peaks(p2, distance=int(p_min / pixel_mm),
                          prominence=p2.std() * 0.4)
    if len(peaks) < 2:
        return []
    sp = np.diff(peaks) * pixel_mm
    return list(sp[(sp >= p_min) & (sp <= p_max)])


def line_spacing_by_columns(arr, pixel_mm, col_w_mm=20.0, step_mm=10.0):
    W = arr.shape[1]
    win_w = int(col_w_mm / pixel_mm)
    step = max(1, int(step_mm / pixel_mm))
    gaps = []
    for x0 in range(0, max(1, W - win_w), step):
        gaps += local_line_gaps(arr[:, x0:x0 + win_w], pixel_mm)
    if len(gaps) < 3:
        return None, None, len(gaps)
    g = np.array(gaps)
    q1, q3 = np.percentile(g, [25, 75])
    return float(np.median(g)), (float(q1), float(q3)), len(g)


# ----------------------------- calibration ---------------------------------
def calibrate_signature(arr, pixel_mm, label=""):
    pX = arr.sum(axis=0)
    letters = dominant_period(pX, pixel_mm, *BAND_LETTERS)
    columns = dominant_period(pX, pixel_mm, *BAND_COLUMNS)
    lines_med, lines_iqr, n_gaps = line_spacing_by_columns(arr, pixel_mm)
    if label:
        print(f"Signature of {label}:")
    print(f"  letter pitch : {letters:.2f} mm" if letters else "  letter pitch : not found")
    print(f"  column period: {columns:.2f} mm" if columns else "  column period: not found")
    if lines_med:
        print(f"  line spacing : {lines_med:.2f} mm  (IQR {lines_iqr[0]:.2f}-{lines_iqr[1]:.2f}, "
              f"n={n_gaps}; spatial per-column estimate)")
    else:
        print(f"  line spacing : not estimable ({n_gaps} gaps)")
    return {"letters": letters, "columns": columns, "lines": lines_med}


# --------------------------- gated window score -----------------------------
def window_score(win, pixel_mm, periods, min_cycles=MIN_CYCLES):
    h_mm = win.shape[0] * pixel_mm
    w_mm = win.shape[1] * pixel_mm
    pY = win.sum(axis=1); pY = pY - pY.mean()
    pX = win.sum(axis=0); pX = pX - pX.mean()
    comps = {
        "lines":   (periods.get("lines"),   pY, h_mm),
        "letters": (periods.get("letters"), pX, w_mm),
        "columns": (periods.get("columns"), pX, w_mm),
    }
    vals = []
    for p_obj, prof, ext in comps.values():
        if p_obj is None or ext / p_obj < min_cycles:
            continue                      # gated out: cannot be measured here
        vals.append(peak_prominence(prof, pixel_mm, p_obj))
    if not vals:
        return 0.0
    return float(np.exp(np.mean(np.log(np.array(vals) + 0.01))))


def sweep(arr, pixel_mm, periods):
    win_w = max(8, int(WINDOW_W_MM / pixel_mm))
    win_h = max(8, int(WINDOW_H_MM / pixel_mm))
    step = max(1, int(STEP_MM / pixel_mm))
    H, W = arr.shape
    xs = np.arange(win_w // 2, W - win_w // 2, step)
    ys = np.arange(win_h // 2, H - win_h // 2, step)
    if len(xs) == 0: xs = np.array([W // 2])
    if len(ys) == 0: ys = np.array([H // 2])
    S = np.zeros((len(ys), len(xs)), dtype=np.float32)
    print(f"  sweeping {len(xs)} x {len(ys)} = {len(xs) * len(ys)} windows "
          f"(gating: >= {MIN_CYCLES:g} cycles/component)")
    for j, yc in enumerate(ys):
        for i, xc in enumerate(xs):
            w = arr[yc - win_h // 2:yc + win_h // 2, xc - win_w // 2:xc + win_w // 2]
            S[j, i] = window_score(w, pixel_mm, periods)
    return S, xs, ys


# ------------------------------ plotting ------------------------------------
def _save_map(S, xs, ys, pixel_mm, title, path, cmap="viridis", vmin=None, vmax=None,
              cbar_label="score"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    ext = [xs[0] * pixel_mm, xs[-1] * pixel_mm, ys[-1] * pixel_mm, ys[0] * pixel_mm]
    fig, ax = plt.subplots(figsize=(13, 3.6))
    im = ax.imshow(S, cmap=cmap, aspect="auto", extent=ext, vmin=vmin, vmax=vmax)
    ax.set_title(title); ax.set_xlabel("X [mm]"); ax.set_ylabel("Y [mm]")
    fig.colorbar(im, ax=ax, label=cbar_label)
    fig.tight_layout(); fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"  wrote {path}")


def _save_csv(S, xs, ys, pixel_mm, path):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["x_mm", "y_mm", "score"])
        for j, yc in enumerate(ys):
            for i, xc in enumerate(xs):
                w.writerow([f"{xc * pixel_mm:.1f}", f"{yc * pixel_mm:.1f}", f"{S[j, i]:.4f}"])
    print(f"  wrote {path}")


# -------------------------------- modes -------------------------------------
def run_analyze(args):
    arr, pixel_mm = load_surface(args.image, args.width_mm, args.downsample)
    stem = os.path.splitext(os.path.basename(args.image))[0]
    print(f"{args.image}: {arr.shape[1]}x{arr.shape[0]} px, pixel = {pixel_mm*1000:.1f} um")
    periods = calibrate_signature(arr, pixel_mm, label=stem)
    S, xs, ys = sweep(arr, pixel_mm, periods)
    print(f"  score: min={S.min():.3f} max={S.max():.3f} median={np.median(S):.3f}")
    _save_map(S, xs, ys, pixel_mm, f"Structural score — {stem}", f"{stem}_score.png")
    _save_csv(S, xs, ys, pixel_mm, f"{stem}_score.csv")


def run_compare(args):
    A, pixel_mm = load_surface(args.image_a, args.width_mm, args.downsample)
    B, _ = load_surface(args.image_b, args.width_mm, args.downsample)
    A, B = match_sizes(A, B)
    la, lb = args.label_a, args.label_b
    print(f"pixel = {pixel_mm*1000:.1f} um")
    pa = calibrate_signature(A, pixel_mm, label=la)
    pb = calibrate_signature(B, pixel_mm, label=lb)
    common = {k: (np.mean([pa[k], pb[k]]) if (pa[k] and pb[k]) else (pa[k] or pb[k]))
              for k in ("lines", "letters", "columns")}
    print("Common signature for local comparison:", {k: (f"{v:.2f} mm" if v else None) for k, v in common.items()})

    print(f"Sweeping {la} ..."); SA, xs, ys = sweep(A, pixel_mm, common)
    print(f"Sweeping {lb} ..."); SB, _, _ = sweep(B, pixel_mm, common)

    nA = SA / (np.percentile(SA, 95) + 1e-9)
    nB = SB / (np.percentile(SB, 95) + 1e-9)
    consensus = np.minimum(nA, nB)
    diff = SA - SB
    agree = float(np.corrcoef(SA.ravel(), SB.ravel())[0, 1])
    print(f"Map agreement (Pearson r): {agree:.3f}")
    print(f"A>B in {(diff > 0).mean()*100:.1f}% of windows; B>A in {(diff < 0).mean()*100:.1f}%")

    vmax = max(np.percentile(SA, 99), np.percentile(SB, 99))
    _save_map(SA, xs, ys, pixel_mm, f"Structural score — {la}", "compare_score_A.png", vmax=vmax)
    _save_map(SB, xs, ys, pixel_mm, f"Structural score — {lb}", "compare_score_B.png", vmax=vmax)
    _save_map(consensus, xs, ys, pixel_mm, "Consensus (high where BOTH see structure)",
              "compare_consensus.png", cmap="Greens", vmin=0, vmax=1)
    _save_map(diff, xs, ys, pixel_mm,
              f"Divergence A−B (red: only {la}; blue: only {lb}) — review queue",
              "compare_divergence.png", cmap="RdBu_r", vmin=-vmax / 2, vmax=vmax / 2,
              cbar_label="score diff")
    _save_csv(diff, xs, ys, pixel_mm, "compare_divergence.csv")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)

    a = sub.add_parser("analyze", help="signature + score map of one surface")
    a.add_argument("image")
    a.add_argument("--width-mm", type=float, required=True,
                   help="physical width of the image in mm (calibrates the pixel)")
    a.add_argument("--downsample", type=int, default=1)
    a.set_defaults(func=run_analyze)

    c = sub.add_parser("compare", help="consensus/divergence between two renders of the same region")
    c.add_argument("image_a"); c.add_argument("image_b")
    c.add_argument("--width-mm", type=float, required=True)
    c.add_argument("--downsample", type=int, default=1)
    c.add_argument("--label-a", default="A"); c.add_argument("--label-b", default="B")
    c.set_defaults(func=run_compare)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
