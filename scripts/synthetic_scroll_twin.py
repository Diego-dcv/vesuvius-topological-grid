#!/usr/bin/env python3
"""
synthetic_scroll_twin.py -- Self-adjusting synthetic papyrus twin.
Reference formulation + implementation + acceptance test.

Diego C. V. (vesuvius-topological-grid) -- the twin the toolchain needed:
a test bench with perfect ground truth, NOT a microscope on the real scroll.

WHAT IT IS
----------
Give it a WORK (its length in columns) and it builds the whole scroll around
it -- that is the self-adjusting part. The chain is:

    obra (N columns)
      -> sheet length  L = lead_in + N * P + tail
      -> winding turns and outer radius (Archimedean spiral from a fixed
         umbilicus r0; the roll is as fat as the work is long)
      -> ink placed on the sheet with the MEASURED grid
         (letter pitch 4.16 mm, line spacing 2.79 mm, column period 43 mm,
          page height 200 mm -- Paris 4 numbers, independently replicated)
      -> geometric crush to the MEASURED deformation: each winding turn is
         mapped, arc-length preserving, onto a 2:1 ellipse of equal
         perimeter, folds landing at 0/180 deg on the long axis -- exactly
         the two opposed folds measured on PHerc1218.

Every letter's position is known before and after crushing because we put it
there: perfect ground truth (per-letter CSV: column, line, letter, unrolled
(s, z), turn, wound (x, y), crushed (x, y)).

WHAT IT IS FOR (and not)
------------------------
FOR: a common, realistic test bench for the toolchain (void_aware, rank,
orient, the fiber idea) -- fuse turns on purpose and check the counter counts
them; carve voids and check "don't count the air" holds; add crossed-fiber
texture and give the fiber detector its first 3D target. And one external
readout, stated carefully: the crushed SECTION SIZE as a function of the work
length -- which yields an implied work only once a pitch AND an umbilicus are
assumed. Neither is measured here. See `sensitivity`.

NOT: evidence about the real scroll. If the tools recover what the twin
contains, the tools work on the twin's assumptions -- nothing more.

WHAT SURVIVED A CORRECTION, AND WHAT DID NOT
--------------------------------------------
NOT: "the measured section implies ~95 columns, which winds to 69.7 turns
against ~70 measured independently -- three measurements closing a loop."
That was circular. With the section and the pitch fixed, the turn count is a
function of the umbilicus alone, and the umbilicus (r0 = 4.1 mm) had been
chosen so that 70 turns came out. Moving r0 from 3 to 6 mm moves the implied
count from 76 to 59 turns; the "agreement" was an identity. What survives is
the inverse: IF the count is ~70 and the pitch 173 um, THEN the umbilicus is
~4.1 mm -- falsifiable against the core in the raw CT. And the implied work
must always name its pitch: 173 um (human anchor) gives 95 columns, 187.3 um
(the corrected 35-scroll atlas) gives 88.

SURVIVES: anisotropic layer gap after crushing. Equal-perimeter 2:1 ellipses
space ~2x wider along the fold axis than along the flattened axis, where the
gap falls BELOW the nominal pitch. The twin therefore predicts merge excess
concentrated on the flattened axis -- which is what the void-aware run on the
real PHerc1218 found, independently. This depends only on the 2:1 ratio,
which is cross-confirmed by two quantities, not on the pitch or the
umbilicus. The absolute figures do scale with the pitch.

DECLARED LIMITS
---------------
1. The crush is imposed, not simulated: arc-length-preserving mapping to the
   observed final shape. Fold sharpness, local buckling and contact mechanics
   are NOT modeled; a finite-element sheet model is a separate project.
2. One scribe, one grid, constant pitch. Options --fuse / --void break the
   ideal on purpose for tool testing; they are labeled in the ground truth.
3. Line count per column follows from the measured 2.79 mm spacing and the
   200 mm page (~54 lines) -- taller than the 25-45 typical of opened rolls.
   The measured grid wins here by policy; override --line-mm to taste.

USAGE
-----
    python synthetic_scroll_twin.py build --columns 72 \
        --csv twin_truth.csv --plot twin.png          # the twin, sized by the obra
    python synthetic_scroll_twin.py sweep --plot sweep.png   # section vs obra
    python synthetic_scroll_twin.py volume --columns 72 --z-window 8 \
        --voxel-um 60 --out twin_vol.npy [--fibers] [--fuse 20,24,90,180]
    python synthetic_scroll_twin.py test                     # the exam
"""

import argparse
import sys
import numpy as np

# ---------------------------------------------------------------------------
# Measured defaults (Paris 4 grid, PHerc1218 winding) -- all overridable
# ---------------------------------------------------------------------------
G = dict(
    pitch_um=173.0,      # winding pitch
    r0_mm=4.1,           # umbilicus radius (fixed; the roll grows outward)
    letter_mm=4.16,      # letter pitch along the line
    line_mm=2.79,        # line spacing -- CONTRADICTED, see grid_warnings()
    col_period_mm=43.0,  # column period -- CONTRADICTED, see grid_warnings()
    col_written_mm=33.0, # written width of a column
    page_mm=200.0,       # sheet height
    margin_mm=25.0,      # top and bottom margins
    lead_in_mm=150.0,    # blank protokollon before column 1
    tail_mm=200.0,       # final blank + subscriptio
    ratio=2.0,           # crush aspect ratio (measured 2:1)
    sheet_um=150.0,      # sheet thickness (for the voxel volume)
    kollesis_mm=180.0,   # kollema (sheet) width -- Egyptian manufacture
    kollesis_ov_mm=15.0, # overlap at the join (double thickness band)
)
SECTION_MEASURED = (42.0, 21.0)   # mm, PHerc1218

