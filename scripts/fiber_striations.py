#!/usr/bin/env python3
"""Fiber striations of the papyrus, measured in the CT of the closed scroll.

Scroll 1 (PHerc. Paris 4), GP segment 20230702185753, 2.4 um surface volume.
Consolidates the verified notebook chain of 2026-08-17 into one reproducible
script. Runs on Colab or any machine with: pip install zarr s3fs tifffile
(data: anonymous S3, bucket vesuvius-challenge-open-data).

WHAT IT MEASURES
  A periodic intensity pattern in the papyrus material, fundamental period
  ~4.2-4.7 mm (first harmonic 8.3-9.3 mm), present on both faces with
  crossed orientations (height on the recto face, arc on the verso face) --
  the fiber striation papyrologists use for fiber matching on fragments,
  here seen inside the rolled scroll.

CONTROLS (all three run below; expected outcomes from the verified run)
  1. Depth: the pattern STRENGTHENS away from the inked surface
     (quarter-depth ~205x background, core ~155x, verso ~203x) -> not ink.
  2. Text stratification: STRONGER between text columns (~1162x) than
     under text (~731x) -> not writing.
  3. Geometry: the surface undulates at OTHER periods (~20 mm along arc,
     ~10 mm in height = crush corrugation of the near-core windings,
     itself a measurement) while at 2-5 mm it is smooth -> not crumpling.
  Also excluded: render tiling (dominant peak ~65 px, not 128).

STATED LIMIT
  At this render resolution (~67 um/px grid) the striation is visible in
  aggregate spectra but not traceable block-to-block (baseline continuity
  0.27-0.33 across three estimators incl. best-lag alignment; synthetic
  benches with noise, drift and shear all keep >=0.85, so the limit is
  coherence at this sampling, not the estimator). Fiber-to-fiber tracing
  -- and join detection from striation breaks -- needs the 1.129 um data.
"""
import io, json
import numpy as np
import s3fs, zarr, tifffile

BUCKET = "vesuvius-challenge-open-data"
SEG = "PHercParis4/segments/20230702185753"
P4 = f"{BUCKET}/{SEG}"
SV = f"{P4}/surface-volumes/2.4um-0.22m-78keV-volume-20260411134726.zarr"
MESH = f"{P4}/mesh/20230702185753-on-20260411134726-2.4um.tifxyz"
INKMAP = (f"{P4}/ink-detection/downsampled/"
          "PHercParis4-20230702185753-2.4um-0.22m-78keV-volume-20260411134726-"
          "20260417190342-new_canon_autoresearch_recipe-tile256-stride128-ds8.jpg")

fs = s3fs.S3FileSystem(anon=True)
sv3 = zarr.open(s3fs.S3Map(SV, s3=fs), mode="r")["3"]
print("volume:", sv3.shape)

def _tif(path):
    return tifffile.imread(io.BytesIO(fs.cat(path))).astype(np.float32)
X, Y, Z = (_tif(f"{MESH}/{a}.tif") for a in "xyz")
valid = np.isfinite(X) & np.isfinite(Y) & np.isfinite(Z) & (X > 0) & (Y > 0)
h, w = X.shape

# orientation: make axis 1 the arc
cx, cy = np.median(X[valid]), np.median(Y[valid])
TH = np.degrees(np.arctan2(Y - cy, X - cx)); TH[~valid] = np.nan
def _span(v):
    v = v[np.isfinite(v)]
    return 0.0 if v.size < 50 else float(np.degrees(np.ptp(np.unwrap(np.radians(v)))))
