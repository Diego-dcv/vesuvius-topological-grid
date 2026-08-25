#!/usr/bin/env python3
"""
route_a_winding_fullres.py
Per-point winding assignment for the full PHerc1218 pre-repair label tree
(npz blocks), restricted to the crossing table's 323 planes at full
in-plane resolution (~2e8 candidate voxels).

Method (same as the validated step-8 run): each labelled voxel is
bracketed between the crossing-table radii on its own ray (theta, z).
Accepted when |dr| <= 15 vox AND d1/(d1+d2) <= 0.45 (ambiguity relative
to the local gap). Prefixed criteria, from the step-8 run: assigned
fraction >= 0.60; median |dr| <= 3 vox (step-8 gave 85.8% and 2.61 vox).

Overlap rule: blocks visited in sorted order, first writer wins —
matching the exporter of the step-8 list (--block-order paths = plain
sorted() on the block paths; use --block-order zyx if the exporter
sorted numerically). Seam disagreement is measured on ALL overlap voxels
of the processed planes and reported next to the published 82.9%
agreement figure.

Outputs (all small; nothing 2e8-rows needs uploading):
  out/winding_maps_1218.npz     n / r_p10 / r_p90 / dr_med per
                                (winding, ray, plane) — r_p90-r_p10 is
                                the per-cell thickness proxy
  out/qa_instances_fullres.csv  instances whose assigned windings have a
                                gap >= 2 with >= 3 points per side
  out/summary.json              counts, exam verdicts, seam stats, params
  out/points_z*.npz             per-plane per-point (y,x,gid,k,dr) —
                                only with --save-points

Needs numpy only. RAM: ~6-8 GB peak. Runtime: dominated by decompressing
the tree once (~1-2 h single process).

Usage:
  python route_a_winding_fullres.py --tree /path/to/tree_root
      [--table URL_or_path.csv.gz] [--origins URL_or_path.csv]
      [--out route_a_out] [--block-order paths|zyx] [--save-points]
"""
import argparse, csv, glob, gzip, io, json, os, time, urllib.request
import numpy as np

RAW = ("https://raw.githubusercontent.com/Jinhojeong/"
       "vesuvius-surface-geometry-diagnostic/main/results/kollesis/")
TOL_ABS, TOL_FRAC = 15.0, 0.45


def read_bytes(path):
    if path.startswith("http"):
        return urllib.request.urlopen(path).read()
    with open(path, "rb") as f:
        return f.read()


def load_table(path):
    data = read_bytes(path)
    if path.endswith(".gz"):
        data = gzip.decompress(data)
    rows = list(csv.DictReader(io.StringIO(data.decode())))
    zs = sorted({int(r["z"]) for r in rows})
    zpos = {z: i for i, z in enumerate(zs)}
    kmax = max(int(r["k"]) for r in rows)
    Rg = np.full((kmax + 1, 60, len(zs)), np.nan, np.float32)
    for r in rows:
        Rg[int(r["k"]),
           int(round(float(r["theta_deg"]) / 6)) % 60,
           zpos[int(r["z"])]] = float(r["r_l1_vox"])
    return zs, zpos, Rg


