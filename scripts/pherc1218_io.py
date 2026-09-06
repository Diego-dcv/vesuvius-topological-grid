#!/usr/bin/env python3
"""
pherc1218_io.py -- ONE loader for every PHerc. 1218 script in this repository.

Every mode-15..19 script used to be a Colab cell that assumed four names
already existed in the notebook: `rows`, `zs`, `zpos` (the crossing table)
and `vol` (the CT volume). No file in the repo defined them, so the scripts
could not run outside that notebook. This module is that missing step.

Usage, in a script or a Colab cell (one line):

    from pherc1218_io import load_all; globals().update(load_all())

That defines rows, zs, zpos, dz_mm, origins, VOX, DX, DY and (if ct=True)
vol -- exactly the names the existing cells expect -- and nothing else
changes. Or pick what you need:

    from pherc1218_io import load_table, load_origins, open_ct
    rows, zs, zpos, dz_mm = load_table()
    origins = load_origins(zs, toward_ct=True)
    vol = open_ct(level=1)

Data provenance (see README, mode 16): the crossing table and per-slice
origins are Jinhojeong's run of iyando's convention, published at
  github.com/Jinhojeong/vesuvius-surface-geometry-diagnostic/results/kollesis/
Downloads are cached locally (Drive folder on Colab, ./cache_1218 elsewhere),
so the 10 MB table is fetched once.

Frame conventions carried here so no script has to restate them:
  * VOX = 0.01728 mm per level-1 voxel (2 x 8.64 um).
  * x = cx + r*cos(theta), y = cy + r*sin(theta); theta = 0 is +x.
  * origins_merged.csv has columns z, cy, cx (in THAT order); this loader
    reads them by name, never by position.
  * Offset (DX, DY) = (-3, -1) voxels applies ONLY when sampling the raw CT;
    the labels are in frame (0, 0). `load_origins(toward_ct=True)` adds it.
  * Duplicate origin rows for one z are averaged; z planes present in the
    table but absent from origins take the nearest available origin.

Self-check: `python pherc1218_io.py` downloads (or reads the cache), prints
the census and compares it with the numbers stated in the README.
"""
import csv
import gzip
import io
import os
import sys
import time
import urllib.request

import numpy as np

# ---- constants (single source of truth) ---------------------------------
VOX = 0.01728                 # mm per level-1 voxel
DX, DY = -3, -1               # label frame -> raw-CT frame, voxels
NRAYS = 60                    # theta step 6 deg
RAW = ("https://raw.githubusercontent.com/Jinhojeong/"
       "vesuvius-surface-geometry-diagnostic/main/results/kollesis/")
TABLE = "positions_merged.csv.gz"
ORIGINS = "origins_merged.csv"
BUCKET = "vesuvius-challenge-open-data"
VOLUME = (BUCKET + "/PHerc1218/volumes/"
          "20250521120456-8.640um-1.2m-116keV-masked.zarr")

# numbers the README states for this table; the self-check compares to them
EXPECTED = dict(rows=1_404_796, planes=323, rays=60, z_step=32,
                dz_mm=0.553)


# ---- cache location ------------------------------------------------------
def cache_dir():
    """Drive folder on Colab (survives kernel restarts), ./cache_1218 else."""
    drive = "/content/drive/MyDrive/vesuvius_1218"
    if os.path.isdir("/content/drive/MyDrive"):
        os.makedirs(drive, exist_ok=True)
        return drive
    d = os.path.join(os.getcwd(), "cache_1218")
    os.makedirs(d, exist_ok=True)
    return d


def _fetch(name, quiet=False):
    """Return local path of `name`, downloading from RAW on first use."""
    path = os.path.join(cache_dir(), name)
    if not os.path.exists(path):
        if not quiet:
            print(f"[pherc1218_io] downloading {name} ...", end="", flush=True)
        t0 = time.time()
        urllib.request.urlretrieve(RAW + name, path)
        if not quiet:
            print(f" {os.path.getsize(path)/1e6:.1f} MB in {time.time()-t0:.0f} s")
    return path


