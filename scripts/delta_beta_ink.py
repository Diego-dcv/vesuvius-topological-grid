#!/usr/bin/env python3
"""
delta_beta_ink.py  --  Quantitative basis for Observation 2 of the technical note.

Question: at which X-ray energies does lead-bearing ink diverge most, in its
X-ray optical response, from carbon papyrus?  This script computes the complex
refractive index terms delta (phase) and beta (absorption) for carbon papyrus
and for lead-loaded ink, from tabulated scattering data (via xraydb), and reports
two contrast ratios as a function of energy and lead loading:

        delta_ink(E)/delta_papyrus(E)   (phase-contrast channel)
        beta_ink(E)/beta_papyrus(E)     (absorption channel; K-edge subtraction)

so the optimal imaging energy -- and the optimal energy pair for the bi-energy
pilot -- can be read off directly.  delta is linear in density, so the lead
contribution at a partial density c_Pb is delta(Pb, c_Pb); likewise for beta.

Assumptions are explicit (see PARAMS) and this is a first-order estimate, not a
substitute for measured ink composition.

Deps: xraydb, numpy, matplotlib.   Usage: python delta_beta_ink.py
Outputs: delta_ratio.png, beta_ratio.png, ink_contrast_table.csv
"""
import csv
import numpy as np
import xraydb

# ------------------------------ PARAMS ------------------------------------
RHO_PAPYRUS = 1.0                        # g/cm^3 (carbonised, porous)
PB_LOADINGS = [0.01, 0.02, 0.05, 0.10]   # g Pb per cm^3 of ink voxel
ACQUIRED = [54e3, 70e3, 88e3, 105e3]     # eV, energies present in the archive
EGRID = np.linspace(50e3, 110e3, 601)    # eV

def delta_beta(material, density, E):
    """Return (delta, beta) arrays for scalar or array E."""
    E = np.atleast_1d(E).astype(float)
    d = np.empty_like(E); b = np.empty_like(E)
    for i, e in enumerate(E):
        val = xraydb.xray_delta_beta(material, density, e)
        d[i], b[i] = val[0], val[1]
    return d, b

# papyrus (carbon) baseline
d_pap, b_pap = delta_beta("C", RHO_PAPYRUS, EGRID)

d_ratio, b_ratio = {}, {}
for c in PB_LOADINGS:
    d_pb, b_pb = delta_beta("Pb", c, EGRID)     # lead at partial density c
    d_ratio[c] = (d_pap + d_pb) / d_pap
    b_ratio[c] = (b_pap + b_pb) / b_pap

# ------------------------------ table -------------------------------------
def at(E):
    dP, bP = delta_beta("C", RHO_PAPYRUS, E)
    r = {"E_keV": E/1e3, "delta_pap": float(dP[0]), "beta_pap": float(bP[0])}
    for c in PB_LOADINGS:
        dpb, bpb = delta_beta("Pb", c, E)
        r[f"dratio_{int(c*1000)}mg"] = float((dP[0]+dpb[0])/dP[0])
        r[f"bratio_{int(c*1000)}mg"] = float((bP[0]+bpb[0])/bP[0])
    return r

rows = [at(E) for E in ACQUIRED]
with open("ink_contrast_table.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader()
    for r in rows:
        w.writerow({k:(f"{v:.4g}" if isinstance(v,float) else v) for k,v in r.items()})

print("Ink/papyrus contrast at the acquired energies (lead loading g/cm^3):\n")
print("PHASE  delta_ink/delta_papyrus")
print(f"{'E[keV]':>7} " + " ".join(f"{c*1000:.0f}mg".rjust(9) for c in PB_LOADINGS))
for r in rows:
    print(f"{r['E_keV']:7.0f} " + " ".join(f"{r[f'dratio_{int(c*1000)}mg']:9.4f}" for c in PB_LOADINGS))
print("\nABSORPTION  beta_ink/beta_papyrus")
print(f"{'E[keV]':>7} " + " ".join(f"{c*1000:.0f}mg".rjust(9) for c in PB_LOADINGS))
for r in rows:
    print(f"{r['E_keV']:7.0f} " + " ".join(f"{r[f'bratio_{int(c*1000)}mg']:9.3f}" for c in PB_LOADINGS))

mid = PB_LOADINGS[len(PB_LOADINGS)//2]
# K-edge subtraction gain: absorption ratio jump across 88 keV
below = b_ratio[mid][np.argmin(np.abs(EGRID-86e3))]
above = b_ratio[mid][np.argmin(np.abs(EGRID-90e3))]
print(f"\nAt {mid} g/cm^3 Pb, absorption ratio jumps from ~{below:.2f} (86 keV) to ~{above:.2f} (90 keV)")
print("=> the cleanest exploitable signal is K-edge subtraction across the Pb K-edge (~88 keV):")
print("   bracket the edge (one energy below, one above); beta jumps for lead, is smooth for carbon.")

# ------------------------------ figures -----------------------------------
try:
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    for name, R, ylab, title in [
        ("delta_ratio.png", d_ratio, r"$\delta_{ink}/\delta_{papyrus}$", "Phase channel"),
        ("beta_ratio.png",  b_ratio, r"$\beta_{ink}/\beta_{papyrus}$",  "Absorption channel (K-edge subtraction)")]:
        fig, ax = plt.subplots(figsize=(7,4.2))
        for c in PB_LOADINGS: ax.plot(EGRID/1e3, R[c], label=f"{c*1000:.0f} mg/cm$^3$ Pb")
        ax.axvline(88.0, ls="--", c="k", lw=0.8, alpha=0.6)
        ax.text(88.3, ax.get_ylim()[1], " Pb K-edge", va="top", fontsize=8)
        ax.set_xlabel("X-ray energy [keV]"); ax.set_ylabel(ylab)
        ax.set_title(f"Ink/papyrus contrast vs energy — {title}")
        ax.legend(fontsize=8); ax.grid(alpha=0.3); fig.tight_layout(); fig.savefig(name, dpi=140)
    print("\nFigures written: delta_ratio.png, beta_ratio.png")
except Exception as e:
    print("figure step skipped:", e)
