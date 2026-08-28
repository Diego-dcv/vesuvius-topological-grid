#!/usr/bin/env python3
"""
planchado_heldout_um_1218.py — mode 17 addendum: the folding law re-examined
in MICRONS by leave-one-winding-out.

Question: if a winding that IS known is hidden, with what error in um is its
radial position reconstructed from the surviving neighbours, and does it fall
inside its correct gap (+/- s/2, s = measured local separation)?

Competing predictors (all three reported, whichever wins):
  P0  ideal spiral: radius interpolated from neighbours, no relief (floor)
  P1  neighbours:   bin-by-bin interpolation (r[k-1]+r[k+1])/2
  P2  held-out field: interpolated radius + A(k)*F(theta,z), with F and A
      computed WITHOUT the hidden winding (mode 17's ironing, held out)
  NEG control: P2 with F shuffled in theta - must degrade toward P0
Two arms: hide 1 winding (neighbours adjacent) / hide 3 (neighbours at +/-2).

Criteria fixed BEFORE running:
  SANITY:   global R^2 of the A*F fit must reproduce mode 17 (0.68 +/- 0.10);
            if not, this re-implementation is wrong.
  EXAM A3:  P2 beats P0 in global median (else the field adds nothing).
  EXAM B3:  does P1 beat P2? - reported exactly as it falls, no verdict.

INPUTS (this was run as a Colab cell): expects `rows`, `zs`, `zpos` already in
namespace from the crossing-table loading step - the 1218 crossing table with
fields k, theta_deg, z, r_l1_vox. Needs no CT and no winding maps.

OUTPUTS: pl4_error_um.png, pl4_resultados_1218.npz
"""
import numpy as np, matplotlib.pyplot as plt, warnings, time
warnings.filterwarnings("ignore", message="All-NaN")

t0 = time.time()
for v in ["rows", "zs", "zpos"]:
    assert v in dir(), f"falta {v}: corre primero la celda de carga"

VOX = 0.01728; COB_MIN = 0.10
rng = np.random.default_rng(4)

kmax = max(int(r["k"]) for r in rows)
nzp = len(zs)
Rg = np.full((kmax + 1, 60, nzp), np.nan, np.float32)
for r in rows:
    Rg[int(r["k"]),
       int(round(float(r["theta_deg"]) / 6)) % 60,
       zpos[int(r["z"])]] = float(r["r_l1_vox"]) * VOX   # mm
cob = np.isfinite(Rg).reshape(kmax + 1, -1).mean(axis=1)
K = np.array([k for k in range(2, kmax + 1) if cob[k] >= COB_MIN])
print(f"vueltas usables (cobertura >={COB_MIN:.0%}): k {K[0]}..{K[-1]} "
      f"({len(K)})")

# relieve por vuelta y normalizados robustos (forma del modo 17)
rbar = np.array([np.nanmedian(Rg[k]) for k in K])
REL = np.stack([Rg[k] - rb for k, rb in zip(K, rbar)])      # (nK,60,nz)
def mad(a):
    m = np.nanmedian(a)
    return 1.4826 * np.nanmedian(np.abs(a - m)) + 1e-9
ESC = np.array([mad(REL[i]) for i in range(len(K))])
NORM = REL / ESC[:, None, None]

def ajusta_A(F, idx):
    """pendiente A_k = <F*rel>/<F^2> por vuelta, solo bins finitos"""
    A = np.full(len(K), np.nan)
    for i in idx:
        m = np.isfinite(REL[i]) & np.isfinite(F)
        den = np.nansum(F[m] ** 2)
        A[i] = np.nansum(F[m] * REL[i][m]) / den if den > 0 else np.nan
    return A

# SANIDAD: reproducir el R2 del modo 17 con todo dentro
F_full = np.nanmedian(NORM, axis=0)
A_full = ajusta_A(F_full, range(len(K)))
sse = sst = 0.0
for i in range(len(K)):
    m = np.isfinite(REL[i]) & np.isfinite(F_full)
    sse += np.nansum((REL[i][m] - A_full[i] * F_full[m]) ** 2)
    sst += np.nansum(REL[i][m] ** 2)
R2 = 1 - sse / sst
print(f"SANIDAD R2 global del ajuste A*F: {R2:.2f} "
      f"({'reproduce el modo 17' if 0.58 <= R2 <= 0.78 else 'AVISO: fuera de 0.68+/-0.10'})")

