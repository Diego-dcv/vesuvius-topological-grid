"""Cross-scroll check of mode 15 on PHerc. 1218 (raw CT, 17 um voxels).

Measures, on the 1218 masked volume plus the public ray/ring geometry:
  1. coarse-band vertical spectrum of sheet-following intensity profiles
     (2-6 mm, where the Paris 4 striation lives) with a shuffled null;
  2. geometric crush corrugation: sheet radii along height
     -> RESULT: 19.8 mm vertical period, ~10x background, 3,363 sheets;
  3. fine-band texture (0.1-1.2 mm) in dense vertical columns of one
     subvolume, two ways: straight columns AND crest-following tracking
     with a matched shuffled null (the "sponge check": absence must be
     the material's, not the sectioning's).

Recorded run (18-19 Aug 2026, Google Colab):
  sanity 88% of samples in material (2,918 profiles)
  coarse band: peak 4.96 mm at z = -12.5 vs shuffled null  -> empty band
  corrugation: 19.8 mm, 10.2x background, 3,363 sheets     -> MEASURED
  fine band straight: 0.7x background (4,025 columns)      -> nothing
  fine band crest:    0.7x vs matched null 1.0x (1,389)    -> nothing

Deps: numpy zarr s3fs (pip install zarr s3fs). Anonymous S3; no keys.
Runtime ~45 min total, dominated by slice reads. Ray/ring geometry:
Jinhojeong/vesuvius-surface-geometry-diagnostic (results/kollesis).
"""

import csv, gzip, io, time, urllib.request

import numpy as np
import s3fs, zarr

BUCKET = "vesuvius-challenge-open-data"
VOL = (BUCKET + "/PHerc1218/volumes/"
       "20250521120456-8.640um-1.2m-116keV-masked.zarr")
RAW = ("https://raw.githubusercontent.com/Jinhojeong/"
       "vesuvius-surface-geometry-diagnostic/main/results/kollesis/")
MM = 0.01728          # mm per level-1 voxel
MAT = 50              # intensity threshold: material vs air


def load_geometry():
    org = {}
    with urllib.request.urlopen(RAW + "origins_merged.csv") as r:
        for row in csv.DictReader(io.TextIOWrapper(r)):
            v = list(row.values())
            org[int(float(v[0]))] = (float(v[1]), float(v[2]))
    with urllib.request.urlopen(RAW + "positions_merged.csv.gz") as r:
        rows = list(csv.DictReader(
            io.StringIO(gzip.decompress(r.read()).decode())))
    porz = {}
    for r_ in rows:
        porz.setdefault(int(r_["z"]), []).append(
            (float(r_["theta_deg"]), int(r_["k"]), float(r_["r_l1_vox"])))
    zs = sorted(porz)
    return org, porz, zs


def sample_profiles(arr1, org, porz, zs):
    """One intensity profile per (ray, ring): patch mean at the local
    radial maximum (+-1.5 vox), following the sheet height by height."""
    claves = sorted({(th, k) for z in zs for th, k, rv in porz[z]})
    idx = {c: i for i, c in enumerate(claves)}
    PER = np.full((len(claves), len(zs)), np.nan, np.float32)
    t0 = time.time(); hit = 0; tot = 0
    for iz, z in enumerate(zs):
        sl = np.asarray(arr1[z]); ox, oy = org[z]
        H, W = sl.shape
        for th, k, rv in porz[z]:
            a = np.radians(th)
            best, bx, by = 0.0, -1, -1
            for dr in (-1.5, 0.0, 1.5):
                x = ox + (rv + dr) * np.cos(a)
                y = oy + (rv + dr) * np.sin(a)
                xi, yi = int(round(x)), int(round(y))
                if 2 <= yi < H - 2 and 2 <= xi < W - 2:
                    v = float(sl[yi, xi])
                    if v > best:
                        best, bx, by = v, xi, yi
            if bx >= 0 and best > MAT:
                par = sl[by - 2:by + 3, bx - 2:bx + 3].astype(np.float32)
                mat = par[par > 30]
                PER[idx[(th, k)], iz] = (mat.mean() if mat.size >= 5
                                         else best)
                hit += 1
            tot += 1
        if (iz + 1) % 25 == 0:
            print(f"  {iz+1}/{len(zs)}  ({time.time()-t0:.0f} s)  "
                  f"material {100*hit/max(tot,1):.0f}%", flush=True)
    print(f"sanity: {100*hit/tot:.0f}% of samples in material")
    return PER, claves, idx