# ---- crossing table ------------------------------------------------------
def load_table(quiet=False):
    """rows (list of dict, same keys as the CSV), zs, zpos, dz_mm."""
    path = _fetch(TABLE, quiet)
    with gzip.open(path, "rt", newline="") as f:
        rows = list(csv.DictReader(f))
    zs = sorted({int(r["z"]) for r in rows})
    zpos = {z: i for i, z in enumerate(zs)}
    dz_mm = float(np.median(np.diff(zs))) * VOX
    if not quiet:
        print(f"[pherc1218_io] table: {len(rows):,} crossings, "
              f"{len(zs)} planes z={zs[0]}..{zs[-1]}, dz={dz_mm:.3f} mm")
    return rows, zs, zpos, dz_mm


def table_array(rows):
    """Same table as a numeric array (z, theta_deg, k, r_vox): faster code."""
    return np.array([(int(r["z"]), float(r["theta_deg"]), int(r["k"]),
                      float(r["r_l1_vox"])) for r in rows], np.float64)


# ---- origins -------------------------------------------------------------
def load_origins(zs=None, toward_ct=False, quiet=False):
    """dict z -> (cx, cy) in voxels. toward_ct=True adds (DX, DY)."""
    path = _fetch(ORIGINS, quiet)
    acc = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            z = int(float(row["z"]))
            acc.setdefault(z, []).append((float(row["cx"]), float(row["cy"])))
    ox, oy = (DX, DY) if toward_ct else (0, 0)
    org = {z: (float(np.mean([p[0] for p in v])) + ox,
               float(np.mean([p[1] for p in v])) + oy) for z, v in acc.items()}
    if zs is not None:
        have = sorted(org)
        for z in zs:
            if z not in org:
                org[z] = org[min(have, key=lambda q: abs(q - z))]
    if not quiet:
        ndup = sum(len(v) > 1 for v in acc.values())
        print(f"[pherc1218_io] origins: {len(acc)} planes "
              f"({ndup} averaged duplicates), frame "
              f"{'CT (offset applied)' if toward_ct else 'labels'}")
    return org


# ---- raw CT (optional; needs zarr + s3fs) --------------------------------
def open_ct(level=1, quiet=False):
    """Open the masked PHerc1218 volume on the public S3 bucket, read-only.
    level 1 = 17.28 um/voxel (the resolution every 1218 mode uses)."""
    try:
        import s3fs
        import zarr
    except ImportError:
        sys.exit("[pherc1218_io] raw CT needs: pip install zarr s3fs")
    fs = s3fs.S3FileSystem(anon=True)
    root = zarr.open(s3fs.S3Map(VOLUME, s3=fs), mode="r")
    vol = root[str(level)]
    if not quiet:
        print(f"[pherc1218_io] CT level {level}: shape {vol.shape}, "
              f"dtype {vol.dtype}")
    return vol


# ---- one call for the Colab cells ---------------------------------------
def load_all(ct=False, quiet=False):
    """Everything the mode-15..19 cells expect, as a dict for globals()."""
    rows, zs, zpos, dz_mm = load_table(quiet)
    out = dict(rows=rows, zs=zs, zpos=zpos, dz_mm=dz_mm,
               origins=load_origins(zs, toward_ct=False, quiet=quiet),
               origins_ct=load_origins(zs, toward_ct=True, quiet=True),
               VOX=VOX, DX=DX, DY=DY)
    if ct:
        out["vol"] = open_ct(1, quiet)
    return out


# ---- self-check ----------------------------------------------------------
def self_check():
    print("=" * 66)
    print("SELF-CHECK -- pherc1218_io (compares with README, mode 16)")
    print("=" * 66)
    rows, zs, zpos, dz_mm = load_table()
    org = load_origins(zs)
    rays = len({float(r["theta_deg"]) for r in rows})
    step = int(np.median(np.diff(zs)))
    checks = [
        ("crossings", len(rows), EXPECTED["rows"]),
        ("z planes", len(zs), EXPECTED["planes"]),
        ("rays", rays, EXPECTED["rays"]),
        ("z step (vox)", step, EXPECTED["z_step"]),
        ("dz (mm)", round(dz_mm, 3), EXPECTED["dz_mm"]),
        ("origins cover all planes", all(z in org for z in zs), True),
    ]
    ok = True
    for name, got, exp in checks:
        good = got == exp
        ok &= good
        print(f"{name:26s} {got!s:>12}  expected {exp!s:<10} "
              f"-> {'PASS' if good else 'FAIL'}")
    kmax = max(int(r["k"]) for r in rows)
    print(f"{'max crossing ordinal k':26s} {kmax:>12}  (README: table reaches "
          f"k=108)")
    print("-" * 66)
    print("OVERALL:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(0 if self_check() else 1)
