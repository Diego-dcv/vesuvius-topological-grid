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


def sweep(arr, pixel_mm, periods, win_w_mm=WINDOW_W_MM, win_h_mm=WINDOW_H_MM):
    win_w = max(8, int(win_w_mm / pixel_mm))
    win_h = max(8, min(int(win_h_mm / pixel_mm), arr.shape[0]))
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





def cross2d_score(win, pixel_mm, periods, ang_tol_deg=2.5, ang_bg=(6.0, 30.0),
                  min_cycles=MIN_CYCLES):
    """v2 score for rank mode: axis-aligned 2D-FFT grid energy, ring-normalized.
    Measures whether grid energy sits WHERE it should (scribe's frequencies) and
    ON-AXIS (square to the page). Rotation moves peaks off-axis, warp smears
    them, and each peak is compared to its own frequency ring so resampling
    smoothing cancels out. Deliberately tolerant to render noise (design
    decision, documented in the acceptance test)."""
    g = win - win.mean()
    wy = np.hanning(win.shape[0])[:, None]; wx = np.hanning(win.shape[1])[None, :]
    F = np.abs(np.fft.fftshift(np.fft.fft2(g * wy * wx)))**2
    fy = np.fft.fftshift(np.fft.fftfreq(win.shape[0], d=pixel_mm))
    fx = np.fft.fftshift(np.fft.fftfreq(win.shape[1], d=pixel_mm))
    FX, FY = np.meshgrid(fx, fy)
    R = np.hypot(FX, FY)
    angx = np.degrees(np.arctan2(np.abs(FY), np.abs(FX)))
    angy = 90.0 - angx
    vals = []
    for p, ext, ang in [(periods.get("letters"), win.shape[1]*pixel_mm, angx),
                        (periods.get("lines"),   win.shape[0]*pixel_mm, angy)]:
        if p is None or ext / p < min_cycles:
            continue
        f0 = 1.0 / p
        band = (R > f0*0.82) & (R < f0*1.18)
        axial = band & (ang <= ang_tol_deg)
        ring = band & (ang >= ang_bg[0]) & (ang <= ang_bg[1])
        if not axial.any() or not ring.any():
            continue
        vals.append(float(F[axial].max() / (np.median(F[ring]) + 1e-12)))
    return float(np.exp(np.mean(np.log(np.array(vals) + 1e-9)))) if vals else 0.0

