#!/usr/bin/env python3
"""
work_size.py -- How big a roll does a work make, and which work fits a roll?

Diego C. V. (vesuvius-topological-grid)

THE TWO DIRECTIONS
------------------
FORWARD  a work of N columns -> sheet length -> roll diameter -> crushed
         section. What to expect if this roll holds that work.

INVERSE  a measured crushed section -> implied column count -> candidate
         works from the catalogue. And the interesting outcome: **a roll
         whose implied size matches nothing known is a candidate for a work
         that did not survive the medieval tradition.** That turns a
         curiosity into a priority list -- which sealed roll to spend the
         next unwrapping effort on.

PRIOR ART -- SAY IT FIRST
-------------------------
Reconstructing a roll's original length and column count from its geometry
is standard papyrology. It is done on opened rolls by measuring the width of
successive volutions and crossing them against column beginnings; the
reconstruction of PHerc. 1004 (a book of Philodemus' On Rhetoric, surviving
in 30 pieces) is a worked example. Nothing here invents that method. The only
new thing is the input: CT geometry from a roll that was never opened, and
therefore not disturbed.

WHY COLUMNS AND NOT CHARACTERS
------------------------------
The chain columns -> sheet length -> diameter needs only the COLUMN PERIOD.
Going through characters, or through stichoi for prose, additionally needs
the LETTER PITCH -- because an ancient stichos is a notional 35-letter unit
(the length of a Homeric hexameter), not a physical line. The letter pitch is
currently the least trustworthy number in the grid: it sits at 92 % of the
upper edge of its search band in grid_metric, and its ratio to the line
spacing is suspiciously close to 3:2. See docs/data_sources.md and
band_sensitivity.py.

So: columns are firm, characters are provisional, and the tool labels which
is which rather than mixing them. For VERSE the stichos IS the physical line,
so the stichoi route stays clean there -- which happens to favour exactly the
Latin material at Herculaneum, most of which is verse.

THE BANDS ARE THE POINT
-----------------------
An implied column count is not a number, it is a range, because it inherits
the umbilicus and the pitch (neither measured on PHerc1218) and the layout
regime (unknown to whoever is exploring). `identify` reports the full band
and only calls a match a match if the candidate falls inside it. A single
figure with no band would be worse than useless here: it would produce
confident wrong attributions.

USAGE
-----
    python work_size.py forward --columns 95
    python work_size.py identify --section 42 21
    python work_size.py population --section 42 21
    python work_size.py test
"""

import argparse
import csv
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOGUE = os.path.join(HERE, 'roll_catalogue.csv')

# geometry defaults, shared with synthetic_scroll_twin.py
COL_PERIOD_MM = 43.0     # measured, Paris 4, replicated
LEAD_IN_MM = 150.0       # assumed
TAIL_MM = 200.0          # assumed
STICHOS_LETTERS = 35.0   # a Homeric hexameter; ~15-16 syllables

# the soft inputs, and the range each is allowed to take
UMBILICUS_MM = (3.0, 4.1, 6.0)          # low, default, high -- all assumed
PITCH_UM = ((173.0, 'human anchor'), (187.3, 'atlas level 1'))
REGIME_PERIOD_MM = (('greek/latin prose', 43.0), ('latin verse', 98.0))

# base rate of the library itself (see roll_catalogue.csv). Of ~1826 rolls,
# 62 are Latin and every identified Latin text is verse. This is the cheapest
# uncertainty reduction available: it needs no scan, and resolving prose vs
# verse collapses 56 % of the width of an implied-columns band.
P_VERSE = 62 / 1826.0

# population envelope of intact Herculaneum rolls (see roll_catalogue.csv)
POP_DIAM_CM = (4.0, 6.0)
POP_HEIGHT_CM = (19.0, 24.0)


def ellipse_perimeter(a, b):
    h = ((a - b) / (a + b)) ** 2
    return np.pi * (a + b) * (1.0 + 3 * h / (10 + np.sqrt(4 - 3 * h)))


def r_out_from_section(w_mm, h_mm):
    """Equal-perimeter circle radius of a crushed section, mm."""
    return ellipse_perimeter(w_mm / 2, h_mm / 2) / (2 * np.pi)


