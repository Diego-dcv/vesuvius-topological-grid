#!/usr/bin/env python3
"""
wedge_audit_1218.py — WEDGE AUDIT: does the dead zone of each column hold its
sheets stacked, or is it empty?

DESIGN ERROR, DOCUMENTED: k is the ORDINAL of a ray crossing, not the identity
of a winding - interior gaps in k cannot exist. The earlier version asked for
gaps the format does not contain; its own calibration exams caught it. Absences
live BEYOND the last crossing of each column: the WEDGE = [last crossing, real
edge of the roll (from the masked CT)]. Nothing is assigned; things are counted
with a self-calibrated counter.

METHOD per column (ray, plane):
 - LAMINA counter (brightness ridges) calibrated on the LABELLED stretch of the
   same column: efficiency eta = ridges / windings
 - EXAM E1 (prefixed): median eta in [0.3, 1.2] - if the counter does not
   reproduce what is known, stop
 - EXAM E2 (prefixed, split-half): eta measured on the inner half must predict
   the number of windings in the outer half with median error <= 25% - proves
   eta travels within the column
 - VERDICT: rho = (ridges in wedge / eta) / (wedge depth / local pitch)
   rho ~ 1: the wedge keeps its sheets; rho ~ 0: empty / no structure.
   Only columns with >= 3 expected windings in the wedge. Bootstrap CI.
 - secondary: material fraction in the wedge vs in the labelled zone

INPUTS (this was run as a Colab cell): expects `rows`, `zs`, `zpos` from the
crossing-table loading step and `vol` from the texture-setup step. Origins are
read from the labels' author's repository over HTTP. ~40 min at Z_STRIDE=2.

OUTPUTS: lam3v3_cunas.npz, lam3v3_mapa.png, lam3v3_scatter.png
"""
import numpy as np, matplotlib.pyplot as plt, csv, io, urllib.request
import warnings, time
from scipy.signal import find_peaks
warnings.filterwarnings("ignore", message="All-NaN")

t0 = time.time()
for v in ["rows", "zs", "zpos", "vol"]:
    assert v in dir(), f"falta {v}: corre carga de tabla y TEX-0"
VOX = 0.01728; DX, DY = -3, -1
Z_STRIDE = 2
RMAX_SCAN = 1360.0
rng = np.random.default_rng(71)
RAW = ("https://raw.githubusercontent.com/Jinhojeong/"
       "vesuvius-surface-geometry-diagnostic/main/results/kollesis/")

texto = urllib.request.urlopen(RAW + "origins_merged.csv").read().decode()
acum = {}
for f_ in csv.DictReader(io.StringIO(texto)):
    z = int(float(f_["z"]))
    acum.setdefault(z, []).append((float(f_["cx"]), float(f_["cy"])))
origins = {z: (np.mean([p[0] for p in v]) + DX,
               np.mean([p[1] for p in v]) + DY) for z, v in acum.items()}
zso = sorted(origins)
for z in zs:
    if z not in origins:
        origins[z] = origins[min(zso, key=lambda q: abs(q - z))]

kmax = max(int(r["k"]) for r in rows)
nzp = len(zs)
Rg = np.full((kmax + 1, 60, nzp), np.nan, np.float32)
for r in rows:
    Rg[int(r["k"]),
       int(round(float(r["theta_deg"]) / 6)) % 60,
       zpos[int(r["z"])]] = float(r["r_l1_vox"])