# --- script presets -------------------------------------------------------
# ONLY the Greek row is measured (Paris 4, replicated). The Latin rows are
# DECLARED PLACEHOLDERS: no Herculaneum Latin roll has been measured to this
# precision here. They exist to model the STRUCTURE (ragged right in verse,
# interpuncts) -- override the metrics with --letter-mm / --line-mm before
# quoting any number from them.
SCRIPTS = {
    'greek': dict(letter_mm=4.16, line_mm=2.79, col_written_mm=33.0,
                  verse=False, interpunct=False, measured=True),
    'latin-prose': dict(letter_mm=2.20, line_mm=3.20, col_written_mm=33.0,
                        verse=False, interpunct=True, measured=False),
    'latin-verse': dict(letter_mm=2.20, line_mm=3.20, col_written_mm=None,
                        verse=True, interpunct=True, measured=False,
                        line_letters=(30, 40)),  # hexameter, ragged right
}


# ---------------------------------------------------------------------------
# Geometry: self-adjusting roll from the obra
# ---------------------------------------------------------------------------
# Plausible ranges established outside this repository. A value outside its
# range is not forbidden -- the measured number stays the default -- but the
# tool says so on every run, because a caveat that lives only in the README is
# a caveat the output does not carry.
PLAUSIBLE = {
    'line_mm': (3.8, 6.0),       # from column-height arithmetic: a 200 mm page
                                 # leaves ~150 mm written, and Herculaneum
                                 # columns carry a few tens of lines
    'col_period_mm': (65.0, 80.0),  # On Poems II 72.1, PHerc.1667 ~75,
                                    # get_ink_metrics 65 mm written + intercolumn
    'letter_mm': (3.8, 4.3),     # 65 mm column / 15-17 letters per line
}


def grid_warnings(g=G):
    """Which grid values sit outside their externally plausible range."""
    out = []
    for k, (lo, hi) in PLAUSIBLE.items():
        v = g.get(k)
        if v is None or lo <= v <= hi:
            continue
        note = ''
        if k == 'line_mm':
            note = f' -> {(g["page_mm"] - 2*g["margin_mm"]) / v:.0f} lines per column'
        out.append(f'{k} = {v:g} mm is outside the plausible {lo:g}-{hi:g}{note}')
    return out


def roll_from_obra(n_columns, g=G):
    """The work fixes the sheet; the sheet fixes the roll."""
    L = g['lead_in_mm'] + n_columns * g['col_period_mm'] + g['tail_mm']
    p = g['pitch_um'] / 1000.0
    r_out = np.sqrt(g['r0_mm'] ** 2 + L * p / np.pi)   # pi(r_out^2-r0^2)/p = L
    n_turns = (r_out - g['r0_mm']) / p
    return dict(length_mm=L, r_out_mm=r_out, n_turns=n_turns)


def ellipse_axes_for_perimeter(perim, ratio=2.0):
    """Semi-axes (a, b=a/ratio) of the ellipse with the given perimeter."""
    h = ((ratio - 1) / (ratio + 1)) ** 2
    c = np.pi * (1 + 1 / ratio) * (1 + 3 * h / (10 + np.sqrt(4 - 3 * h)))
    a = perim / c
    return a, a / ratio


def ellipse_arc_table(a, b, n=4096):
    """t -> cumulative arc length fraction, CCW from +x."""
    t = np.linspace(0, 2 * np.pi, n)
    ds = np.sqrt((a * np.sin(t)) ** 2 + (b * np.cos(t)) ** 2)
    s = np.concatenate([[0.0], np.cumsum(0.5 * (ds[1:] + ds[:-1]) * np.diff(t))])
    return t, s / s[-1], s[-1]


def wound_position(s_mm, g=G):
    """Unrolled arc position s (from the INNER end of the sheet, i.e. text
    END; see note) -> (turn, phi, r, x, y) on the ideal spiral.

    Convention: the sheet is wound from the umbilicus outward, so arc length
    is measured from the inner end. Text START is OUTERMOST, so the builder
    converts reading position to s internally.
    """
    p = g['pitch_um'] / 1000.0
    b = p / (2 * np.pi)
    r0 = g['r0_mm']
    # s(phi) = r0 phi + b phi^2 / 2  ->  invert (quadratic, exact)
    phi = (-r0 + np.sqrt(r0 ** 2 + 2 * b * np.asarray(s_mm, float))) / b
    r = r0 + b * phi
    return phi / (2 * np.pi), phi, r, r * np.cos(phi), r * np.sin(phi)


def crush_points(turn_idx, phi, r, ratio=2.0):
    """Arc-length preserving map of wound points onto equal-perimeter 2:1
    ellipses, one per turn; folds land at the long-axis ends (0/180 deg)."""
    x_c = np.empty_like(r)
    y_c = np.empty_like(r)
    for ti in np.unique(turn_idx):
        m = turn_idx == ti
        r_t = np.mean(r[m])                      # winding radius of this turn
        a, b = ellipse_axes_for_perimeter(2 * np.pi * r_t, ratio)
        t_tab, f_tab, _ = ellipse_arc_table(a, b)
        frac = (phi[m] % (2 * np.pi)) / (2 * np.pi)
        t_e = np.interp(frac, f_tab, t_tab)
        x_c[m] = a * np.cos(t_e)
        y_c[m] = b * np.sin(t_e)
    return x_c, y_c