def band_spectrum(P, d, lo_mm, hi_mm, bg_lo, bg_hi, detrend, min_ok):
    n = P.shape[1]; f = np.fft.rfftfreq(n, d=d)
    acc = np.zeros(len(f)); m = 0
    for i in range(P.shape[0]):
        p = P[i]; ok = np.isfinite(p)
        if ok.sum() < min_ok:
            continue
        q = p.copy(); q[~ok] = np.nanmedian(p[ok])
        if detrend:
            q = q - np.convolve(q, np.ones(detrend) / detrend, "same")
        else:
            q = q - q.mean()
        acc += np.abs(np.fft.rfft(q * np.hanning(n))) ** 2; m += 1
    acc /= max(m, 1)
    band = (f > 1 / hi_mm) & (f < 1 / lo_mm)
    bg = (f > 1 / bg_hi) & (f < 1 / bg_lo)
    peak = 1 / f[band][np.argmax(acc[band])]
    snr = acc[band].max() / np.median(acc[bg])
    return peak, snr, m, acc, f, band, bg


def main():
    org, porz, zs = load_geometry()
    dz = float(np.median(np.diff(zs))) * MM
    print(f"geometry: {len(zs)} heights (step {dz:.2f} mm)")
    fs = s3fs.S3FileSystem(anon=True)
    zroot = zarr.open(s3fs.S3Map(VOL, s3=fs), mode="r")
    arr1 = zroot["1"]

    # 1) sheet-following profiles + coarse band vs shuffled null
    PER, claves, idx = sample_profiles(arr1, org, porz, zs)
    peak, snr, m, acc, f, band, _ = band_spectrum(
        PER, dz, 2.0, 6.0, 10.0, 25.0, 31, 250)
    rng = np.random.default_rng(0); nulls = []
    for _ in range(40):
        Ps = PER.copy()
        for i in range(Ps.shape[0]):
            ok = np.isfinite(Ps[i])
            v = Ps[i][ok]; rng.shuffle(v); Ps[i][ok] = v
        an = band_spectrum(Ps, dz, 2.0, 6.0, 10.0, 25.0, 31, 250)[3]
        nulls.append(np.max(np.where(band, an, 0)))
    zsc = (acc[band].max() - np.mean(nulls)) / np.std(nulls)
    print(f"coarse band ({m:,} profiles): peak {peak:.2f} mm, "
          f"z = {zsc:.1f} vs shuffled null")

    # 2) geometric corrugation: radii along z
    zpos = {z: i for i, z in enumerate(zs)}
    R = np.full((len(claves), len(zs)), np.nan, np.float32)
    for z in zs:
        for th, k, rv in porz[z]:
            R[idx[(th, k)], zpos[z]] = rv * MM
    pk, sn, mm_ = band_spectrum(R, dz, 4.0, 40.0, 50.0, 90.0, 41, 250)[:3]
    print(f"crush corrugation ({mm_:,} sheets): {pk:.1f} mm, "
          f"{sn:.1f}x background")

    # 3) fine band in one dense subvolume, straight AND crest-following
    zc = zs[len(zs) // 2]; ox, oy = org[zc]
    rr = sorted(rv for th, k, rv in porz[zc] if abs(th) < 1.0)
    x0 = int(ox + rr[len(rr) // 2]) - 128; y0 = int(oy) - 128
    sub = np.asarray(arr1[zc - 1000:zc + 1000,
                          y0:y0 + 256, x0:x0 + 256])
    occ = (sub > MAT).mean(axis=0)
    cols = np.argwhere(occ > 0.7)
    n = sub.shape[0]; f = np.fft.rfftfreq(n, d=MM)
    band = (f > 1 / 1.2) & (f < 1 / 0.1)
    bg = (f > 1 / 3.0) & (f < 1 / 1.5)
    for mode in ("straight", "crest"):
        rng = np.random.default_rng(1)
        acc = np.zeros(len(f)); accn = np.zeros(len(f)); m = 0
        sel = (cols[::max(1, len(cols) // 4000)] if mode == "straight"
               else cols[rng.choice(len(cols),
                                    min(3000, len(cols)), replace=False)])
        for (yy, xx) in sel:
            if mode == "straight":
                p = sub[:, yy, xx].astype(np.float32)
                ok = p > MAT
                if ok.mean() < 0.7:
                    continue
                p[~ok] = np.median(p[ok])
            else:                      # ride the sheet's local maximum
                if xx < 4 or xx > sub.shape[2] - 5:
                    continue
                p = np.empty(n, np.float32); cx = int(xx); alive = True
                for iz in range(n):
                    w = sub[iz, yy, max(cx - 3, 0):cx + 4].astype(
                        np.float32)
                    j = int(np.argmax(w)); cx = max(cx - 3, 0) + j
                    p[iz] = w[j]
                    if p[iz] <= 30:
                        alive = False; break
                if not alive:
                    continue
            q = p - np.convolve(p, np.ones(201) / 201, "same")
            acc += np.abs(np.fft.rfft(q * np.hanning(n))) ** 2
            rng.shuffle(q)
            accn += np.abs(np.fft.rfft(q * np.hanning(n))) ** 2
            m += 1
        acc /= max(m, 1); accn /= max(m, 1)
        s = acc[band].max() / np.median(acc[bg])
        sn = accn[band].max() / np.median(accn[bg])
        print(f"fine band, {mode} ({m:,} cols): {s:.1f}x background "
              f"(matched null {sn:.1f}x)")


if __name__ == "__main__":
    main()