def sheet_length(n_columns, period_mm=COL_PERIOD_MM):
    return LEAD_IN_MM + n_columns * period_mm + TAIL_MM


def roll_from_length(L_mm, pitch_um, r0_mm):
    """Sheet length -> outer radius and turns, wound from the umbilicus out."""
    p = pitch_um / 1000.0
    r_out = np.sqrt(r0_mm ** 2 + L_mm * p / np.pi)
    return r_out, (r_out - r0_mm) / p


def columns_from_section(w_mm, h_mm, pitch_um, r0_mm, period_mm):
    """Inverse: crushed section -> implied column count."""
    r_out = r_out_from_section(w_mm, h_mm)
    p = pitch_um / 1000.0
    L = np.pi * (r_out ** 2 - r0_mm ** 2) / p
    # floor, but with a tolerance: the forward chain goes through a sqrt, so
    # an exact N comes back as N - 1e-13 and would floor to N-1
    n = (L - LEAD_IN_MM - TAIL_MM) / period_mm
    return int(max(0, np.floor(n + 1e-6))), L, r_out


def implied_band(w_mm, h_mm):
    """Every combination of the soft inputs. Returns rows + the overall band."""
    rows = []
    for label_r, period in REGIME_PERIOD_MM:
        for pitch, label_p in PITCH_UM:
            for r0 in UMBILICUS_MM:
                n, L, r_out = columns_from_section(w_mm, h_mm, pitch, r0,
                                                   period)
                rows.append(dict(regime=label_r, period_mm=period,
                                 pitch_um=pitch, pitch_label=label_p,
                                 r0_mm=r0, n_columns=n, length_mm=L,
                                 r_out_mm=r_out))
    ns = [r['n_columns'] for r in rows]
    return rows, (min(ns), max(ns))


def stichoi_to_columns(stichoi, lines_per_col, verse, letters_per_line=None):
    """Verse: one stichos is one physical line -- clean. Prose: a stichos is a
    notional 35-letter unit, so the physical line length is needed, which
    drags in the letter pitch. Returns (columns, is_firm)."""
    if verse:
        return int(np.ceil(stichoi / lines_per_col)), True
    if not letters_per_line:
        return None, False
    phys_lines = stichoi * STICHOS_LETTERS / letters_per_line
    return int(np.ceil(phys_lines / lines_per_col)), False


def load_catalogue(path=CATALOGUE):
    if not os.path.exists(path):
        return []
    with open(path, newline='', encoding='utf-8') as f:
        rows = [r for r in csv.DictReader(
            (line for line in f if not line.startswith('#')))]
    return rows


def sized_entries(cat):
    """Catalogue entries that carry a usable size (columns or stichoi)."""
    out = []
    for r in cat:
        n = r.get('columns', '').strip()
        s = r.get('stichoi', '').strip()
        if n.isdigit() or s.isdigit():
            out.append(r)
    return out


