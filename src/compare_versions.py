"""
compare_versions.py — Compare two rendered surfaces of the same scroll.

Computes local topological maps for two rendered surfaces (typically produced
by different ML architectures over the same geometric segmentation), and
generates consensus and divergence maps to identify robust readings and
zones requiring manual review.

The metric used is spectral prominence: how much each expected peak stands
out above the local spectral background. This rewards clear structure and
penalizes noise.

Usage:
    python compare_versions.py path/to/version_A.png path/to/version_B.png
    python compare_versions.py A.png B.png --label-a "Model A" --label-b "Model B"
    python compare_versions.py A.png B.png --pixel-size 7.91 --downsample 2

Output:
    comp_originals.png  — the two images side by side
    comp_scores.png     — local topological maps of each version
    comp_diff.png       — consensus map (green) + divergence map (red/blue)
    Console: detected periods, score statistics, consensus/divergence summary

Requirements:
    pip install numpy scipy matplotlib pillow
"""

import argparse
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from scipy.ndimage import gaussian_filter1d


# ----------------------------------------------------------------------------
# Image loading
# ----------------------------------------------------------------------------

def load_image(path, downsample=1):
    if not os.path.exists(path):
        sys.exit(f"ERROR: file not found: {path}")
    img = Image.open(path).convert('L')
    if downsample > 1:
        w, h = img.size
        img = img.resize((w // downsample, h // downsample), Image.LANCZOS)
    arr = np.array(img, dtype=np.float32) / 255.0
    if arr.mean() > 0.5:
        arr = 1.0 - arr
    return arr


def align_sizes(arr_a, arr_b):
    """If two images have different shapes, resize B to A's shape."""
    if arr_a.shape == arr_b.shape:
        return arr_a, arr_b
    print(f"  Different sizes: A={arr_a.shape}, B={arr_b.shape}. "
          f"Resizing B to A's shape.")
    img_b = Image.fromarray((arr_b * 255).astype(np.uint8))
    img_b = img_b.resize((arr_a.shape[1], arr_a.shape[0]), Image.LANCZOS)
    return arr_a, np.array(img_b, dtype=np.float32) / 255.0


# ----------------------------------------------------------------------------
# Spectral analysis
# ----------------------------------------------------------------------------

def detect_period(signal, pixel_mm, p_min, p_max):
    s = signal - gaussian_filter1d(signal, sigma=len(signal) / 20)
    s = s * np.hanning(len(s))
    fft = np.abs(np.fft.rfft(s))
    freq = np.fft.rfftfreq(len(s), d=pixel_mm)
    with np.errstate(divide='ignore'):
        per = np.where(freq > 0, 1.0 / freq, np.inf)
    mask = (per >= p_min) & (per <= p_max)
    if not mask.any():
        return None
    idx = np.where(mask)[0][np.argmax(fft[mask])]
    return per[idx]


def calibrate_global_signature(arr, pixel_mm):
    """Detect the three dominant spatial periods of a rendered surface."""
    pY, pX = arr.sum(axis=1), arr.sum(axis=0)
    return (detect_period(pY, pixel_mm, 3.0, 8.0),
            detect_period(pX, pixel_mm, 2.0, 5.0),
            detect_period(pX, pixel_mm, 8.0, 30.0))


def peak_prominence(signal, pixel_mm, p_target, tol=0.20):
    """How much the expected peak stands out above the local spectral background.

    Returns a value in [0, ~1+]: 0 = no peak, higher = more prominent.
    Unlike a simple energy-fraction metric, this rewards clear structure and
    is not contaminated by overall ink density.
    """
    if p_target is None or len(signal) < 16:
        return 0.0
    s = signal - gaussian_filter1d(signal, sigma=max(2, len(signal) / 10))
    s = s * np.hanning(len(s))
    fft = np.abs(np.fft.rfft(s))
    freq = np.fft.rfftfreq(len(s), d=pixel_mm)
    with np.errstate(divide='ignore'):
        per = np.where(freq > 0, 1.0 / freq, np.inf)
    peak_mask = (per >= p_target * (1 - tol)) & (per <= p_target * (1 + tol))
    if not peak_mask.any():
        return 0.0
    h_peak = fft[peak_mask].max()
    bg_mask = ((per >= p_target * (1 - 3 * tol)) &
               (per <= p_target * (1 + 3 * tol)) &
               ~peak_mask)
    if not bg_mask.any() or h_peak == 0:
        return 0.0
    h_bg = np.median(fft[bg_mask]) + 1e-9
    return float(max(0.0, (h_peak - h_bg) / h_bg))


def structural_score(window, pixel_mm, periods):
    """Combined prominence in Y (lines) and X (letters + columns)."""
    if window.size == 0:
        return 0.0
    pY = window.sum(axis=1) - window.sum(axis=1).mean()
    pX = window.sum(axis=0) - window.sum(axis=0).mean()
    p_lines = peak_prominence(pY, pixel_mm, periods.get('lines'))
    p_letters = peak_prominence(pX, pixel_mm, periods.get('letters'))
    p_columns = peak_prominence(pX, pixel_mm, periods.get('columns'))
    return float(np.cbrt((p_lines + 0.01) *
                         (p_letters + 0.01) *
                         (p_columns + 0.01)))


# ----------------------------------------------------------------------------
# Window sweep
# ----------------------------------------------------------------------------

def sweep(arr, pixel_mm, win_w_mm, win_h_mm, step_mm, periods):
    win_w = max(8, int(win_w_mm / pixel_mm))
    win_h = max(8, int(win_h_mm / pixel_mm))
    step = max(1, int(step_mm / pixel_mm))
    H, W = arr.shape

    xs = np.arange(win_w // 2, W - win_w // 2, step)
    ys = np.arange(win_h // 2, H - win_h // 2, step)
    if len(xs) == 0:
        xs = np.array([W // 2])
    if len(ys) == 0:
        ys = np.array([H // 2])

    ink_map = np.zeros((len(ys), len(xs)), dtype=np.float32)
    score_map = np.zeros_like(ink_map)

    print(f"  Sweeping {len(xs)} x {len(ys)} = {len(xs) * len(ys)} windows...")
    for j, yc in enumerate(ys):
        for i, xc in enumerate(xs):
            v = arr[yc - win_h // 2:yc + win_h // 2,
                    xc - win_w // 2:xc + win_w // 2]
            ink_map[j, i] = v.mean()
            score_map[j, i] = structural_score(v, pixel_mm, periods)
    return ink_map, score_map, xs, ys


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------

def compare(image_a, image_b, label_a, label_b,
            pixel_size_um, downsample,
            win_w_mm, win_h_mm, step_mm):
    pixel_mm = pixel_size_um * downsample / 1000.0
    print(f"Effective resolution: {pixel_mm * 1000:.2f} um/pixel")

    print(f"\nLoading A: {image_a}")
    arr_a = load_image(image_a, downsample)
    print(f"  {arr_a.shape[1]} x {arr_a.shape[0]} pixels = "
          f"{arr_a.shape[1] * pixel_mm:.0f} x {arr_a.shape[0] * pixel_mm:.0f} mm")

    print(f"\nLoading B: {image_b}")
    arr_b = load_image(image_b, downsample)
    print(f"  {arr_b.shape[1]} x {arr_b.shape[0]} pixels = "
          f"{arr_b.shape[1] * pixel_mm:.0f} x {arr_b.shape[0] * pixel_mm:.0f} mm")

    arr_a, arr_b = align_sizes(arr_a, arr_b)

    print(f"\nGlobal signature of {label_a}:")
    pl_a, plet_a, pc_a = calibrate_global_signature(arr_a, pixel_mm)
    print(f"  Lines: {pl_a:.2f} mm, Letters: {plet_a:.2f} mm, "
          f"Columns: {pc_a:.2f} mm")

    print(f"\nGlobal signature of {label_b}:")
    pl_b, plet_b, pc_b = calibrate_global_signature(arr_b, pixel_mm)
    print(f"  Lines: {pl_b:.2f} mm, Letters: {plet_b:.2f} mm, "
          f"Columns: {pc_b:.2f} mm")

    common_periods = {
        'lines':   np.mean([pl_a, pl_b])     if (pl_a and pl_b) else (pl_a or pl_b),
        'letters': np.mean([plet_a, plet_b]) if (plet_a and plet_b) else (plet_a or plet_b),
        'columns': np.mean([pc_a, pc_b])     if (pc_a and pc_b) else (pc_a or pc_b),
    }
    print(f"\nCommon signature for local comparison:")
    print(f"  Lines: {common_periods['lines']:.2f} mm")
    print(f"  Letters: {common_periods['letters']:.2f} mm")
    print(f"  Columns: {common_periods['columns']:.2f} mm")

    print(f"\nSweeping {label_a}...")
    ta, sa, xs, ys = sweep(arr_a, pixel_mm, win_w_mm, win_h_mm, step_mm,
                            common_periods)
    print(f"  Score: min={sa.min():.3f}, max={sa.max():.3f}, "
          f"median={np.median(sa):.3f}")

    print(f"Sweeping {label_b}...")
    tb, sb, _, _ = sweep(arr_b, pixel_mm, win_w_mm, win_h_mm, step_mm,
                          common_periods)
    print(f"  Score: min={sb.min():.3f}, max={sb.max():.3f}, "
          f"median={np.median(sb):.3f}")

    diff = sa - sb
    print(f"\nDifference (A - B):")
    print(f"  min={diff.min():.3f}, max={diff.max():.3f}, "
          f"median={np.median(diff):.3f}")
    print(f"  Windows where A > B: {(diff > 0).sum()} "
          f"({100 * (diff > 0).sum() / diff.size:.1f}%)")
    print(f"  Windows where B > A: {(diff < 0).sum()} "
          f"({100 * (diff < 0).sum() / diff.size:.1f}%)")

    sa_norm = sa / (np.percentile(sa, 95) + 1e-9)
    sb_norm = sb / (np.percentile(sb, 95) + 1e-9)
    consensus = np.minimum(sa_norm, sb_norm)

    # Figures
    H_mm = arr_a.shape[0] * pixel_mm
    W_mm = arr_a.shape[1] * pixel_mm
    extent_img = [0, W_mm, H_mm, 0]
    extent_map = [xs[0] * pixel_mm, xs[-1] * pixel_mm,
                  ys[-1] * pixel_mm, ys[0] * pixel_mm]

    # Originals
    fig, axes = plt.subplots(2, 1, figsize=(15, 7))
    axes[0].imshow(arr_a, cmap='gray_r', aspect='auto', extent=extent_img)
    axes[0].set_title(f'A: {label_a}')
    axes[0].set_xlabel('X [mm]'); axes[0].set_ylabel('Y [mm]')
    axes[1].imshow(arr_b, cmap='gray_r', aspect='auto', extent=extent_img)
    axes[1].set_title(f'B: {label_b}')
    axes[1].set_xlabel('X [mm]'); axes[1].set_ylabel('Y [mm]')
    plt.tight_layout()
    plt.savefig('comp_originals.png', dpi=130, bbox_inches='tight')
    print(f"\nSaved: comp_originals.png")

    # Scores
    vmax = max(np.percentile(sa, 99), np.percentile(sb, 99))
    fig, axes = plt.subplots(2, 1, figsize=(15, 7))
    im1 = axes[0].imshow(sa, cmap='viridis', aspect='auto', extent=extent_map,
                          vmin=0, vmax=vmax)
    axes[0].set_title(f'Topological score of {label_a}')
    axes[0].set_xlabel('X [mm]'); axes[0].set_ylabel('Y [mm]')
    plt.colorbar(im1, ax=axes[0], label='Score (prominence)')
    im2 = axes[1].imshow(sb, cmap='viridis', aspect='auto', extent=extent_map,
                          vmin=0, vmax=vmax)
    axes[1].set_title(f'Topological score of {label_b}')
    axes[1].set_xlabel('X [mm]'); axes[1].set_ylabel('Y [mm]')
    plt.colorbar(im2, ax=axes[1], label='Score (prominence)')
    plt.tight_layout()
    plt.savefig('comp_scores.png', dpi=130, bbox_inches='tight')
    print(f"Saved: comp_scores.png")

    # Consensus + difference
    fig, axes = plt.subplots(2, 1, figsize=(15, 7))
    im1 = axes[0].imshow(consensus, cmap='Greens', aspect='auto',
                          extent=extent_map, vmin=0, vmax=1)
    axes[0].set_title('Consensus: zones where both models detect clear structure')
    axes[0].set_xlabel('X [mm]'); axes[0].set_ylabel('Y [mm]')
    plt.colorbar(im1, ax=axes[0], label='Score min(A, B) normalized')

    im2 = axes[1].imshow(diff, cmap='RdBu_r', aspect='auto', extent=extent_map,
                          vmin=-vmax / 2, vmax=vmax / 2)
    axes[1].set_title(f'Difference A - B: red=A more structure, '
                      f'blue=B more structure')
    axes[1].set_xlabel('X [mm]'); axes[1].set_ylabel('Y [mm]')
    plt.colorbar(im2, ax=axes[1], label='Score difference')
    plt.tight_layout()
    plt.savefig('comp_diff.png', dpi=130, bbox_inches='tight')
    print(f"Saved: comp_diff.png")


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Compare two rendered surfaces via topological grid analysis.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('image_a', help='First image (e.g. version A)')
    parser.add_argument('image_b', help='Second image (e.g. version B)')
    parser.add_argument('--label-a', default='Version A',
                        help='Label for the first image')
    parser.add_argument('--label-b', default='Version B',
                        help='Label for the second image')
    parser.add_argument('--pixel-size', type=float, default=7.91,
                        help='Pixel size in micrometers')
    parser.add_argument('--downsample', type=int, default=2,
                        help='Downsampling factor')
    parser.add_argument('--window-w', type=float, default=30.0,
                        help='Window width in mm')
    parser.add_argument('--window-h', type=float, default=8.0,
                        help='Window height in mm')
    parser.add_argument('--step', type=float, default=3.0,
                        help='Step between windows in mm')
    args = parser.parse_args()

    compare(args.image_a, args.image_b,
            args.label_a, args.label_b,
            args.pixel_size, args.downsample,
            args.window_w, args.window_h, args.step)


if __name__ == '__main__':
    main()
