# =====================================================================
# CELDA "PARED POR ALTURA" — PHerc1218 (segundos, no lee el escáner)
# Lee contar_vueltas.json (lo guardó la celda de contar en Drive) y dice,
# para cada altura: grosor de la pared contada, separación entre hojas y
# cuánto ombligo se saltó. Sirve para decidir por qué hay menos vueltas
# al subir aunque el rollo mide lo mismo por fuera:
#   - si la PARED adelgaza  -> el hueco central (lo no contable) crece
#   - si la SEPARACIÓN crece -> las hojas están más sueltas arriba
# =====================================================================
import json, os
import numpy as np
try:
    from google.colab import drive
    drive.mount("/content/drive")
    P = "/content/drive/MyDrive/vesuvius_1218/contar_vueltas/contar_vueltas.json"
except Exception:
    P = "./vesuvius_1218/contar_vueltas/contar_vueltas.json"
R = json.load(open(P))["results"]
print(f"{'altura':>7} | {'pared arriba+abajo':>18} | {'separación':>10} | {'ombligo saltado':>15} | vueltas")
for z in sorted({r["z"] for r in R}):
    rr = [r for r in R if r["z"] == z and r["offset"] == 0.0]
    wall = sum(r["pared_mm"] for r in rr)
    sep = np.median([r["sep_mm"] for r in R if r["z"] == z]) * 1000
    omb = sum(r["omb_mm"] for r in rr)
    n = np.mean([np.median([r["vueltas"] for r in R if r["z"] == z and r["lado"] == s])
                 for s in ("ARRIBA", "ABAJO")])
    print(f"{z:7.0f} | {wall:15.1f} mm | {sep:7.0f} µm | {omb:12.2f} mm | {n:5.1f}")
print("\nLECTURA: si la pared baja al subir -> crece lo no contable del centro;")
print("si la separación sube al subir -> hojas más sueltas arriba; si ninguna, avisa.")
print("listo")