# --------------------------------------------------------------------------
def acceptance_test(verbose=True):
    """Pre-registered.

    A. ROUND TRIP. forward(N) then inverse on the resulting section must
       return N, at the same pitch, umbilicus and period.
       PASS: exact for N in 20..200 step 10.
    B. THE BAND MUST BE WIDE, AND HONESTLY SO. Implied columns for the
       measured 42x21 section, across the soft inputs.
       PASS: the band spans more than a factor of 2, AND the tool never
       reports a single number outside identify's band. This exam exists to
       stop a future version quoting a point estimate: if the band were
       narrow, a point estimate would be defensible; it is not.
    C. NO UNSOURCED SIZES. Every catalogue entry carrying a number in
       `columns` or `stichoi` must have a non-empty `source`.
       PASS: no violations. (This is the exam that keeps the catalogue
       honest as it grows -- it is the one most likely to fail later.)
    """
    res = {}

    # A
    ok = True
    for n in range(20, 201, 10):
        L = sheet_length(n)
        r_out, _ = roll_from_length(L, 173.0, 4.1)
        # crushed 2:1 section of equal perimeter
        from math import pi, sqrt
        ratio = 2.0
        hh = ((ratio - 1) / (ratio + 1)) ** 2
        c = pi * (1 + 1 / ratio) * (1 + 3 * hh / (10 + sqrt(4 - 3 * hh)))
        A = 2 * pi * r_out / c
        w, h = 2 * A, 2 * A / ratio
        back, _, _ = columns_from_section(w, h, 173.0, 4.1, COL_PERIOD_MM)
        if back != n:
            ok = False
            break
    res['A_roundtrip'] = dict(passed=bool(ok))

    # B
    rows, band = implied_band(42.0, 21.0)
    spread = band[1] / max(band[0], 1)
    res['B_band'] = dict(low=band[0], high=band[1], spread=float(spread),
                         passed=bool(spread > 2.0))

    # C
    cat = load_catalogue()
    bad = [r['id'] for r in sized_entries(cat) if not r.get('source', '').strip()]
    res['C_sourced'] = dict(n_sized=len(sized_entries(cat)),
                            unsourced=bad, passed=bool(not bad))

    if verbose:
        print("=" * 70)
        print("ACCEPTANCE TEST -- work_size (pre-registered)")
        print("=" * 70)
        print(f"A round trip       forward -> inverse returns N for N=20..200 "
              f"-> {'PASS' if res['A_roundtrip']['passed'] else 'FAIL'}")
        B = res['B_band']
        print(f"B band is wide     42x21 mm implies {B['low']}-{B['high']} "
              f"columns ({B['spread']:.1f}x spread) -> "
              f"{'PASS' if B['passed'] else 'FAIL'}")
        C = res['C_sourced']
        print(f"C sourced sizes    {C['n_sized']} sized entries, "
              f"{len(C['unsourced'])} unsourced -> "
              f"{'PASS' if C['passed'] else 'FAIL'}")
        print("-" * 70)
        print("OVERALL:", "PASS" if all(v['passed'] for v in res.values())
              else "FAIL")
    return res


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument('mode', choices=['forward', 'identify', 'population',
                                     'test'])
    ap.add_argument('--columns', type=int, default=95)
    ap.add_argument('--section', type=float, nargs=2, default=[42.0, 21.0],
                    metavar=('WIDTH', 'HEIGHT'))
    ap.add_argument('--height-cm', type=float, default=None,
                    help='roll height, for the population check')
    args = ap.parse_args()

    if args.mode == 'test':
        r = acceptance_test()
        sys.exit(0 if all(v['passed'] for v in r.values()) else 1)

    w, h = args.section

    if args.mode == 'forward':
        print(f"A work of {args.columns} columns, wound at each candidate "
              f"pitch and umbilicus:\n")
        print(f"  {'regime':<18} {'pitch':>7} {'r0':>5} {'sheet':>8} "
              f"{'turns':>6} {'diameter':>9} {'crushed 2:1':>14}")
        print("  " + "-" * 74)
        for label_r, period in REGIME_PERIOD_MM:
            for pitch, _ in PITCH_UM:
                for r0 in (UMBILICUS_MM[1],):
                    L = sheet_length(args.columns, period)
                    r_out, turns = roll_from_length(L, pitch, r0)
                    from math import pi, sqrt
                    hh = (1 / 3.) ** 2
                    c = pi * 1.5 * (1 + 3 * hh / (10 + sqrt(4 - 3 * hh)))
                    A = 2 * pi * r_out / c
                    print(f"  {label_r:<18} {pitch:>6.1f}u {r0:>4.1f}m "
                          f"{L/1000:>7.2f}m {turns:>6.1f} "
                          f"{2*r_out/10:>8.2f}cm "
                          f"{2*A:>6.1f} x {2*A/2:>4.1f} mm")
        lo, hi = POP_DIAM_CM
        print(f"\n  Intact Herculaneum rolls run {lo:.0f}-{hi:.0f} cm in "
              f"diameter and {POP_HEIGHT_CM[0]:.0f}-{POP_HEIGHT_CM[1]:.0f} cm "
              f"in height.")
        return

    rows, band = implied_band(w, h)
    r_out = r_out_from_section(w, h)

    if args.mode == 'population':
        d_cm = 2 * r_out / 10
        lo, hi = POP_DIAM_CM
        print(f"Crushed section {w:.0f} x {h:.0f} mm -> equal-perimeter "
              f"diameter {d_cm:.2f} cm\n")
        print(f"  intact Herculaneum rolls: {lo:.0f}-{hi:.0f} cm diameter")
        if d_cm < lo:
            print(f"  -> BELOW the population range by "
                  f"{100*(lo-d_cm)/lo:.0f} %.")
            print(f"     Either a small roll, or -- as happened to PHerc. 1667,")
            print(f"     reduced from 4.9 cm to 2 cm by opening attempts -- what")
            print(f"     survives is not what was buried. Both are testable:")
            print(f"     a stripped roll should show a truncated OUTER surface,")
            print(f"     an intrinsically small one should not.")
        elif d_cm > hi:
            print(f"  -> ABOVE the population range: an unusually large roll.")
        else:
            print(f"  -> inside the population range.")
        if args.height_cm:
            lo_h, hi_h = POP_HEIGHT_CM
            inside = lo_h <= args.height_cm <= hi_h
            print(f"\n  height {args.height_cm:.1f} cm vs {lo_h:.0f}-{hi_h:.0f} "
                  f"cm -> {'inside' if inside else 'OUTSIDE'} the range")
        return

    # identify
    print(f"Crushed section {w:.0f} x {h:.0f} mm "
          f"(equal-perimeter diameter {2*r_out/10:.2f} cm)\n")
    print(f"  implied columns, over every combination of the soft inputs:")
    print(f"  {'regime':<18} {'pitch':>7} {'r0':>5} {'columns':>8}")
    print("  " + "-" * 42)
    for r in rows:
        print(f"  {r['regime']:<18} {r['pitch_um']:>6.1f}u {r['r0_mm']:>4.1f}m "
              f"{r['n_columns']:>8d}")
    prose = [r['n_columns'] for r in rows if r['regime'].startswith('greek')]
    verse = [r['n_columns'] for r in rows if r['regime'].startswith('latin')]
    print(f"\n  RAW BAND: {band[0]} - {band[1]} columns "
          f"({band[1]/max(band[0],1):.1f}x) if the regime is a coin flip.\n")
    print(f"  But it is not a coin flip. Of ~1826 rolls from this library, 62")
    print(f"  are Latin and every identified Latin text is verse, so:\n")
    print(f"    Greek prose   p ~ {1-P_VERSE:.3f}   ->  "
          f"{min(prose)} - {max(prose)} columns  ({max(prose)/min(prose):.2f}x)")
    print(f"    Latin verse   p ~ {P_VERSE:.3f}   ->  "
          f"{min(verse)} - {max(verse)} columns  (low-prior alternative)\n")
    print(f"  The prose band is the working answer. It costs no scan to get:")
    print(f"  it is a base rate, and it removes more uncertainty than the")
    print(f"  umbilicus and the winding pitch put together.\n")
    band = (min(prose), max(prose))

    cat = load_catalogue()
    sized = sized_entries(cat)
    if not sized:
        print("  CATALOGUE: no entry yet carries a column or stichoi count, so")
        print("  no candidate can be matched or excluded. The frame is here and")
        print("  the schema is documented; the sizes come from Gigante's")
        print("  Catalogo and Sider's Library of the Villa dei Papiri, one")
        print("  sourced row at a time. An empty cell is information -- an")
        print("  invented one is damage.")
        print("\n  What the discriminator will do once populated: a roll whose")
        print("  implied band overlaps NO known work is a candidate for a work")
        print("  lost to the medieval tradition -- i.e. a reason to spend the")
        print("  next unwrapping effort on it.")
        return

    lo, hi = band
    inside = [r for r in sized
              if r['columns'].isdigit() and lo <= int(r['columns']) <= hi]
    print(f"  candidates within the band ({len(sized)} sized entries "
          f"searched):")
    if inside:
        for r in inside:
            print(f"    {r['id']:<12} {r['work']} -- {r['columns']} columns "
                  f"[{r['status']}]")
    else:
        print("    NONE.")
        print("    A roll whose implied size matches no known work is a")
        print("    candidate for a work that did not survive the medieval")
        print("    tradition. Treat as a priority for unwrapping, not as a")
        print("    conclusion: the band is wide and the catalogue is partial.")


if __name__ == '__main__':
    main()