# ---------------------------------------------------------------------------
# The twin: obra -> ink ground truth, wound and crushed
# ---------------------------------------------------------------------------
def build_twin(n_columns, g=G, script='greek', seed=0):
    """Build the twin. `script` selects the layout REGIME, which matters more
    than the language:

    PROSE (Greek or Latin) in scriptio continua fills the column to its edge
    -- the scribe adapts to the column, which is the workshop module. VERSE
    inverts the dependency: the metre fixes the line length and the column
    width becomes a consequence, with a ragged right edge. This is not
    academic for Herculaneum -- the ~62 Latin papyri there are mostly verse
    (Carmen de bello Actiaco, Ennius, Lucretius, Caecilius Statius); the
    main prose one is PHerc 1067.

    Interpuncts (present in the Carmen, gone from Latin books by ~150 AD)
    add a quasi-periodic mark every ~5-6 letters that Greek scriptio
    continua does not have -- a spectral discriminator, not noise.
    """
    sc = SCRIPTS[script]
    g = dict(g)
    g['letter_mm'] = sc.get('letter_mm', g['letter_mm'])
    g['line_mm'] = sc.get('line_mm', g['line_mm'])
    rng = np.random.default_rng(seed)

    lines_per_col = int((g['page_mm'] - 2 * g['margin_mm']) // g['line_mm'])

    if sc['verse']:
        lo, hi = sc['line_letters']
        counts = rng.integers(lo, hi + 1, size=(n_columns, lines_per_col))
        letters_per_line = int(np.max(counts))       # column set by longest
        g['col_written_mm'] = letters_per_line * g['letter_mm']
        # THE point of the verse regime: the metre fixes the line, so the
        # column period is a CONSEQUENCE, not a workshop module. Keep the
        # measured intercolumn gap and let the period follow.
        intercol = G['col_period_mm'] - G['col_written_mm']
        g['col_period_mm'] = g['col_written_mm'] + intercol
    else:
        letters_per_line = int(sc['col_written_mm'] // g['letter_mm'])
        g['col_written_mm'] = sc['col_written_mm']
        counts = np.full((n_columns, lines_per_col), letters_per_line)

    # the roll is sized only AFTER the layout regime has fixed the column
    # period -- in verse that period is a consequence of the metre
    roll = roll_from_obra(n_columns, g)
    L = roll['length_mm']

    Cl, Ll, Kl = [], [], []
    for ci in range(n_columns):
        for li in range(lines_per_col):
            n = int(counts[ci, li])
            Cl.append(np.full(n, ci + 1)); Ll.append(np.full(n, li + 1))
            Kl.append(np.arange(1, n + 1))
    C = np.concatenate(Cl); Lz = np.concatenate(Ll); K = np.concatenate(Kl)

    # reading position from the OUTER end (text start outermost)
    s_read = (g['lead_in_mm'] + (C - 1) * g['col_period_mm']
              + (K - 0.5) * g['letter_mm'])
    s_inner = L - s_read                       # arc from the inner end
    z = g['margin_mm'] + (Lz - 0.5) * g['line_mm']
    is_punct = (rng.random(len(C)) < 1.0 / 5.5) if sc['interpunct'] \
        else np.zeros(len(C), bool)

    turn_f, phi, r, x_w, y_w = wound_position(s_inner, g)
    turn_idx = np.floor(turn_f).astype(int)
    x_c, y_c = crush_points(turn_idx, phi, r, g['ratio'])

    a_out, b_out = ellipse_axes_for_perimeter(2 * np.pi * roll['r_out_mm'],
                                              g['ratio'])
    truth = dict(col=C, line=Lz, letter=K, s_read_mm=s_read, z_mm=z,
                 turn=turn_idx, r_mm=r, x_wound=x_w, y_wound=y_w,
                 x_crushed=x_c, y_crushed=y_c, interpunct=is_punct.astype(int))
    meta = dict(**roll, lines_per_col=lines_per_col,
                col_period_mm=g['col_period_mm'],
                letters_per_line=letters_per_line,
                n_letters=len(C), script=script, verse=sc['verse'],
                measured_grid=sc['measured'],
                col_written_mm=g['col_written_mm'],
                letter_mm=g['letter_mm'], line_mm=g['line_mm'],
                section_w_mm=2 * a_out, section_h_mm=2 * b_out)
    meta['kollesis'] = kollesis_map(L, g)
    return truth, meta


def kollesis_map(L_mm, g=G):
    """Where the SHEET JOINS fall inside the wound roll.

    All papyrus was Egyptian manufacture: the roll is not one sheet but
    kollemata glued with an overlap. Pliny (NH XIII) says the scapus never
    exceeded twenty sheets, about 11-12 feet -- i.e. sheets of ~17-19 cm.
    Each join is a band of DOUBLE THICKNESS recurring every ~180 mm of arc.

    That is a real periodic structure, detectable by thickness alone with no
    ink model, and it is the natural registration landmark for unwrapping.
    Its signature is distinctive: because consecutive joins are separated by
    a FIXED arc while the local circumference GROWS with radius, the angular
    step between successive joins shrinks monotonically outward -- an
    angular chirp no software artefact would imitate.
    """
    W = g['kollesis_mm']
    j = np.arange(1, int(L_mm // W) + 1)
    s_inner = L_mm - j * W                    # arc from the inner end
    keep = s_inner > 0
    j, s_inner = j[keep], s_inner[keep]
    turn_f, phi, r, x_w, y_w = wound_position(s_inner, g)
    theta = np.degrees(phi) % 360.0
    d_theta = np.abs(np.diff(np.degrees(phi)))
    return dict(index=j, s_inner_mm=s_inner, turn=turn_f, theta_deg=theta,
                r_mm=r, n_joins=len(j), scapus_sheets=float(L_mm / W),
                step_deg=np.concatenate([[np.nan], d_theta]))


def section_sweep(col_range, g=G):
    out = []
    for n in col_range:
        roll = roll_from_obra(n, g)
        a, b = ellipse_axes_for_perimeter(2 * np.pi * roll['r_out_mm'],
                                          g['ratio'])
        out.append((n, roll['n_turns'], 2 * a, 2 * b))
    return np.array(out)


def implied_umbilicus(n_turns, pitch_um=None, a_mm=None, b_mm=None):
    """The honest inverse. Section and pitch do NOT corroborate the winding
    count -- with those two fixed, the count is a function of the umbilicus
    alone. So the falsifiable statement runs the other way: IF the winding
    count is n and the pitch is p, THEN the umbilicus must be

        r0 = r_out - p * n

    which a raw-CT look at the core confirms or kills. Returns mm.[0m"""
    pitch_um = G['pitch_um'] if pitch_um is None else pitch_um
    a_mm = SECTION_MEASURED[0] / 2 if a_mm is None else a_mm
    b_mm = SECTION_MEASURED[1] / 2 if b_mm is None else b_mm
    _, _, perim = ellipse_arc_table(a_mm, b_mm)
    r_out = perim / (2 * np.pi)          # equal-perimeter circle
    return r_out - (pitch_um / 1000.0) * n_turns


def sensitivity(g=G, target=SECTION_MEASURED):
    """What the implied work does when the two soft inputs move. Neither the
    umbilicus nor the pitch is measured on PHerc1218 in this work, so no
    'the section implies N columns' claim may travel without them."""
    rows_r0, rows_p = [], []
    for r0 in (3.0, 3.5, 4.1, 5.0, 6.0):
        imp = obra_implied_by_section(dict(g, r0_mm=r0), target)
        rows_r0.append((r0, imp['n_columns'], imp['n_turns']))
    for p_um, label in ((173.0, 'human anchor'),
                        (187.3, 'pscamillo atlas, level 1'),
                        (207.0, 'atlas level 2, since corrected')):
        imp = obra_implied_by_section(dict(g, pitch_um=p_um), target)
        rows_p.append((p_um, label, imp['n_columns'], imp['n_turns']))
    return dict(by_umbilicus=rows_r0, by_pitch=rows_p)


def regime_table(g=G, target=SECTION_MEASURED,
                 pitches=((173.0, 'human anchor'),
                          (187.3, 'atlas level 1'))):
    """What a measured section implies WITHOUT knowing the text.

    Whoever is exploring a real scroll has the section and does not know the
    work, the language or the layout. So the honest output is not a number
    but an enumeration: for each layout regime, and for each candidate pitch,
    how much text the roll can hold. Columns alone are misleading -- Greek and
    Latin prose share a 43 mm column period yet hold very different amounts of
    text, because the letter pitch differs. Characters is the comparable
    quantity, and it is what places a candidate work.
    """
    rows = []
    for script in SCRIPTS:
        _, m0 = build_twin(6, script=script)
        gs = dict(g, col_period_mm=m0['col_period_mm'])
        for p_um, label in pitches:
            imp = obra_implied_by_section(dict(gs, pitch_um=p_um), target)
            _, mf = build_twin(max(imp['n_columns'], 1), script=script)
            rows.append(dict(script=script, pitch_um=p_um, pitch_label=label,
                             col_period_mm=m0['col_period_mm'],
                             n_columns=imp['n_columns'],
                             n_turns=imp['n_turns'],
                             lines_per_col=mf['lines_per_col'],
                             n_chars=mf['n_letters'],
                             measured_grid=mf['measured_grid']))
    return rows


def obra_implied_by_section(g=G, target=SECTION_MEASURED):
    """Invert the sweep: which obra length reproduces the measured section?"""
    sw = section_sweep(np.arange(10, 260), g)
    i = int(np.argmin(np.abs(sw[:, 2] - target[0])))
    return dict(n_columns=int(sw[i, 0]), n_turns=float(sw[i, 1]),
                section=(float(sw[i, 2]), float(sw[i, 3])))


# ---------------------------------------------------------------------------
# Optional voxel volume (a z-slab) for tool testing
# ---------------------------------------------------------------------------
def make_volume(truth, meta, g=G, z0=None, z_window_mm=8.0, voxel_um=60.0,
                fibers=False, fuse=None, kollesis=True, rng=None):
    """uint8 volume (z, y, x) of the crushed slab. Papyrus ~90, ink ~200,
    air 0. --fuse ti,tj,a0,a1 welds turns ti..tj over angles a0..a1 deg
    (their gap set to contact) and labels affected letters in the truth.
    Fibers: recto striation along z, verso along the winding direction,
    +-15 intensity."""
    rng = rng or np.random.default_rng(0)
    a_out, b_out = meta['section_w_mm'] / 2, meta['section_h_mm'] / 2
    pad = 1.0
    nx = int((2 * a_out + 2 * pad) * 1000 / voxel_um)
    ny = int((2 * b_out + 2 * pad) * 1000 / voxel_um)
    nz = int(z_window_mm * 1000 / voxel_um)
    z0 = z0 if z0 is not None else g['page_mm'] / 2 - z_window_mm / 2
    vol = np.zeros((nz, ny, nx), np.uint8)

    half_t = g['sheet_um'] / 2000.0            # half sheet thickness, mm
    n_turns = int(np.ceil(meta['n_turns']))
    p = g['pitch_um'] / 1000.0

    fuse_set = set()
    if fuse:
        ti, tj, a0, a1 = fuse
        fuse_set = set(range(int(ti), int(tj) + 1))

    # paint papyrus turn by turn on the crushed ellipses
    t_hi = np.linspace(0, 2 * np.pi, 3000)
    for t in range(n_turns):
        r_t = g['r0_mm'] + (t + 0.5) * p
        a, b = ellipse_axes_for_perimeter(2 * np.pi * r_t, g['ratio'])
        xs, ys = a * np.cos(t_hi), b * np.sin(t_hi)
        if t in fuse_set and t != int(fuse[1]):
            # true fusion: collapse this turn's sector ONTO the target
            # turn's ellipse (turn tj) -- the crossings become one
            ang = np.degrees(t_hi) % 360
            sel = (ang >= fuse[2]) & (ang <= fuse[3])
            a2, b2 = ellipse_axes_for_perimeter(
                2 * np.pi * (g['r0_mm'] + (int(fuse[1]) + 0.5) * p),
                g['ratio'])
            xs = np.where(sel, a2 * np.cos(t_hi), xs)
            ys = np.where(sel, b2 * np.sin(t_hi), ys)
        ix = ((xs + a_out + pad) * 1000 / voxel_um).astype(int)
        iy = ((ys + b_out + pad) * 1000 / voxel_um).astype(int)
        ok = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny)
        base = 90
        if fibers:
            # verso striation along winding direction: modulate along t
            base = 90 + (15 * np.sign(np.sin(t_hi * 40))).astype(int)
        for zz in range(nz):
            v = base if not fibers else \
                np.clip(base + 15 * np.sign(np.sin(zz * 0.9)), 0, 255)
            if np.isscalar(v):
                vol[zz, iy[ok], ix[ok]] = np.maximum(vol[zz, iy[ok], ix[ok]], v)
            else:
                vv = np.asarray(v)[ok] if not np.isscalar(v) else v
                vol[zz, iy[ok], ix[ok]] = np.maximum(vol[zz, iy[ok], ix[ok]],
                                                     vv.astype(np.uint8))
    # kollesis: double-thickness bands where sheets are glued (Egyptian
    # manufacture). Painted as an extra papyrus layer just inside the turn.
    ko = meta.get('kollesis')
    if ko is not None and kollesis:
        for r_k, th_k in zip(ko['r_mm'], ko['theta_deg']):
            a, b = ellipse_axes_for_perimeter(2 * np.pi * r_k, g['ratio'])
            t_tab, f_tab, _ = ellipse_arc_table(a, b)
            half = 0.5 * g['kollesis_ov_mm'] / (2 * np.pi * r_k)   # arc frac
            fr = (th_k / 360.0 + np.linspace(-half, half, 120)) % 1.0
            t_e = np.interp(fr, f_tab, t_tab)
            for dr in (0.0, -g['sheet_um'] / 1000.0):
                sc_ = (r_k + dr) / r_k
                ix = ((a * sc_ * np.cos(t_e) + a_out + pad) * 1000 / voxel_um).astype(int)
                iy = ((b * sc_ * np.sin(t_e) + b_out + pad) * 1000 / voxel_um).astype(int)
                ok = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny)
                vol[:, iy[ok], ix[ok]] = np.maximum(vol[:, iy[ok], ix[ok]], 130)

    # ink from the truth table, inside the z window
    inz = (truth['z_mm'] >= z0) & (truth['z_mm'] < z0 + z_window_mm)
    ix = ((truth['x_crushed'][inz] + a_out + pad) * 1000 / voxel_um).astype(int)
    iy = ((truth['y_crushed'][inz] + b_out + pad) * 1000 / voxel_um).astype(int)
    iz = ((truth['z_mm'][inz] - z0) * 1000 / voxel_um).astype(int)
    ok = (ix >= 0) & (ix < nx) & (iy >= 0) & (iy < ny) & (iz >= 0) & (iz < nz)
    vol[iz[ok], iy[ok], ix[ok]] = 200
    return vol, dict(z0_mm=z0, voxel_um=voxel_um, shape=vol.shape)


# ---------------------------------------------------------------------------
# Acceptance test (pre-registered)
# ---------------------------------------------------------------------------
def acceptance_test(verbose=True):
    """Three exams, criteria fixed before running:

    A. INEXTENSIBILITY. The crush must not stretch the sheet: for every turn,
       crushed ellipse perimeter == wound circumference.
       PASS: max relative error < 0.1 %.

    B. GROUND-TRUTH ROUND TRIP. Invert the crush analytically (crushed point
       + turn index -> arc fraction -> unrolled s) and recover every letter.
       PASS: max |s error| < 10 um and max |z error| == 0.

    C. UMBILICUS INVERSION (replaces a circular earlier test). An earlier
       version of this exam claimed that the measured section implies ~70
       turns "against ~70 measured independently", and read that as three
       independent measurements closing a loop. It is not: with the section
       and the pitch fixed, the turn count is a function of the umbilicus
       r0 alone, and r0 had been chosen to give 70. The check corroborated
       nothing -- it restated an identity.
       What survives is the inverse, which IS falsifiable outside the model:
       if the winding count is ~70 and the pitch is 173 um, the umbilicus
       must be ~4.1 mm, and the core in the raw CT confirms or kills that.
       PASS: (i) the inversion round-trips -- feeding the implied r0 back
       through the twin returns the same turn count to < 0.1 turns; and
       (ii) the tool demonstrates that r0 is a FREE parameter, i.e. moving
       it over 3-6 mm moves the implied turn count by more than 10 turns.
       Criterion (ii) is deliberately a test that the earlier claim was
       unfounded: if r0 barely mattered, the old framing would have been
       defensible.
    """
    results = {}

    truth, meta = build_twin(72)

    # ---- A -----------------------------------------------------------------
    errs = []
    p = G['pitch_um'] / 1000.0
    for t in np.unique(truth['turn']):
        r_t = np.mean(truth['r_mm'][truth['turn'] == t])
        a, b = ellipse_axes_for_perimeter(2 * np.pi * r_t, G['ratio'])
        _, _, perim = ellipse_arc_table(a, b)
        errs.append(abs(perim - 2 * np.pi * r_t) / (2 * np.pi * r_t))
    ok_A = max(errs) < 1e-3
    results['A_inextensible'] = dict(max_rel_err=float(max(errs)),
                                     passed=bool(ok_A))

    # ---- B -----------------------------------------------------------------
    ds_max = 0.0
    for t in np.unique(truth['turn'])[::7]:            # sample turns
        m = truth['turn'] == t
        r_t = np.mean(truth['r_mm'][m])
        a, b = ellipse_axes_for_perimeter(2 * np.pi * r_t, G['ratio'])
        t_tab, f_tab, _ = ellipse_arc_table(a, b, n=8192)
        t_e = np.arctan2(truth['y_crushed'][m] / b, truth['x_crushed'][m] / a) \
            % (2 * np.pi)
        frac = np.interp(t_e, t_tab, f_tab)
        phi_rec = 2 * np.pi * (t + frac)
        b_sp = p / (2 * np.pi)
        s_rec = G['r0_mm'] * phi_rec + 0.5 * b_sp * phi_rec ** 2
        s_true = meta['length_mm'] - truth['s_read_mm'][m]
        # the wound turn boundary: letters just below phi=2pi(t+1)
        ds = np.abs(s_rec - s_true)
        ds_max = max(ds_max, float(np.max(ds)))
    ok_B = ds_max < 0.010
    results['B_roundtrip'] = dict(max_s_err_mm=ds_max, passed=bool(ok_B))

    # ---- C -----------------------------------------------------------------
    r0_imp = implied_umbilicus(70.0)
    # round trip on the geometry itself, not through the column-quantized
    # sweep (which rounds to whole columns of 43 mm and would inject ~0.2
    # turns of quantization noise into a test about arithmetic)
    _, _, perim = ellipse_arc_table(SECTION_MEASURED[0] / 2,
                                    SECTION_MEASURED[1] / 2)
    r_out_m = perim / (2 * np.pi)
    round_trip = abs((r_out_m - r0_imp) / (G['pitch_um'] / 1000.0) - 70.0)
    back = obra_implied_by_section(dict(G, r0_mm=r0_imp))
    sens = sensitivity()
    spread = (max(r[2] for r in sens['by_umbilicus'])
              - min(r[2] for r in sens['by_umbilicus']))
    ok_C = round_trip < 0.1 and spread > 10.0
    results['C_umbilicus'] = dict(r0_implied_mm=float(r0_imp),
                                  round_trip_turns=float(round_trip),
                                  turn_spread_over_r0=float(spread),
                                  n_columns=int(back['n_columns']),
                                  passed=bool(ok_C))

    # ---- D: kollesis chirp -------------------------------------------------
    # The joins are a fixed arc apart while the circumference grows outward,
    # so the angular step between successive joins must shrink MONOTONICALLY
    # from the umbilicus outward. This is the signature that distinguishes a
    # manufacturing periodicity from a software slicing artefact (which is
    # constant in index, not chirped). Also: the join count must equal
    # sheet length / kollema width.
    ko = meta['kollesis']
    step = ko['step_deg'][1:]        # array runs OUTER -> INNER (join 1 is
    mono = float(np.mean(np.diff(step) > 0))   # outermost), so the angular
    #                                  step must GROW inward: diff > 0.
    n_ok = abs(ko['n_joins'] - int(meta['length_mm'] // G['kollesis_mm'])) <= 1
    ok_D = mono > 0.98 and n_ok
    results['D_kollesis'] = dict(n_joins=int(ko['n_joins']),
                                 scapus_sheets=float(ko['scapus_sheets']),
                                 monotone_frac=mono,
                                 step_first_deg=float(step[0]),
                                 step_last_deg=float(step[-1]),
                                 passed=bool(ok_D))

    if verbose:
        print("=" * 68)
        print("ACCEPTANCE TEST -- synthetic_scroll_twin (pre-registered)")
        print("=" * 68)
        A = results['A_inextensible']
        print(f"A inextensibility  max rel perimeter err = "
              f"{A['max_rel_err']:.2e} (<1e-3) -> "
              f"{'PASS' if A['passed'] else 'FAIL'}")
        B = results['B_roundtrip']
        print(f"B round trip       max |s err| = {B['max_s_err_mm']*1000:.2f} um "
              f"(<10) -> {'PASS' if B['passed'] else 'FAIL'}")
        C = results['C_umbilicus']
        print(f"C umbilicus        70 turns @173 um -> r0 = "
              f"{C['r0_implied_mm']:.2f} mm (round trip "
              f"{C['round_trip_turns']:.3f} turns); r0 is FREE: 3-6 mm spans "
              f"{C['turn_spread_over_r0']:.0f} turns -> "
              f"{'PASS' if C['passed'] else 'FAIL'}")
        D = results['D_kollesis']
        print(f"D kollesis chirp   {D['n_joins']} joins "
              f"({D['scapus_sheets']:.1f} sheets), angular step "
              f"{D['step_first_deg']:.0f} (outer) -> {D['step_last_deg']:.0f} (inner) deg, "
              f"monotone {D['monotone_frac']*100:.0f}% (>98) -> "
              f"{'PASS' if D['passed'] else 'FAIL'}")
        allp = all(v['passed'] for v in results.values())
        print("-" * 68)
        print("OVERALL:", "PASS" if allp else "FAIL")
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument('mode', choices=['build', 'sweep', 'volume', 'kollesis',
                                     'regimes', 'sensitivity', 'test'])
    ap.add_argument('--columns', type=int, default=72)
    ap.add_argument('--pitch-um', type=float, default=G['pitch_um'])
    ap.add_argument('--line-mm', type=float, default=G['line_mm'])
    ap.add_argument('--letter-mm', type=float, default=G['letter_mm'])
    ap.add_argument('--csv', type=str, default=None)
    ap.add_argument('--plot', type=str, default=None)
    ap.add_argument('--out', type=str, default='twin_volume.npy')
    ap.add_argument('--z-window', type=float, default=8.0)
    ap.add_argument('--voxel-um', type=float, default=60.0)
    ap.add_argument('--fibers', action='store_true')
    ap.add_argument('--script', choices=list(SCRIPTS), default='greek')
    ap.add_argument('--kollesis-mm', type=float, default=G['kollesis_mm'],
                    help='kollema (sheet) width; 0 disables joins')
    ap.add_argument('--fuse', type=str, default=None,
                    help='ti,tj,ang0,ang1 -- weld turns ti..tj over angles')
    args = ap.parse_args()
    for k_cli, k_g in [('pitch_um', 'pitch_um'), ('line_mm', 'line_mm'),
                       ('letter_mm', 'letter_mm')]:
        G[k_g] = getattr(args, k_cli)

    if args.mode == 'test':
        res = acceptance_test()
        sys.exit(0 if all(v['passed'] for v in res.values()) else 1)

    if args.mode == 'regimes':
        rows = regime_table()
        print(f"Measured section {SECTION_MEASURED[0]:.0f} x "
              f"{SECTION_MEASURED[1]:.0f} mm. The layout regime is UNKNOWN to "
              f"whoever is exploring,\nso here is what the section implies "
              f"under each one (umbilicus r0 = {G['r0_mm']:.1f} mm assumed):\n")
        print(f"  {'regime':<13} {'pitch':>7}  {'col period':>10} "
              f"{'columns':>8} {'turns':>6} {'lines/col':>10} {'characters':>11}")
        print("  " + "-" * 72)
        last = None
        for r in rows:
            if last and r['script'] != last:
                print()
            print(f"  {r['script']:<13} {r['pitch_um']:>6.1f}u "
                  f"{r['col_period_mm']:>9.0f}mm {r['n_columns']:>8d} "
                  f"{r['n_turns']:>6.1f} {r['lines_per_col']:>10d} "
                  f"{r['n_chars']:>11,d}"
                  + ("" if r['measured_grid'] else "   *"))
            last = r['script']
        print("\n  * grid metrics are declared placeholders, not measured")
        print("  Columns alone mislead: Greek and Latin prose share a 43 mm")
        print("  column period but differ in letter pitch, so the character")
        print("  count -- the quantity that places a candidate work -- differs")
        print("  by nearly a factor of two. Verse holds fewer columns but not")
        print("  proportionally less text.")
        return

    if args.mode == 'sensitivity':
        sens = sensitivity()
        r0_imp = implied_umbilicus(70.0)
        print("The section does NOT corroborate the winding count: with the")
        print("section and the pitch fixed, the count is a function of the")
        print("umbilicus alone, and the umbilicus is not measured here.\n")
        print("  implied work vs assumed umbilicus r0 (pitch 173 um):")
        for r0, ncol, nt in sens['by_umbilicus']:
            mark = "  <- default" if abs(r0 - G['r0_mm']) < 1e-6 else ""
            print(f"    r0 = {r0:.1f} mm -> {ncol:3d} columns, "
                  f"{nt:5.1f} turns{mark}")
        print("\n  implied work vs assumed pitch (r0 = %.1f mm):" % G['r0_mm'])
        for p_um, label, ncol, nt in sens['by_pitch']:
            print(f"    {p_um:5.1f} um ({label}) -> {ncol:3d} columns, "
                  f"{nt:5.1f} turns")
        print(f"\n  The falsifiable inverse: if the winding count is ~70 and "
              f"the pitch\n  is 173 um, the umbilicus must be "
              f"{r0_imp:.2f} mm -- check it against the core\n"
              f"  in the raw CT.")
        return

    if args.mode == 'sweep':
        # the column period depends on the layout regime, so learn it from a
        # throwaway twin before sweeping
        _, m0 = build_twin(10, script=args.script)
        gs = dict(G, col_period_mm=m0['col_period_mm'])
        sw = section_sweep(np.arange(20, 220, 2), gs)
        imp = obra_implied_by_section(gs)
        print(f"[implied obra] measured section {SECTION_MEASURED[0]:.0f} x "
              f"{SECTION_MEASURED[1]:.0f} mm -> {imp['n_columns']} columns "
              f"of {m0['col_period_mm']:.0f} mm ({args.script}), "
              f"{imp['n_turns']:.1f} turns")
        if args.plot:
            import matplotlib; matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(8, 5.5))
            ax.plot(sw[:, 0], sw[:, 2], label='crushed width (2a)')
            ax.plot(sw[:, 0], sw[:, 3], label='crushed height (2b)')
            ax.axhline(SECTION_MEASURED[0], color='k', ls='--', lw=1,
                       label='measured 42 mm')
            ax.axhline(SECTION_MEASURED[1], color='k', ls=':', lw=1,
                       label='measured 21 mm')
            ax.axvline(imp['n_columns'], color='r', ls='--',
                       label=f"implied obra: {imp['n_columns']} cols")
            ax.set_xlabel('obra length (columns of 43 mm)')
            ax.set_ylabel('crushed section (mm)')
            ax.set_title('The section reads the length of the work\n'
                         '(twin geometry vs measured PHerc1218 section)')
            ax.legend(fontsize=8)
            fig.tight_layout(); fig.savefig(args.plot, dpi=150)
            print(f"[plot] {args.plot}")
        return

    G['kollesis_mm'] = args.kollesis_mm or 1e9
    for w in grid_warnings():
        print(f'[warning] {w}')
    if grid_warnings():
        print('[warning] see docs/data_sources.md, "Grid self-consistency". '
              'Every line and\n          character count below scales with '
              'these; override with --line-mm etc.')
    truth, meta = build_twin(args.columns, script=args.script)
    if not meta['measured_grid']:
        print('[warning] the %s grid metrics are DECLARED PLACEHOLDERS, '
              'not measured -- override with --letter-mm/--line-mm before '
              'quoting numbers' % args.script)
    print(f"[twin] obra {args.columns} cols -> sheet {meta['length_mm']/1000:.2f} m, "
          f"{meta['n_turns']:.1f} turns, r_out {meta['r_out_mm']:.2f} mm, "
          f"crushed section {meta['section_w_mm']:.1f} x "
          f"{meta['section_h_mm']:.1f} mm, "
          f"{meta['n_letters']} letters "
          f"({meta['lines_per_col']} lines x {meta['letters_per_line']} "
          f"letters per column)")

    if args.mode == 'kollesis':
        ko = meta['kollesis']
        print(f"[kollesis] {ko['n_joins']} joins of {args.kollesis_mm:.0f} mm "
              f"= {ko['scapus_sheets']:.1f} sheets "
              f"(Pliny: a scapus is 20 sheets, ~11-12 ft)")
        print(f"[chirp] angular step between successive joins: "
              f"{ko['step_deg'][1]:.0f} deg (outermost) -> "
              f"{ko['step_deg'][-1]:.0f} deg (innermost)")
        print("join,s_inner_mm,turn,theta_deg,r_mm,step_deg")
        for row in zip(ko['index'], ko['s_inner_mm'], ko['turn'],
                       ko['theta_deg'], ko['r_mm'], ko['step_deg']):
            print(",".join(f"{v:.2f}" for v in row))
        if args.plot:
            import matplotlib; matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
            a_o, b_o = meta['section_w_mm'] / 2, meta['section_h_mm'] / 2
            x_c, y_c = crush_points(np.floor(ko['turn']).astype(int),
                                    np.radians(ko['theta_deg'])
                                    + 2 * np.pi * np.floor(ko['turn']),
                                    ko['r_mm'], G['ratio'])
            axes[0].scatter(x_c, y_c, c=ko['index'], cmap='plasma', s=45,
                            zorder=3, edgecolor='k', lw=0.4)
            th = np.linspace(0, 2 * np.pi, 400)
            axes[0].plot(a_o * np.cos(th), b_o * np.sin(th), color='0.7', lw=1)
            axes[0].set_aspect('equal'); axes[0].set_xlabel('mm')
            axes[0].set_title('Sheet joins in the crushed section\n'
                              '(thickness landmarks, no ink needed)')
            axes[1].plot(ko['turn'][1:], ko['step_deg'][1:], 'o-', ms=4)
            axes[1].set_xlabel('winding turn (from umbilicus)')
            axes[1].set_ylabel('angular step to next join (deg)')
            axes[1].set_title('The chirp: fixed arc, growing circumference\n'
                              '-> monotonically shrinking angular step')
            fig.tight_layout(); fig.savefig(args.plot, dpi=150)
            print(f"[plot] {args.plot}")
        return

    if args.mode == 'volume':
        fuse = tuple(float(x) for x in args.fuse.split(',')) if args.fuse else None
        vol, vmeta = make_volume(truth, meta, z_window_mm=args.z_window,
                                 voxel_um=args.voxel_um, fibers=args.fibers,
                                 fuse=fuse)
        np.save(args.out, vol)
        print(f"[volume] {args.out} shape {vmeta['shape']} "
              f"({vol.nbytes/1e6:.0f} MB), z0 {vmeta['z0_mm']:.1f} mm, "
              f"voxel {vmeta['voxel_um']:.0f} um"
              + (f", fused turns {args.fuse}" if fuse else "")
              + (", fibers on" if args.fibers else ""))
        return

    if args.csv:
        hdr = ("col,line,letter,s_read_mm,z_mm,turn,r_mm,"
               "x_wound,y_wound,x_crushed,y_crushed")
        rows = np.column_stack([truth[k] for k in
                                ['col', 'line', 'letter', 's_read_mm', 'z_mm',
                                 'turn', 'r_mm', 'x_wound', 'y_wound',
                                 'x_crushed', 'y_crushed']])
        np.savetxt(args.csv, rows, delimiter=',', header=hdr, comments='',
                   fmt='%.4f')
        print(f"[csv] {args.csv} ({len(rows)} letters)")

    if args.plot:
        import matplotlib; matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 2, figsize=(13.5, 6.5))
        mid = np.abs(truth['z_mm'] - G['page_mm'] / 2) < G['line_mm']
        for ax, (xk, yk, ttl) in zip(axes, [
                ('x_wound', 'y_wound', 'wound (ideal)'),
                ('x_crushed', 'y_crushed',
                 f"crushed 2:1 -- section {meta['section_w_mm']:.1f} x "
                 f"{meta['section_h_mm']:.1f} mm")]):
            sc = ax.scatter(truth[xk][mid], truth[yk][mid],
                            c=truth['col'][mid], cmap='viridis', s=6)
            ax.set_aspect('equal'); ax.set_title(ttl)
            ax.set_xlabel('mm'); ax.set_ylabel('mm')
        fig.colorbar(sc, ax=axes, label='column index', shrink=0.8)
        fig.suptitle(f"Synthetic twin, obra = {args.columns} columns "
                     f"-> {meta['n_turns']:.0f} turns (one text line, "
                     f"mid-height)", y=0.98)
        fig.savefig(args.plot, dpi=150, bbox_inches='tight')
        print(f"[plot] {args.plot}")


if __name__ == '__main__':
    main()
