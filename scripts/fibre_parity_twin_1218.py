#!/usr/bin/env python3
"""
fibre_parity_twin_1218.py -- synthetic twin for fibre_parity_1218.py.
A fake level-0 volume with sheets of two crossed fibre layers, computed on
demand. Five cases, all must come out as stated (run before the real scroll):
    layers   -> MARKER EXISTS      (two layers, horizontal in / vertical out)
    tilted   -> MARKER EXISTS      (same, sheets locally tilted up to 15 deg)
    smooth   -> E1 FAIL            (no fibre texture at all)
    uniform  -> NO MARKER          (texture, but one direction through the sheet)
    fused    -> MARKER EXISTS      (sheets pressed together, no air between them)
What the twin caught before the real run: an interpolation bias that faked a
direction on smooth sheets (null now shuffled BEFORE the rotation), and tilt
mixing the two layers inside a patch (box now flattened on the sheet's own
tilt before measuring).
"""
import numpy as np, sys, os
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
mode = sys.argv[1]      # "layers" | "smooth" | "tilted"
rng = np.random.default_rng(3)
# geometry: 12 planes, origin (600,600), sheets k=0..29 pitch 11.6 coarse vox
zs = list(range(1000, 1000+32*12, 32)); zpos = {z:i for i,z in enumerate(zs)}
ox, oy = 600.0, 600.0
rows = []
for z in zs:
    for i in range(60):
        for k in range(21):
            rows.append(dict(z=str(z), theta_deg=str(i*6.0), k=str(k), r_l1_vox=str(100+11.6*k), r_um="0"))
origins_ct = {z:(ox, oy) for z in zs}
TH = 22 if mode == "fused" else 8    # fused: sheets fill the 23-fine-vox pitch, no air
class L0:
    """level-0 volume computed on demand for the requested box only"""
    def __getitem__(s, key):
        zsl, ysl, xsl = key
        zf = np.arange(zsl.start, zsl.stop)[:, None, None].astype(np.float64)
        yy = np.arange(ysl.start, ysl.stop)[None, :, None].astype(np.float64)
        xx = np.arange(xsl.start, xsl.stop)[None, None, :].astype(np.float64)
        dx, dy = xx - ox*2, yy - oy*2
        rr = np.hypot(dx, dy) / 2.0 + 0*zf                # coarse-vox radius, broadcast over z
        ang = np.arctan2(dy, dx) + 0*zf
        if mode == "tilted":
            rr = rr - 1.3 * np.sin(2*np.pi*zf/60.0)   # local slope up to 15 deg
        ph = (rr - 100 + TH/4.0) % 11.6
        img = np.full(rr.shape, 20.0)
        inner = (ph < TH/4.0); outer = (ph >= TH/4.0) & (ph < TH/2.0)
        img[inner | outer] = 110
        if mode in ("layers", "tilted", "uniform", "fused"):
            hz = 25 * np.sign(np.sin(2*np.pi*zf/6.0)) + 0*rr
            arc = ang * rr * 2.0
            vt = 25 * np.sign(np.sin(2*np.pi*arc/6.0))
            img[inner] += hz[inner]
            img[outer] += (hz[outer] if mode == "uniform" else vt[outer])
        img += rng.normal(0, 6, img.shape)
        return img.astype(np.float32)
ct_root = {"0": L0()}
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fibre_parity_1218.py')).read().replace("N_SAMPLES = 300", "N_SAMPLES = 90")
exec(src)
