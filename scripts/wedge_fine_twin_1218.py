#!/usr/bin/env python3
"""
wedge_fine_twin_1218.py -- the synthetic twin for wedge_fine_1218.py.
Builds a two-level fake scroll (rings of known pitch, a wedge zone) and runs
the real script on it. Two cases, both must come out as stated in the
script's docstring:
    python wedge_fine_twin_1218.py fused   -> E2a FUSED, E2b NO
    python wedge_fine_twin_1218.py thin    -> E2a LAMINATED (52 um pitch)
What the twin taught before the real run: the audit's counter had a 100 um
floor (could not count anything tighter at any resolution), and a short
floor lets scanner noise fake ridges unless prominence is noise-scaled.
"""
import numpy as np, sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
mode = sys.argv[1]           # "thin" (sheets thinner than coarse voxel in wedge) or "fused"
rng = np.random.default_rng(0)
# geometry: 20 planes, origin at (700,700) level-1, labelled sheets k=0..29 pitch 11.6, then wedge to r=600
zs = list(range(1000, 1000+32*20, 32)); zpos = {z:i for i,z in enumerate(zs)}
ox, oy = 700.0, 700.0
rows = []
for z in zs:
    for i in range(60):
        for k in range(30):
            r = 100 + 11.6*k + rng.normal(0, .3)
            rows.append(dict(z=str(z), theta_deg=str(i*6.0), k=str(k), r_l1_vox=str(r), r_um=str(r*17.28)))
# volume level 1: 1400x1400 per plane; brightness = rings
def make_plane(scale):
    N = int(1400*scale); yy, xx = np.mgrid[0:N, 0:N]
    rr = np.hypot(xx - ox*scale, yy - oy*scale) / scale    # in level-1 voxels
    img = np.full(rr.shape, 20.0)
    # labelled zone: sheets every 11.6 vox, thickness 4 vox
    lab = (rr >= 95) & (rr <= 100+11.6*29+6)
    ph = ((rr - 100 + 2) % 11.6)
    img[lab & (ph < 4)] = 120
    # wedge zone r in [455, 600]
    wed = (rr > 455) & (rr <= 600)
    if mode == "thin":       # sheets pitch 4.0 vox, thickness 1.5 vox: invisible at level 1, visible at level 0
        img[wed & (((rr-455) % 3.0) < 1.2)] = 120
        img[wed & (((rr-455) % 3.0) >= 1.2)] = 60
    else:                    # fused: uniform slab, no ridges
        img[wed] = 120
    img += rng.normal(0, 4, img.shape)
    return img.astype(np.float32)
class Lvl:
    def __init__(s, scale): s.scale = scale; s.cache = {}
    def __getitem__(s, key):
        z, ysl, xsl = key
        if z not in s.cache: s.cache[z] = make_plane(s.scale)
        return s.cache[z][ysl, xsl]
# level 0 has z doubled: map back
class Root(dict): pass
class L0(Lvl):
    def __getitem__(s, key):
        z, ysl, xsl = key; return Lvl.__getitem__(s, (z//2, ysl, xsl))
ct_root = {"1": Lvl(1.0), "0": L0(2.0)}
origins_ct = {z:(ox, oy) for z in zs}
Z_STRIDE_TWIN = 4
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'wedge_fine_1218.py')).read().replace('Z_STRIDE = 16', 'Z_STRIDE = 4')
exec(src)
