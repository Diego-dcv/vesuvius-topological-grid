
import numpy as np, matplotlib.pyplot as plt, warnings
warnings.filterwarnings("ignore", message="All-NaN")

VOX = 0.01728; COB_MIN = 0.10
kmax = max(int(r["k"]) for r in rows)
nz = len(zs)
Rg = np.full((kmax + 1, 60, nz), np.nan, np.float32)
for r in rows:
    Rg[int(r["k"]),
       int(round(float(r["theta_deg"]) / 6)) % 60,
       zpos[int(r["z"])]] = float(r["r_l1_vox"]) * VOX
cob = np.isfinite(Rg).reshape(kmax + 1, -1).mean(axis=1)
K0 = 2
K1 = max(k for k in range(kmax + 1) if cob[k] >= COB_MIN)
nk = K1 - K0 + 1

# eje L: el desarrollo por geometría mediana (el de la cinta v5)
rmed = np.nanmedian(Rg[K0:K1 + 1], axis=2)
rk = np.nanmedian(rmed, axis=1)
f = np.isfinite(rk)
rk = np.interp(np.arange(nk), np.arange(nk)[f], rk[f])
for a in range(nk):
    fila = rmed[a]; fila[~np.isfinite(fila)] = rk[a]
rv = rmed.ravel()
seg = np.sqrt((rv * np.radians(6.0)) ** 2
              + np.diff(rv, prepend=rv[0]) ** 2)
Lfin = np.cumsum(seg); Lc = (Lfin - seg / 2)          # centro de cada bin

# la espiral IDEAL del gemelo: ajuste lineal r = a + b·k a los radios
aj = np.polyfit(np.arange(nk), rk, 1)
r_ideal_k = np.polyval(aj, np.arange(nk))
print(f"espiral ideal ajustada: paso {aj[0]:.3f} mm/vuelta, "
      f"r0 {aj[1]:.2f} mm (radios medianos {rk[0]:.2f}→{rk[-1]:.2f})")

# mapear CADA cruce de la tabla
Ls, Zr, Th, Rr, Kk = [], [], [], [], []
for r in rows:
    k = int(r["k"])
    if not (K0 <= k <= K1):
        continue
    i = int(round(float(r["theta_deg"]) / 6)) % 60
    Ls.append(Lc[(k - K0) * 60 + i])
    Zr.append(zpos[int(r["z"])])
    Th.append(i * 6.0)
    Rr.append(float(r["r_l1_vox"]) * VOX)
    Kk.append(k - K0)
Ls = np.array(Ls); Zr = np.array(Zr); Th = np.array(Th)
Rr = np.array(Rr); Kk = np.array(Kk)
desp = Rr - r_ideal_k[Kk]                 # desplazamiento radial vs ideal
print(f"cruces mapeados: {len(Ls):,} (vueltas {K0}..{K1}); "
      f"desplazamiento |d| mediana {np.median(np.abs(desp)):.2f} mm, "
      f"p95 {np.percentile(np.abs(desp),95):.2f} mm")

# ---------- figura 1: LA HOJA PLANA ----------
nbL = int(Lfin[-1] / 4.0)                 # bins de 4 mm en L
H, xe, ye = np.histogram2d(Ls, Zr, bins=[nbL, nz])
S, _, _ = np.histogram2d(Ls, Zr, bins=[nbL, nz], weights=desp)
Dm = np.divide(S, H, out=np.full_like(S, np.nan), where=H > 0)
fig, axs = plt.subplots(2, 1, figsize=(20, 7), sharex=True)
axs[0].imshow(np.log1p(H).T, aspect="auto", origin="lower", cmap="gray",
              extent=[0, Lfin[-1] / 1000, 0, nz * dz_mm])
axs[0].set_title("presencia de etiquetas (log) — los agujeros son "
                 "información: cuñas, daño, segmentación perdida")
axs[0].set_ylabel("altura (mm)")
v = np.nanpercentile(np.abs(Dm), 95)
im = axs[1].imshow(Dm.T, aspect="auto", origin="lower", cmap="RdBu_r",
                   vmin=-v, vmax=v, extent=[0, Lfin[-1] / 1000, 0,
                                            nz * dz_mm])
axs[1].set_title("desplazamiento radial respecto a la espiral ideal (mm) "
                 "— el aplastamiento entero, punto a punto")
axs[1].set_ylabel("altura (mm)")
axs[1].set_xlabel("desarrollo del papiro (m) — la hoja plana")
fig.colorbar(im, ax=axs, label="Δr vs ideal (mm)", pad=0.01)
plt.savefig("hoja_plana_1218.png", dpi=140, bbox_inches="tight")
plt.show()

# ---------- figura 2: EL ROLLO RESTAURADO ----------
sub = np.random.default_rng(0).choice(len(Ls), min(400000, len(Ls)),
                                      replace=False)
a_ = np.radians(Th[sub])
xr = r_ideal_k[Kk[sub]] * np.cos(a_)
yr = r_ideal_k[Kk[sub]] * np.sin(a_)
plt.figure(figsize=(8, 8))
sc = plt.scatter(xr, yr, s=0.3, c=np.abs(desp[sub]), cmap="inferno",
                 vmin=0, vmax=np.percentile(np.abs(desp), 95))
plt.colorbar(sc, label="|desplazamiento| al aplastarse (mm)")
plt.gca().set_aspect("equal")
plt.title("PHerc1218 restaurado a su espiral ideal — cada etiqueta en su "
          "origen,\ncolor = cuánto viajó en el colapso")
plt.xlabel("mm"); plt.ylabel("mm")
plt.tight_layout()
plt.savefig("rollo_restaurado_1218.png", dpi=140, bbox_inches="tight")
plt.show()
print("guardadas hoja_plana_1218.png y rollo_restaurado_1218.png")