# ---------- el examen: dos brazos ----------
def examen(paso):
    """paso=1: ocultar k, vecinas k+/-1; paso=2: ocultar k-1..k+1, vecinas k+/-2"""
    res = {m: {"k": [], "med": [], "gap": []} for m in
           ["P0", "P1", "P2", "NEG"]}
    kidx = {k: i for i, k in enumerate(K)}
    for k in K:
        if (k - paso) not in kidx or (k + paso) not in kidx:
            continue
        i0, im, ip = kidx[k], kidx[k - paso], kidx[k + paso]
        oculta = [j for j in range(len(K))
                  if abs(K[j] - k) <= (paso - 1)]          # 1 o 3 vueltas
        vis = [j for j in range(len(K)) if j not in oculta]
        # campo y amplitudes SIN las vueltas ocultas
        Fh = np.nanmedian(NORM[vis], axis=0)
        Ah = ajusta_A(Fh, vis)
        Aint = np.interp(k, K[vis], Ah[vis])
        rint = np.interp(k, K[vis], rbar[vis])
        # bins evaluables comunes
        m = (np.isfinite(Rg[k]) & np.isfinite(Rg[k - paso])
             & np.isfinite(Rg[k + paso]) & np.isfinite(Fh))
        if m.sum() < 100:
            continue
        s = (Rg[k + paso][m] - Rg[k - paso][m]) / (2 * paso)  # separacion local
        verdad = Rg[k][m]
        preds = {
            "P0": np.full(m.sum(), rint),
            "P1": (Rg[k - paso][m] + Rg[k + paso][m]) / 2,
            "P2": rint + Aint * Fh[m],
            "NEG": rint + Aint * np.roll(Fh, rng.integers(5, 55), axis=0)[m],
        }
        for nom, p in preds.items():
            e = np.abs(p - verdad) * 1000.0                   # um
            res[nom]["k"].append(k)
            res[nom]["med"].append(np.median(e))
            res[nom]["gap"].append(np.mean(e < np.abs(s) * 500.0))  # |e|<s/2
        if k == K[len(K) // 2]:
            res["_s_med"] = float(np.median(np.abs(s)) * 1000)
    return res

print("\ncorriendo brazo 1 (ocultar 1 vuelta) y brazo 2 (ocultar 3)...")
R1, R2b = examen(1), examen(2)

def resumen(R, titulo):
    print(f"\n- {titulo} (separacion local mediana "
          f"~{R.get('_s_med', float('nan')):.0f} um) -")
    filas = {}
    for nom, lab in [("P0", "P0 espiral (suelo)"),
                     ("P1", "P1 interp vecinas"),
                     ("P2", "P2 campo held-out"),
                     ("NEG", "control barajado")]:
        med = np.array(R[nom]["med"]); gap = np.array(R[nom]["gap"])
        filas[nom] = (np.median(med), np.percentile(med, [25, 75]),
                      np.mean(gap))
        print(f"  {lab:22s} mediana|e| {np.median(med):6.0f} um "
              f"[{np.percentile(med,25):.0f}-{np.percentile(med,75):.0f}]  "
              f"en hueco correcto {np.mean(gap):.0%}")
    return filas

f1 = resumen(R1, "BRAZO 1: vuelta oculta, vecinas pegadas")
f2 = resumen(R2b, "BRAZO 2: tres ocultas, vecinas a +/-2")

a3 = f1["P2"][0] < f1["P0"][0] and f2["P2"][0] < f2["P0"][0]
print(f"\nEXAMEN A3 (P2 mejora a P0 en ambos brazos): "
      f"{'PASS' if a3 else 'FAIL'}")
neg_ok = f1["NEG"][0] > f1["P2"][0]
print(f"control negativo degrada a P2: {'si' if neg_ok else 'NO - REVISAR'}")
print(f"EXAMEN B3 (informativo): P1 vs P2 - brazo 1: "
      f"{'P1' if f1['P1'][0] < f1['P2'][0] else 'P2'} gana "
      f"({f1['P1'][0]:.0f} vs {f1['P2'][0]:.0f} um); brazo 2: "
      f"{'P1' if f2['P1'][0] < f2['P2'][0] else 'P2'} gana "
      f"({f2['P1'][0]:.0f} vs {f2['P2'][0]:.0f} um)")

fig, ax = plt.subplots(1, 2, figsize=(13, 4.5), sharey=True)
for A, R, tt in [(ax[0], R1, "brazo 1: 1 vuelta oculta"),
                 (ax[1], R2b, "brazo 2: 3 ocultas (vecinas +/-2)")]:
    for nom, st in [("P0", "k:"), ("P1", "g-"), ("P2", "b-"),
                    ("NEG", "r--")]:
        A.plot(R[nom]["k"], R[nom]["med"], st, label=nom, lw=1.5)
    A.axhline(100, color="gray", ls=":", lw=1)
    A.text(K[2], 105, "s/2 ~ 100 um", fontsize=8, color="gray")
    A.set_yscale("log"); A.set_xlabel("vuelta k"); A.set_title(tt)
    A.grid(alpha=0.3)
ax[0].set_ylabel("mediana |error| (um)"); ax[0].legend(fontsize=8)
plt.tight_layout(); plt.savefig("pl4_error_um.png", dpi=130)
np.savez_compressed(
    "pl4_resultados_1218.npz", R2_sanidad=R2,
    **{f"b1_{n}_{c}": np.array(R1[n][c]) for n in ["P0", "P1", "P2", "NEG"]
       for c in ["k", "med", "gap"]},
    **{f"b2_{n}_{c}": np.array(R2b[n][c]) for n in ["P0", "P1", "P2", "NEG"]
       for c in ["k", "med", "gap"]})
print(f"\nficheros: pl4_error_um.png, pl4_resultados_1218.npz "
      f"[{time.time()-t0:.0f}s]")
