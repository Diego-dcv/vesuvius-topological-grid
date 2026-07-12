#!/usr/bin/env python3
"""
experiment_A_degradation.py  --  Negative validation of the spatial-coherence metric.

The repository claims that a correct unwrapping preserves the spatial periodicity of
writing (line/letter/column spacing) and that degradation destroys it, so the spectral
coherence score can rank surfaces. That claim is only a calibrated tool once we show the
score falls monotonically and reproducibly as a surface is progressively degraded in
controlled ways. This script does exactly that, at ZERO data cost: it runs on the public
Paris-4 rendered surfaces you already hold (or, with no input, on a synthetic text-like
lattice so the pipeline is testable out of the box).

For each degradation family (rotation, shear, sinusoidal warp, additive noise, patch
erasure) it sweeps intensity 0..1, scores each degraded version, averages over the
supplied ROIs, and plots score-vs-intensity. A monotone, reproducible fall validates the
metric; a flat or noisy curve exposes its failure modes -- either outcome is a result.

PLUG POINT: replace `coherence_score` with your repository's exact scorer to validate the
published metric itself (see --scorer note). The default scorer below is a faithful,
self-contained stand-in: peak prominence of the dominant periodic component in the
axis-projected intensity profile.

Deps: numpy, scipy, matplotlib, pillow.  Usage:
    python experiment_A_degradation.py --input /path/to/tiles [--pixel-um 3.24]
    python experiment_A_degradation.py            # synthetic self-test
Outputs: degradation_curves.png, degradation_scores.csv
"""
import argparse, glob, os, csv
import numpy as np
from scipy import ndimage

# ----------------------------- scorer -------------------------------------
def _profile_prominence(profile):
    """Prominence of the dominant non-DC peak in the power spectrum of a 1D profile.
    High for a clean periodic signal, low for noise/aperiodic content."""
    p = profile - profile.mean()
    if p.std() < 1e-9:
        return 0.0
    w = np.hanning(len(p))
    P = np.abs(np.fft.rfft(p * w))**2
    P[0] = 0.0                      # kill DC
    if P.max() <= 0:
        return 0.0
    peak = P.max()
    med = np.median(P[P > 0]) + 1e-12
    return float(np.log1p(peak / med))    # log peak-to-typical ratio

def coherence_score(img):
    """Self-contained spatial-coherence score in [0, inf).
    Aggregates periodic prominence perpendicular to lines (vertical projection) and
    along lines (horizontal projection). Replace with your repo scorer to validate it."""
    g = img.astype(np.float64)
    g = (g - g.mean()) / (g.std() + 1e-9)
    vert = g.mean(axis=1)           # profile along y -> line spacing
    horiz = g.mean(axis=0)          # profile along x -> letter/column spacing
    return 0.5 * (_profile_prominence(vert) + _profile_prominence(horiz))

# --------------------------- degradations ---------------------------------
def degrade_rotate(img, s):
    return ndimage.rotate(img, angle=10.0 * s, reshape=False, mode="reflect", order=1)

def degrade_shear(img, s):
    M = np.array([[1.0, 0.15 * s], [0.0, 1.0]])
    off = np.array([0.0, -0.15 * s * img.shape[0] / 2.0])
    return ndimage.affine_transform(img, M, offset=off, mode="reflect", order=1)

def degrade_warp(img, s):
    h, w = img.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    amp = 6.0 * s                                   # px
    xx2 = xx + amp * np.sin(2 * np.pi * yy / max(20.0, h / 4.0))
    return ndimage.map_coordinates(img, [yy, xx2], mode="reflect", order=1)

def degrade_noise(img, s, rng):
    sigma = 1.5 * s * (img.std() + 1e-9)
    return img + rng.normal(0.0, sigma, img.shape)