def load_origins(path, zs):
    txt = read_bytes(path).decode()
    acc = {}
    for f_ in csv.DictReader(io.StringIO(txt)):
        z = int(float(f_["z"]))
        acc.setdefault(z, []).append((float(f_["cx"]), float(f_["cy"])))
    org = {z: (float(np.mean([p[0] for p in v])),
               float(np.mean([p[1] for p in v]))) for z, v in acc.items()}
    zo = sorted(org)
    return {z: org[z] if z in org
            else org[min(zo, key=lambda q: abs(q - z))] for z in zs}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True)
    ap.add_argument("--table", default=RAW + "positions_merged.csv.gz")
    ap.add_argument("--origins", default=RAW + "origins_merged.csv")
    ap.add_argument("--out", default="route_a_out")
    ap.add_argument("--block-order", choices=["paths", "zyx"],
                    default="paths")
    ap.add_argument("--save-points", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    t0 = time.time()

    zs, zpos, Rg = load_table(args.table)
    origins = load_origins(args.origins, zs)
    zs_arr = np.array(zs)
    nzp, nk = len(zs), Rg.shape[0]
    print(f"table: {np.isfinite(Rg).sum():,} crossings on {nzp} planes; "
          f"k up to {nk-1}")

    paths = sorted(glob.glob(os.path.join(args.tree, "blocks",
                                          "z*", "tile_*.npz")))
    assert paths, f"no blocks under {args.tree}"
    if args.block_order == "zyx":
        def zyx(p):
            with np.load(p) as q:
                return (int(q["z0"]), int(q["y0"]), int(q["x0"]))
        paths = sorted(paths, key=zyx)
    with open(os.path.join(args.tree, "global_table.json")) as f:
        gtable = json.load(f)
    print(f"{len(paths)} blocks, order = {args.block_order}")

    # ---- pass over the tree: collect candidates on the table's planes ----
    acc = {i: [] for i in range(nzp)}
    n_unmapped = 0
    for rank, path in enumerate(paths):
        with np.load(path) as npz:
            z0 = int(npz["z0"]); y0 = int(npz["y0"]); x0 = int(npz["x0"])
            lo = np.searchsorted(zs_arr, z0, "left")
            hi = np.searchsorted(zs_arr, z0 + 256, "left")
            if lo == hi:
                continue
            labels = npz["labels"]
            hi = np.searchsorted(zs_arr, z0 + labels.shape[0], "left")
            if lo == hi:
                continue
            tab = gtable[f"z{z0}/y{y0}_x{x0}"]
            mx = max((int(k) for k in tab), default=0)
            lut = np.full(mx + 1, -1, np.int64)
            for kloc, gid in tab.items():
                lut[int(kloc)] = gid
            for z in zs_arr[lo:hi]:
                sl = labels[z - z0]
                ys, xs = np.nonzero(sl)
                if not len(ys):
                    continue
                loc = sl[ys, xs]
                gid = np.where(loc <= mx, lut[np.minimum(loc, mx)], -1)
                keep = gid >= 0
                n_unmapped += int((~keep).sum())
                acc[zpos[int(z)]].append(
                    ((ys[keep] + y0).astype(np.uint16),
                     (xs[keep] + x0).astype(np.uint16),
                     gid[keep].astype(np.int32),
                     np.full(keep.sum(), rank, np.uint16)))
        if (rank + 1) % 100 == 0:
            print(f"  {rank+1}/{len(paths)} blocks  "
                  f"[{time.time()-t0:.0f}s]")
    if n_unmapped:
        print(f"WARNING: {n_unmapped:,} voxels with a local id missing "
              f"from global_table.json (dropped)")

    # ---- per plane: first-writer-wins, seam stats, winding assignment ----
    N = np.zeros((nk, 60, nzp), np.int32)
    R10 = np.full((nk, 60, nzp), np.nan, np.float32)
    R90 = np.full((nk, 60, nzp), np.nan, np.float32)
    DRM = np.full((nk, 60, nzp), np.nan, np.float32)
    hist_dr = np.zeros(300, np.int64)          # |dr| in 0.05-vox bins
    seam_dup = seam_dis = n_vox = n_ok = 0
    qa_u, qa_c = [], []
    for iz, z in enumerate(zs):
        if not acc[iz]:
            continue
        y = np.concatenate([c[0] for c in acc[iz]])
        x = np.concatenate([c[1] for c in acc[iz]])
        g = np.concatenate([c[2] for c in acc[iz]])
        rk = np.concatenate([c[3] for c in acc[iz]])
        acc[iz] = None
        o = np.argsort(rk, kind="stable")      # writer order
        y, x, g = y[o], x[o], g[o]
        key = y.astype(np.int64) * 4096 + x
        s = np.argsort(key, kind="stable")     # groups keys, keeps order
        kv, gv = key[s], g[s]
        new = np.r_[True, kv[1:] != kv[:-1]]
        grp = np.cumsum(new) - 1
        fg = gv[new][grp]                      # first writer's gid
        seam_dup += int((~new).sum())
        seam_dis += int(((~new) & (gv != fg)).sum())
        yw, xw, gw = y[s][new], x[s][new], gv[new]
        n_vox += len(yw)

        ox, oy = origins[z]
        dx = xw.astype(np.float64) - ox
        dy = yw.astype(np.float64) - oy
        ir = (np.rint((np.degrees(np.arctan2(dy, dx)) % 360.0) / 6.0)
              .astype(np.int64)) % 60
        rp = np.hypot(dx, dy)
        M = Rg[:, ir, iz]
        D = np.abs(M - rp[None, :])
        D = np.where(np.isfinite(D), D, np.inf)
        j = np.arange(D.shape[1])
        k1 = np.argmin(D, axis=0)
        d1 = D[k1, j]
        D[k1, j] = np.inf
        d2 = np.min(D, axis=0)
        with np.errstate(invalid="ignore"):
            frac = d1 / np.maximum(d1 + d2, 1e-9)
        okm = np.isfinite(d1) & (d1 <= TOL_ABS) & (frac <= TOL_FRAC)
        n_ok += int(okm.sum())
        kk = k1[okm].astype(np.int16)
        irr = ir[okm].astype(np.int16)
        rr = rp[okm].astype(np.float32)
        dd = d1[okm].astype(np.float32)
        gg = gw[okm]
        hist_dr += np.bincount(np.minimum((dd / 0.05).astype(np.int64),
                                          299), minlength=300)
        cell = kk.astype(np.int64) * 60 + irr
        o2 = np.argsort(cell, kind="stable")
        cs, rs, ds = cell[o2], rr[o2], dd[o2]
        bnd = np.flatnonzero(np.r_[True, cs[1:] != cs[:-1]])
        ends = np.r_[bnd[1:], len(cs)]
        for a, b in zip(bnd, ends):
            k_, i_ = int(cs[a] // 60), int(cs[a] % 60)
            N[k_, i_, iz] = b - a
            R10[k_, i_, iz] = np.percentile(rs[a:b], 10)
            R90[k_, i_, iz] = np.percentile(rs[a:b], 90)
            DRM[k_, i_, iz] = np.median(ds[a:b])
        pk = gg.astype(np.int64) * 128 + kk
        u, c = np.unique(pk, return_counts=True)
        qa_u.append(u); qa_c.append(c)
        if args.save_points:
            np.savez_compressed(
                os.path.join(args.out, f"points_z{z}.npz"),
                y=yw[okm], x=xw[okm], gid=gg, k=kk, dr=dd)

    # ---- exams ------------------------------------------------------------
    frac_ok = n_ok / max(1, n_vox)
    cum = np.cumsum(hist_dr)
    med = (np.searchsorted(cum, cum[-1] / 2) + 0.5) * 0.05
    agree = 1 - seam_dis / max(1, seam_dup)
    print(f"\nvoxels on the table's planes (after first-writer): "
          f"{n_vox:,}")
    print(f"assigned without ambiguity: {n_ok:,} ({frac_ok:.1%}) — "
          f"EXAM A (>=60%): {'PASS' if frac_ok >= 0.60 else 'FAIL'} "
          f"(step-8 gave 85.8%)")
    print(f"median |dr|: {med:.2f} vox — EXAM B (<=3): "
          f"{'PASS' if med <= 3.0 else 'REVIEW'} (step-8 gave 2.61)")
    print(f"overlap voxels: {seam_dup:,}; id agreement {agree:.1%} "
          f"(published sample: 82.9%)")

    # ---- instance QA: winding gaps ---------------------------------------
    u = np.concatenate(qa_u); c = np.concatenate(qa_c)
    uu, inv = np.unique(u, return_counts=False), None
    uu, inv = np.unique(u, return_inverse=True)
    cc = np.bincount(inv, weights=c).astype(np.int64)
    gidq, kq = uu // 128, (uu % 128).astype(np.int64)
    o3 = np.lexsort((kq, gidq))
    gidq, kq, cc = gidq[o3], kq[o3], cc[o3]
    bnd = np.flatnonzero(np.r_[True, gidq[1:] != gidq[:-1]])
    ends = np.r_[bnd[1:], len(gidq)]
    n_eval = n_gap = 0
    with open(os.path.join(args.out, "qa_instances_fullres.csv"),
              "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["instance_id", "n_pts", "n_k", "kmin", "kmax",
                    "gap", "side_min"])
        for a, b in zip(bnd, ends):
            ks, ns = kq[a:b], cc[a:b]
            npts = int(ns.sum())
            if npts < 6:
                continue
            n_eval += 1
            if b - a == 1:
                continue
            difs = np.diff(ks)
            jm = int(np.argmax(difs))
            gap = int(difs[jm]) - 1
            side = min(int(ns[:jm + 1].sum()), int(ns[jm + 1:].sum()))
            if gap >= 2 and side >= 3:
                n_gap += 1
                w.writerow([int(gidq[a]), npts, b - a, int(ks[0]),
                            int(ks[-1]), gap, side])
    print(f"instance QA: {n_eval:,} instances (>=6 pts), "
          f"{n_gap:,} with a winding gap >=2 "
          f"({n_gap/max(1,n_eval):.1%}; step-8 gave 27.7%)")

    np.savez_compressed(os.path.join(args.out, "winding_maps_1218.npz"),
                        n=N, r_p10=R10, r_p90=R90, dr_med=DRM,
                        zs=zs_arr, note="thickness proxy = r_p90 - r_p10")
    json.dump({"voxels": n_vox, "assigned": n_ok,
               "assigned_frac": round(frac_ok, 4),
               "median_dr_vox": round(float(med), 3),
               "overlap_voxels": seam_dup,
               "overlap_agreement": round(agree, 4),
               "instances_eval": n_eval, "instances_gap": n_gap,
               "tol_abs": TOL_ABS, "tol_frac": TOL_FRAC,
               "block_order": args.block_order,
               "seconds": round(time.time() - t0)},
              open(os.path.join(args.out, "summary.json"), "w"), indent=1)
    print(f"\nwritten to {args.out}/ ; total {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()