s_rows = np.median([_span(TH[r]) for r in range(h//4, 3*h//4, max(1, h//10))])
s_cols = np.median([_span(TH[:, c]) for c in range(w//4, 3*w//4, max(1, w//10))])
TRANSP = s_cols > s_rows
if TRANSP:
    X, Y, Z, valid = X.T, Y.T, Z.T, valid.T
    h, w = X.shape
print(f"arc span: {max(s_rows, s_cols):.0f} deg, grid {h}x{w}")

fila, col = h//2, w//2
du = np.nanmedian(np.abs(np.diff(X[fila])) + np.abs(np.diff(Y[fila])) + np.abs(np.diff(Z[fila])))
dv = np.nanmedian(np.abs(np.diff(X[:, col])) + np.abs(np.diff(Y[:, col])) + np.abs(np.diff(Z[:, col])))
mm_u, mm_v = du*2.4/1000, dv*2.4/1000
print(f"scale (L1 estimate): {mm_u:.3f} mm/px arc, {mm_v:.3f} mm/px height")

def capa(k):
    a = np.asarray(sv3[k])
    if TRANSP: a = a.T
    return a[np.linspace(0, a.shape[0]-1, h).astype(int)][:,
             np.linspace(0, a.shape[1]-1, w).astype(int)].astype(np.float32)

def spectrum(profile, step_mm, lo_mm=2.0, hi_mm=30.0):
    p = profile[np.isfinite(profile)]
    p = p - np.convolve(p, np.ones(101)/101, "same")
    f = np.fft.rfftfreq(len(p), d=step_mm)
    P = np.abs(np.fft.rfft(p*np.hanning(len(p))))**2
    band = (f > 1/hi_mm) & (f < 1/lo_mm)
    bg = (f > 1/60) & (f < 1/40)
    peak_mm = 1/f[band][np.argmax(P[band])]
    snr = float(P[band].max()/np.median(P[bg]))
    return round(float(peak_mm), 2), round(snr, 1)

out = {"segment": SEG, "grid": [int(h), int(w)],
       "scale_mm_per_px": [round(float(mm_u), 4), round(float(mm_v), 4)],
       "depth_profile_height": {}, "arc_verso": {}, "text_strata": {},
       "geometry": {}}

print("\n[1] depth control -- height-axis spectrum by layer")
for k, name in [(15, "recto_surface"), (35, "quarter"), (54, "core"),
                (75, "three_quarter"), (93, "verso_surface")]:
    m = np.where(valid, capa(k), np.nan)
    pk, snr = spectrum(np.nanmedian(m, axis=1), mm_v)
    out["depth_profile_height"][name] = [pk, snr]
    print(f"  layer {k:3d} {name:14s}: {pk} mm, {snr}x")
for k, name in [(93, "verso_surface"), (54, "core")]:
    m = np.where(valid, capa(k), np.nan)
    pk, snr = spectrum(np.nanmedian(m, axis=0), mm_u)
    out["arc_verso"][name] = [pk, snr]
    print(f"  layer {k:3d} {name:14s} (arc): {pk} mm, {snr}x")

print("\n[2] text control -- core layer, with/without text columns")
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
ink = np.asarray(Image.open(io.BytesIO(fs.cat(INKMAP))).convert("L")).astype(np.float32)
if TRANSP: ink = ink.T
INK = ink[np.linspace(0, ink.shape[0]-1, h).astype(int)][:,
          np.linspace(0, ink.shape[1]-1, w).astype(int)]
tinta_u = np.nanmean(np.where(valid, INK, np.nan), axis=0)
con = tinta_u > np.nanpercentile(tinta_u, 60)
sin = tinta_u < np.nanpercentile(tinta_u, 25)
core = np.where(valid, capa(54), np.nan)
pk1, s1 = spectrum(np.nanmedian(core[:, con], axis=1), mm_v)
pk2, s2 = spectrum(np.nanmedian(core[:, sin], axis=1), mm_v)
out["text_strata"] = {"under_text": [pk1, s1, int(con.sum())],
                      "between_columns": [pk2, s2, int(sin.sum())]}
print(f"  under text      : {pk1} mm, {s1}x  ({int(con.sum())} arc px)")
print(f"  between columns : {pk2} mm, {s2}x  ({int(sin.sum())} arc px)")

print("\n[3] geometry control -- surface radius vs core intensity")
R = np.where(valid, np.hypot(X - np.median(X[valid]), Y - np.median(Y[valid])), np.nan)
for prof, step, name in [(np.nanmedian(R, axis=0), mm_u, "geometry_arc"),
                         (np.nanmedian(R, axis=1), mm_v, "geometry_height"),
                         (np.nanmedian(core, axis=0), mm_u, "intensity_arc"),
                         (np.nanmedian(core, axis=1), mm_v, "intensity_height")]:
    pk, snr = spectrum(prof, step)
    out["geometry"][name] = [pk, snr]
    print(f"  {name:16s}: {pk} mm, {snr}x")

json.dump(out, open("fiber_striations_results.json", "w"), indent=1)
print("\nsaved fiber_striations_results.json")