def degrade_erase(img, s, rng):
    out = img.copy()
    h, w = img.shape
    n_patches = int(round(30 * s))
    ph, pw = max(2, h // 12), max(2, w // 12)
    for _ in range(n_patches):
        y = rng.integers(0, max(1, h - ph)); x = rng.integers(0, max(1, w - pw))
        out[y:y+ph, x:x+pw] = img.mean()
    return out

FAMILIES = ["rotation", "shear", "warp", "noise", "erase"]

def apply(img, family, s, rng):
    if family == "rotation": return degrade_rotate(img, s)
    if family == "shear":    return degrade_shear(img, s)
    if family == "warp":     return degrade_warp(img, s)
    if family == "noise":    return degrade_noise(img, s, rng)
    if family == "erase":    return degrade_erase(img, s, rng)
    raise ValueError(family)

# --------------------------- data loading ---------------------------------
def load_tiles(input_dir, tile=256, max_tiles=6):
    from PIL import Image
    paths = []
    for ext in ("*.png", "*.tif", "*.tiff", "*.jpg", "*.jpeg"):
        paths += glob.glob(os.path.join(input_dir, ext))
    tiles = []
    for pth in sorted(paths)[:max_tiles]:
        im = np.asarray(Image.open(pth).convert("L"), dtype=np.float64)
        h, w = im.shape
        if h >= tile and w >= tile:
            y = (h - tile) // 2; x = (w - tile) // 2
            tiles.append(im[y:y+tile, x:x+tile])
        else:
            tiles.append(im)
    return tiles

def synthetic_text(tile=256, rng=None):
    """A crude but periodic 'writing' lattice: rows of blobs at fixed line/letter pitch."""
    rng = rng or np.random.default_rng(0)
    img = np.zeros((tile, tile))
    line_pitch, letter_pitch = 22, 14
    yy, xx = np.mgrid[0:tile, 0:tile]
    for ly in range(line_pitch // 2, tile, line_pitch):
        for lx in range(letter_pitch // 2, tile, letter_pitch):
            if rng.random() < 0.75:
                img += np.exp(-(((yy-ly)**2)/8.0 + ((xx-lx)**2)/6.0))
    img += 0.05 * rng.standard_normal((tile, tile))
    return img

# ------------------------------- main -------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=None, help="dir of rendered surface tiles")
    ap.add_argument("--pixel-um", type=float, default=None, help="pixel size (metadata only)")
    ap.add_argument("--levels", type=int, default=9)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)

    if args.input:
        tiles = load_tiles(args.input)
        src = f"{len(tiles)} tiles from {args.input}"
    else:
        tiles = [synthetic_text(rng=np.random.default_rng(k)) for k in range(5)]
        src = "synthetic self-test (5 tiles)"
    if not tiles:
        raise SystemExit("no tiles found")

    intensities = np.linspace(0.0, 1.0, args.levels)
    # baseline scores (undegraded)
    base = np.array([coherence_score(t) for t in tiles])
    results = {fam: np.zeros((len(tiles), len(intensities))) for fam in FAMILIES}
    for fi, fam in enumerate(FAMILIES):
        for ti, t in enumerate(tiles):
            for si, s in enumerate(intensities):
                deg = apply(t, fam, float(s), np.random.default_rng(1000 + ti))
                results[fam][ti, si] = coherence_score(deg)

    # normalise each tile's curve by its own baseline so tiles are comparable
    norm = {fam: results[fam] / (base[:, None] + 1e-9) for fam in FAMILIES}
    mean = {fam: norm[fam].mean(axis=0) for fam in FAMILIES}
    std = {fam: norm[fam].std(axis=0) for fam in FAMILIES}

    # monotonicity diagnostic: Spearman-like fraction of non-increasing steps
    def mono(curve):
        d = np.diff(curve)
        return float((d <= 1e-6).mean())

    with open("degradation_scores.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["family", "intensity", "mean_norm_score", "std", "monotone_frac"])
        for fam in FAMILIES:
            m = mono(mean[fam])
            for si, s in enumerate(intensities):
                w.writerow([fam, f"{s:.3f}", f"{mean[fam][si]:.4f}", f"{std[fam][si]:.4f}", f"{m:.2f}"])

    print(f"Experiment A -- {src}")
    print(f"{'family':<9} {'score@0':>8} {'score@1':>8} {'drop%':>7} {'monotone':>9}")
    for fam in FAMILIES:
        s0, s1 = mean[fam][0], mean[fam][-1]
        print(f"{fam:<9} {s0:8.3f} {s1:8.3f} {100*(1-s1/max(s0,1e-9)):7.1f} {mono(mean[fam]):9.2f}")

    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7.2, 4.4))
        for fam in FAMILIES:
            ax.plot(intensities, mean[fam], marker="o", ms=3, label=fam)
            ax.fill_between(intensities, mean[fam]-std[fam], mean[fam]+std[fam], alpha=0.12)
        ax.axhline(1.0, ls=":", c="grey", lw=0.8)
        ax.set_xlabel("degradation intensity"); ax.set_ylabel("coherence score (normalised to undegraded)")
        ax.set_title("Experiment A: coherence score vs controlled degradation")
        ax.legend(fontsize=8); ax.grid(alpha=0.3); fig.tight_layout()
        fig.savefig("degradation_curves.png", dpi=140)
        print("\nFigure written: degradation_curves.png")
    except Exception as e:
        print("figure step skipped:", e)

if __name__ == "__main__":
    main()
