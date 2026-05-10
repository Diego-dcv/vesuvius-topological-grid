"""
analyze_grid.py — Global topological grid analysis on a single rendered surface.

Computes the Fourier signature of the ink projections along the X and Y axes,
detects the three dominant spatial periods (lines, letters, columns) without
assuming predefined values, and produces six diagnostic figures plus a 2D FFT.

Usage:
    python analyze_grid.py path/to/rendered_surface.png
    python analyze_grid.py path/to/rendered_surface.png --pixel-size 7.91
    python analyze_grid.py path/to/rendered_surface.png --downsample 2

Output:
    analysis_fourier.png  — six-panel diagnostic figure
    fft2d.png             — 2D FFT showing the grid cross
    Console: detected periods and prominence values

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
    """Load an image as a 2D float array in [0, 1], with ink as high values."""
    if not os.path.exists(path):
        sys.exit(f"ERROR: file not found: {path}")
    img = Image.open(path).convert('L')
    if downsample > 1:
        w, h = img.size
        img = img.resize((w // downsample, h // downsample), Image.LANCZOS)
    arr = np.array(img, dtype=np.float32) / 255.0
    # If background is bright and ink is dark, invert so ink = high
    if arr.mean() > 0.5:
        arr = 1.0 - arr
        print("  (inverted: dark ink on light background)")
    return arr


# ----------------------------------------------------------------------------
# Spectral analysis
# ----------------------------------------------------------------------------

def spectrum(signal, pixel_mm):
    """Power spectrum of a 1D signal. Returns (periods_mm, amplitudes)."""
    s = signal - gaussian_filter1d(signal, sigma=len(signal) / 20)
    s = s * np.hanning(len(s))
    fft = np.abs(np.fft.rfft(s))
    freq = np.fft.rfftfreq(len(s), d=pixel_mm)
    with np.errstate(divide='ignore'):
        periods = np.where(freq > 0, 1.0 / freq, np.inf)
    return periods, fft


def find_peak_in_range(periods, amp, p_min, p_max):
    """Find the highest-amplitude peak whose period is in [p_min, p_max] mm."""
    mask = (periods >= p_min) & (periods <= p_max)
    if not mask.any():
        return None
    idx = np.where(mask)[0][np.argmax(amp[mask])]
    period_at_peak = periods[idx]
    amp_at_peak = amp[idx]
    background = np.median(amp[mask])
    prominence = amp_at_peak / background if background > 0 else float('inf')
    return period_at_peak, amp_at_peak, prominence


# ----------------------------------------------------------------------------
# Main analysis
# ----------------------------------------------------------------------------

def analyze(image_path, pixel_size_um, downsample):
    pixel_mm = pixel_size_um * downsample / 1000.0
    print(f"Effective resolution: {pixel_mm * 1000:.2f} um/pixel "
          f"= {pixel_mm:.4f} mm/pixel")

    arr = load_image(image_path, downsample)
    print(f"Image: {arr.shape[1]} x {arr.shape[0]} pixels = "
          f"{arr.shape[1] * pixel_mm:.0f} x {arr.shape[0] * pixel_mm:.0f} mm")

    pY = arr.sum(axis=1)
    pX = arr.sum(axis=0)

    per_y, amp_y = spectrum(pY, pixel_mm)
    per_x, amp_x = spectrum(pX, pixel_mm)

    # Search ranges (broad, not asserting specific values for any tradition)
    line_range = (3.5, 7.0)        # text lines (Y)
    letter_range = (2.0, 4.5)      # individual letters (X)
    column_range = (8.0, 30.0)     # column + intercolumnium (X)

    print("\n" + "=" * 70)
    print("DETECTED PEAKS")
    print("=" * 70)

    print("\nIn Y projection (along the scroll axis):")
    res = find_peak_in_range(per_y, amp_y, *line_range)
    if res:
        period, _, prom = res
        print(f"  Text lines ({line_range[0]}-{line_range[1]} mm):  "
              f"period = {period:.2f} mm, prominence = {prom:.1f}x")

    print("\nIn X projection (perpendicular to the axis):")
    for label, rng in [('Individual letters', letter_range),
                       ('Column + intercolumnium', column_range)]:
        res = find_peak_in_range(per_x, amp_x, *rng)
        if res:
            period, _, prom = res
            print(f"  {label} ({rng[0]}-{rng[1]} mm):  "
                  f"period = {period:.2f} mm, prominence = {prom:.1f}x")

    # Six-panel figure
    fig, axes = plt.subplots(3, 2, figsize=(14, 12))

    ax = axes[0, 0]
    ax.imshow(arr, cmap='gray_r', aspect='auto',
              extent=[0, arr.shape[1] * pixel_mm,
                      arr.shape[0] * pixel_mm, 0])
    ax.set_title(f'Rendered surface (dark = ink)\n'
                 f'{arr.shape[1] * pixel_mm:.0f} x {arr.shape[0] * pixel_mm:.0f} mm')
    ax.set_xlabel('X [mm]'); ax.set_ylabel('Y [mm]')

    ax = axes[0, 1]
    ax.imshow(arr, cmap='inferno', aspect='auto',
              extent=[0, arr.shape[1] * pixel_mm,
                      arr.shape[0] * pixel_mm, 0])
    ax.set_title('Same image, heat map')
    ax.set_xlabel('X [mm]'); ax.set_ylabel('Y [mm]')

    ax = axes[1, 0]
    y_mm = np.arange(len(pY)) * pixel_mm
    ax.plot(y_mm, pY, lw=0.7)
    ax.set_title('Y projection: ink summed by row\n(peaks = text lines)')
    ax.set_xlabel('Y [mm]'); ax.set_ylabel('Accumulated ink')
    ax.grid(alpha=0.3)

    ax = axes[1, 1]
    mask = (per_y > 1) & (per_y < 50)
    ax.plot(per_y[mask], amp_y[mask], lw=0.8)
    ax.axvspan(*line_range, color='green', alpha=0.18,
               label=f'expected lines: {line_range[0]}-{line_range[1]} mm')
    res = find_peak_in_range(per_y, amp_y, *line_range)
    if res:
        ax.axvline(res[0], color='red', ls='--', lw=1,
                   label=f'detected: {res[0]:.2f} mm')
    ax.set_xscale('log')
    ax.set_title('Spectrum of Y projection')
    ax.set_xlabel('Period [mm]'); ax.set_ylabel('Amplitude')
    ax.legend(fontsize=8); ax.grid(alpha=0.3, which='both')

    ax = axes[2, 0]
    x_mm = np.arange(len(pX)) * pixel_mm
    ax.plot(x_mm, pX, lw=0.7)
    ax.set_title('X projection: ink summed by column\n'
                 '(fine peaks = letters; wider blocks = columns)')
    ax.set_xlabel('X [mm]'); ax.set_ylabel('Accumulated ink')
    ax.grid(alpha=0.3)

    ax = axes[2, 1]
    mask = (per_x > 1) & (per_x < 200)
    ax.plot(per_x[mask], amp_x[mask], lw=0.8)
    ax.axvspan(*letter_range, color='blue', alpha=0.18,
               label=f'letters: {letter_range[0]}-{letter_range[1]} mm')
    ax.axvspan(*column_range, color='orange', alpha=0.18,
               label=f'columns: {column_range[0]}-{column_range[1]} mm')
    for name, rng, color in [('letters', letter_range, 'red'),
                              ('column', column_range, 'darkred')]:
        res = find_peak_in_range(per_x, amp_x, *rng)
        if res:
            ax.axvline(res[0], color=color, ls='--', lw=1,
                       label=f'{name}: {res[0]:.2f} mm')
    ax.set_xscale('log')
    ax.set_title('Spectrum of X projection')
    ax.set_xlabel('Period [mm]'); ax.set_ylabel('Amplitude')
    ax.legend(fontsize=8); ax.grid(alpha=0.3, which='both')

    plt.tight_layout()
    plt.savefig('analysis_fourier.png', dpi=130, bbox_inches='tight')
    print(f"\nSaved: analysis_fourier.png")

    # 2D FFT
    fig2, ax = plt.subplots(figsize=(8, 6))
    fft2 = np.fft.fftshift(np.abs(np.fft.fft2(arr - arr.mean())))
    h, w = fft2.shape
    crop = 80
    center = fft2[h // 2 - crop:h // 2 + crop,
                  w // 2 - crop:w // 2 + crop]
    ax.imshow(np.log1p(center), cmap='magma',
              extent=[-crop, crop, -crop, crop])
    ax.set_title('2D FFT (log) — central zone\n'
                 'horizontal/vertical cross = regular text grid')
    ax.set_xlabel('X frequency [bins]')
    ax.set_ylabel('Y frequency [bins]')
    plt.savefig('fft2d.png', dpi=130, bbox_inches='tight')
    print(f"Saved: fft2d.png")


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Global topological grid analysis on a rendered surface.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('image', help='Path to the rendered surface image '
                                       '(PNG, JPG, WEBP, etc.)')
    parser.add_argument('--pixel-size', type=float, default=7.91,
                        help='Pixel size in micrometers')
    parser.add_argument('--downsample', type=int, default=2,
                        help='Downsampling factor (1=no downsample, '
                             '2=half size, 4=quarter)')
    args = parser.parse_args()
    analyze(args.image, args.pixel_size, args.downsample)


if __name__ == '__main__':
    main()