# ---------- umbral de material (pre-pasada en vueltas presentes) ------------
mues = []
for iz in list(range(0, nzp, max(1, nzp // 10)))[:10]:
    zv = zs[iz]; ox, oy = origins[zv]
    kk, ii = np.nonzero(np.isfinite(Rg[:, :, iz]))
    if len(kk) > 600:
        s = rng.choice(len(kk), 600, replace=False); kk, ii = kk[s], ii[s]
    rr = Rg[kk, ii, iz]; aa = np.radians(ii * 6.0)
    xs = (ox + rr * np.cos(aa)).astype(int)
    ys = (oy + rr * np.sin(aa)).astype(int)
    x0, x1 = xs.min() - 2, xs.max() + 3
    y0, y1 = ys.min() - 2, ys.max() + 3
    img = np.asarray(vol[zv, y0:y1, x0:x1])
    mues.append(img[ys - y0, xs - x0].astype(np.float32))
mues = np.concatenate(mues)
UMB = np.percentile(mues, 5)
print(f"umbral de material (p5 en vueltas presentes, n={len(mues):,}): "
      f"{UMB:.0f}  [{time.time()-t0:.0f}s]")

def procesa_columna(rr_l, prof, rs):
    """devuelve dict con calibracion, examen split-half y auditoria de cuna
       (None si la columna no es utilizable)"""
    mat = prof >= UMB
    suave = np.convolve(prof, np.ones(3) / 3.0, mode="same")
    pk, _ = find_peaks(suave, height=UMB, distance=6, prominence=10)
    rpk = rr_l[pk]
    # calibracion en el tramo etiquetado
    et0, et1 = rs[0] - 3, rs[-1] + 3
    n_et = int(((rpk >= et0) & (rpk <= et1)).sum())
    eta = n_et / len(rs)
    if not (0.2 <= eta <= 1.5):
        return None
    # split-half dentro del etiquetado
    mid = len(rs) // 2
    n_in = int(((rpk >= et0) & (rpk <= rs[mid - 1] + 3)).sum())
    n_out_true = len(rs) - mid
    eta_in = n_in / mid if mid else np.nan
    n_out_det = int(((rpk > rs[mid - 1] + 3) & (rpk <= et1)).sum())
    err_sh = (abs(n_out_det / max(eta_in, 1e-9) - n_out_true)
              / max(n_out_true, 1)) if mid >= 4 else np.nan
    # borde real del rollo: ultima ventana de 7 con >=4 material
    conv = np.convolve(mat.astype(int), np.ones(7), mode="same")
    dens = np.flatnonzero(conv >= 4)
    if not len(dens):
        return None
    R_edge = rr_l[dens[-1]]
    w0, w1 = rs[-1] + 6, R_edge
    res = {"eta": eta, "err_sh": err_sh, "exp": np.nan, "det": np.nan,
           "matfrac": np.nan, "wlen": max(0.0, w1 - w0)}
    if w1 - w0 >= 20:
        pasos = np.diff(rs[-8:]) if len(rs) >= 8 else np.diff(rs)
        pitch = float(np.median(pasos)) if len(pasos) else 11.6
        pitch = min(max(pitch, 7.0), 25.0)
        sl = (rr_l >= w0) & (rr_l <= w1)
        res["exp"] = (w1 - w0) / pitch
        res["det"] = ((rpk >= w0) & (rpk <= w1)).sum() / eta
        res["matfrac"] = float(mat[sl].mean())
    return res

# ---------- pasada principal ------------------------------------------------
cols = []
z_idx = list(range(0, nzp, Z_STRIDE))
print(f"auditando columnas en {len(z_idx)} planos...")
for c_, iz in enumerate(z_idx):
    zv = zs[iz]; ox, oy = origins[zv]
    col_fin = np.isfinite(Rg[:, :, iz])
    if not col_fin.any():
        continue
    x0 = max(0, int(ox - RMAX_SCAN) - 2); x1 = int(ox + RMAX_SCAN) + 3
    y0 = max(0, int(oy - RMAX_SCAN) - 2); y1 = int(oy + RMAX_SCAN) + 3
    img = np.asarray(vol[zv, y0:y1, x0:x1])
    for i in range(60):
        ks = np.flatnonzero(col_fin[:, i])
        if len(ks) < 8:
            continue
        rs = np.sort(Rg[ks, i, iz])
        a = np.radians(i * 6.0)
        rr_l = np.arange(max(0.0, rs[0] - 10), RMAX_SCAN, 1.0)
        px = np.clip((ox + rr_l * np.cos(a)).astype(int) - x0, 0,
                     img.shape[1] - 1)
        py = np.clip((oy + rr_l * np.sin(a)).astype(int) - y0, 0,
                     img.shape[0] - 1)
        prof = img[py, px].astype(np.float32)
        res = procesa_columna(rr_l, prof, rs)
        if res is not None:
            res["i"] = i; res["iz"] = iz
            cols.append(res)
    if c_ % 30 == 0:
        print(f"  {c_}/{len(z_idx)}  [{time.time()-t0:.0f}s]")
print(f"columnas utilizables: {len(cols):,}  [{time.time()-t0:.0f}s]")

eta = np.array([c["eta"] for c in cols])
esh = np.array([c["err_sh"] for c in cols], float)
print(f"\nEXAMEN E1 - eficiencia del contador en lo conocido: "
      f"mediana {np.median(eta):.2f}  IQR "
      f"[{np.percentile(eta,25):.2f}-{np.percentile(eta,75):.2f}]  "
      f"(criterio mediana en 0.3-1.2): "
      f"{'PASS' if 0.3 <= np.median(eta) <= 1.2 else 'FAIL - PARAR'}")
fsh = np.isfinite(esh)
print(f"EXAMEN E2 - split-half (eta interior predice mitad exterior): "
      f"error mediano {np.nanmedian(esh[fsh]):.1%}  "
      f"(criterio <=25%): "
      f"{'PASS' if np.nanmedian(esh[fsh]) <= 0.25 else 'FAIL - PARAR'}")

exp = np.array([c["exp"] for c in cols], float)
det = np.array([c["det"] for c in cols], float)
mfr = np.array([c["matfrac"] for c in cols], float)
q = np.isfinite(exp) & (exp >= 3)
print(f"\ncolumnas con cuna auditable (>=3 vueltas esperadas): {q.sum():,}")
rho = det[q].sum() / exp[q].sum()
boots = []
idx = np.flatnonzero(q)
for _ in range(500):
    s = rng.choice(idx, len(idx))
    boots.append(det[s].sum() / exp[s].sum())
lo, hi = np.percentile(boots, [2.5, 97.5])
print(f"VEREDICTO rho global = {rho:.2f}  [IC95 {lo:.2f}-{hi:.2f}]  "
      f"(1 = la cuna guarda sus hojas / 0 = vacia)")
print(f"vueltas esperadas en cunas: {exp[q].sum():,.0f} | laminas "
      f"detectadas (corregidas por eta): {det[q].sum():,.0f}")
print(f"material en cuna: fraccion mediana {np.nanmedian(mfr[q]):.2f} "
      f"(en zona etiquetada es ~1.0 por contacto pleno)")
print("\n  rho por percentiles de columna: "
      f"p10 {np.percentile(det[q]/exp[q],10):.2f}  "
      f"p50 {np.percentile(det[q]/exp[q],50):.2f}  "
      f"p90 {np.percentile(det[q]/exp[q],90):.2f}")

# figuras
plt.figure(figsize=(7.5, 6))
plt.scatter(exp[q], det[q], s=4, alpha=0.2)
mx = np.percentile(exp[q], 99)
plt.plot([0, mx], [0, mx], "g--", label="rho=1: todas las hojas estan")
plt.plot([0, mx], [0, 0], "r--", label="rho=0: cuna vacia")
plt.xlabel("vueltas esperadas en la cuna (profundidad/paso)")
plt.ylabel("laminas detectadas / eta")
plt.title(f"LAM-3v3 - auditoria de cunas: rho = {rho:.2f} "
          f"[{lo:.2f}-{hi:.2f}]")
plt.legend(); plt.grid(alpha=0.3); plt.xlim(0, mx)
plt.tight_layout(); plt.savefig("lam3v3_scatter.png", dpi=140)
M = np.full((60, nzp), np.nan)
for c in cols:
    if np.isfinite(c["exp"]) and c["exp"] >= 3:
        M[c["i"], c["iz"]] = c["det"] / c["exp"]
plt.figure(figsize=(14, 4))
plt.pcolormesh(np.arange(nzp + 1), np.arange(61) * 6,
               np.clip(M, 0, 1.5), cmap="RdYlGn", vmin=0, vmax=1.2)
plt.colorbar(label="rho por columna (1 = hojas presentes)", pad=0.01)
plt.xlabel("plano z"); plt.ylabel("theta (grados)")
plt.title("Donde guardan las cunas sus hojas (verde = si, rojo = no)")
plt.tight_layout(); plt.savefig("lam3v3_mapa.png", dpi=140)
np.savez_compressed("lam3v3_cunas.npz",
                    eta=eta, err_sh=esh, exp=exp, det=det, matfrac=mfr,
                    i=np.array([c["i"] for c in cols]),
                    iz=np.array([c["iz"] for c in cols]), umbral=UMB)
print(f"\nficheros escritos  [{time.time()-t0:.0f}s]")