def run_rank(args):
    """Screen multiple candidate renders of the same region: score each against
    the common signature and rank. Selective use only -- ranks existing
    candidates, never places windings (see sean bruniss's warning re: pitch).

    STATUS: v3 -- integrated acceptance test PASSES ON ORDER. The decisive fix
    (Diego's standardization principle): the reference signature is EXTERNAL --
    known corpus values passed via --letters-mm/--lines-mm, or measured once on
    a trusted source -- never calibrated from the candidate pool, so degraded
    candidates cannot contaminate the ruler. Ranking is by MEDIAN across
    windows. Result on the real-strip control: original first; line-wobble warp
    (the classic unwrap error) -24 percent; rotation and noise below original but
    with THIN margins (~3 percent median vs rotation) -- expected physics: letter
    pitch is nearly rotation-invariant and the discriminating line component is
    cycle-starved on a 13 mm strip. Margins should widen on taller strips.
    Use accordingly: trust it to flag clearly bad geometry; treat close scores
    as inconclusive; it does not arbitrate between two good candidates."""
    arrs, names = [], []
    for p in args.images:
        a, pixel_mm = load_surface(p, args.width_mm, args.downsample)
        arrs.append(a); names.append(os.path.splitext(os.path.basename(p))[0])
    # Reference signature: EXTERNAL by design (Diego's standardization
    # principle) -- known values are passed in, or measured once on a trusted
    # source; never calibrated from the candidate pool, so degraded candidates
    # cannot contaminate the ruler.
    if args.letters_mm or args.lines_mm:
        common = {"letters": args.letters_mm, "lines": args.lines_mm, "columns": None}
    else:
        print("WARNING: no external reference given (--letters-mm/--lines-mm); "
              "falling back to pooled calibration, which degraded candidates can contaminate.")
        sigs = [calibrate_signature(a, pixel_mm, label=n) for a, n in zip(arrs, names)]
        common = {}
        for k in ("lines", "letters", "columns"):
            vals = [s[k] for s in sigs if s[k]]
            common[k] = float(np.median(vals)) if vals else None
    print("Common signature:", {k: (f"{v:.2f} mm" if v else None) for k, v in common.items()})

    rows = []
    for a, n in zip(arrs, names):
        win_w = max(16, int(args.win_w_mm / pixel_mm)); step = max(1, win_w // 3)
        ss = [cross2d_score(a[:, x0:x0 + win_w], pixel_mm, common)
              for x0 in range(0, max(1, a.shape[1] - win_w), step)]
        S = np.array(ss if ss else [0.0])
        rows.append((n, float(np.mean(S)), float(np.median(S)), float(np.percentile(S, 90))))
    rows.sort(key=lambda r: -r[2])   # rank by MEDIAN (robust to outlier windows)

    print(f"\nRanking (higher = grid survives better):")
    print(f"{'rank':>4}  {'candidate':<28} {'mean':>7} {'median':>7} {'p90':>7}")
    for i, (n, m, md, p90) in enumerate(rows, 1):
        print(f"{i:>4}  {n:<28} {m:7.3f} {md:7.3f} {p90:7.3f}")
    with open("rank_results.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["rank", "candidate", "mean", "median", "p90"])
        for i, r in enumerate(rows, 1): w.writerow([i, *r])
    print("wrote rank_results.csv")


# ------------------------- orient: directional coherence --------------------
def grid_energy_rotated(win, pixel_mm, periods, angle_deg, crop=0.15):
    """cross2d_score after de-rotating the window by angle_deg. If the writing
    grid sits at +angle, de-rotating by that angle brings it onto the axes and
    the score peaks -- so argmax over angle recovers the local grid orientation."""
    from scipy import ndimage
    r = ndimage.rotate(win, -angle_deg, reshape=False, mode="reflect", order=1)
    h, w = r.shape
    m = int(crop * min(h, w))
    r = r[m:h - m, m:w - m]
    if min(r.shape) < 16:
        return 0.0
    return cross2d_score(r, pixel_mm, periods)


def orientation_at(win, pixel_mm, periods, span_deg=14.0, step_deg=1.0):
    """Local orientation of the writing grid, in degrees. Parabolic refinement
    around the coarse maximum. Returns (angle_deg, peak_score)."""
    angles = np.arange(-span_deg, span_deg + step_deg, step_deg)
    scores = np.array([grid_energy_rotated(win, pixel_mm, periods, a) for a in angles])
    i = int(np.argmax(scores))
    best = float(angles[i])
    if 0 < i < len(scores) - 1:
        y0, y1, y2 = scores[i - 1:i + 2]
        den = y0 - 2 * y1 + y2
        if abs(den) > 1e-12:
            best = float(angles[i] - 0.5 * step_deg * (y2 - y0) / den)
    return best, float(scores[i])


def run_orient(args):
    """Map the local tilt of the writing baseline across a surface.

    An orientation estimator independent of CT intensity: it reads the text
    layout, not the sheet normal, so systematic disagreement with a
    structure-tensor normal field is a cheap mesh-QA signal.

    STATUS: PASSES its acceptance test (orient_acceptance_test.py) on a real
    Paris 4 surface: median |error| 0.00 deg, max 1.37 deg, bias +0.09 deg over
    4 windows x 7 imposed rotations, each measured against that window's own
    baseline tilt. Two declared limits: the search saturates beyond
    +-span_deg (raise it if the surface is strongly tilted, but stay well
    inside +-45 deg, where a rotation swaps the letter and line components);
    and the absolute zero is the image grid, not the scroll axis, so compare
    tilts between surfaces, never absolute angles.
    """
    arr, pixel_mm = load_surface(args.image, args.width_mm, args.downsample)
    stem = os.path.splitext(os.path.basename(args.image))[0]
    periods = {"letters": args.letters_mm, "lines": args.lines_mm}
    if periods["letters"] is None and periods["lines"] is None:
        sig = calibrate_signature(arr, pixel_mm, label=stem)
        periods = {"letters": sig["letters"], "lines": sig["lines"]}
    print("reference periods: " + ", ".join(
        f"{k} {v:.2f} mm" if v else f"{k} n/a" for k, v in periods.items()))

    win_w = max(16, int(args.win_w_mm / pixel_mm))
    step = max(1, int(args.step_mm / pixel_mm))
    xs, ang, strength = [], [], []
    for x0 in range(0, max(1, arr.shape[1] - win_w), step):
        a, s = orientation_at(arr[:, x0:x0 + win_w], pixel_mm, periods)
        xs.append((x0 + win_w / 2) * pixel_mm); ang.append(a); strength.append(s)
    xs, ang, strength = np.array(xs), np.array(ang), np.array(strength)
    print(f"  {len(xs)} windows | tilt {ang.min():.1f} to {ang.max():.1f} deg "
          f"(median {np.median(ang):.1f})")

    with open(f"{stem}_orient.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["x_mm", "tilt_deg", "grid_strength"])
        for a, b, c in zip(xs, ang, strength):
            w.writerow([f"{a:.1f}", f"{b:.2f}", f"{c:.3f}"])
    print(f"  wrote {stem}_orient.csv")

    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        H_mm = arr.shape[0] * pixel_mm; W_mm = arr.shape[1] * pixel_mm
        fig, (a0, a1) = plt.subplots(2, 1, figsize=(13, 6), height_ratios=[2.2, 1])
        a0.imshow(arr, cmap="gray", aspect="auto", extent=[0, W_mm, H_mm, 0],
                  vmin=np.percentile(arr, 2), vmax=np.percentile(arr, 98))
        smax = strength.max() if strength.max() > 0 else 1.0
        for x, a, s in zip(xs, ang, strength):
            L = args.win_w_mm / 7.0; t = np.radians(a)
            a0.plot([x - L * np.cos(t), x + L * np.cos(t)],
                    [H_mm / 2 - L * np.sin(t), H_mm / 2 + L * np.sin(t)],
                    color=plt.cm.viridis(s / smax), lw=2.2, solid_capstyle="round")
        a0.set_title(f"Local writing orientation - {stem}")
        a0.set_xlabel("X [mm]"); a0.set_ylabel("Y [mm]")
        a1.plot(xs, ang, "-o", ms=3, color="steelblue")
        a1.axhline(0, ls=":", c="grey", lw=0.8)
        a1.set_xlabel("X [mm]"); a1.set_ylabel("tilt [deg]"); a1.grid(alpha=0.3)
        a1.set_title("baseline tilt vs position")
        fig.tight_layout(); fig.savefig(f"{stem}_orient.png", dpi=140, bbox_inches="tight")
        print(f"  wrote {stem}_orient.png")
    except Exception as e:
        print("figure step skipped:", e)

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

    r = sub.add_parser("rank", help="screen K candidate renders of the same region; rank by grid survival")
    r.add_argument("images", nargs="+")
    r.add_argument("--width-mm", type=float, required=True)
    r.add_argument("--downsample", type=int, default=1)
    r.add_argument("--letters-mm", type=float, default=None, help="external reference letter pitch (known/trusted)")
    r.add_argument("--lines-mm", type=float, default=None, help="external reference line spacing (known/trusted)")
    r.add_argument("--win-w-mm", type=float, default=WINDOW_W_MM)
    r.add_argument("--win-h-mm", type=float, default=WINDOW_H_MM,
                   help="use the full strip height on short strips so the line component re-enters the gated score")
    r.set_defaults(func=run_rank)

    o = sub.add_parser("orient", help="map the local tilt of the writing baseline")
    o.add_argument("image")
    o.add_argument("--width-mm", type=float, required=True)
    o.add_argument("--downsample", type=int, default=1)
    o.add_argument("--letters-mm", type=float, default=None)
    o.add_argument("--lines-mm", type=float, default=None)
    o.add_argument("--win-w-mm", type=float, default=30.0)
    o.add_argument("--step-mm", type=float, default=10.0)
    o.set_defaults(func=run_orient)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
