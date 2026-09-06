# 9 — Work size (`scripts/work_size.py`, `archives/results/roll_catalogue.csv`)

*Moved unchanged from the README on 2026-09-06; the README now holds only the summary. Figures and scripts are referenced relative to the repository root.*


How big a roll does a work make, and which work fits a roll? Two directions:

- **forward** — a work of N columns → sheet length → roll diameter → crushed
  section.
- **inverse** — a measured crushed section → implied column count →
  candidates from a catalogue. And the outcome worth having: **a roll whose
  implied size matches nothing known is a candidate for a work that did not
  survive the medieval tradition** — which turns a curiosity into a priority
  list of which sealed roll to unwrap next.

```bash
python scripts/work_size.py identify --section 42 21
python scripts/work_size.py population --section 42 21
python scripts/work_size.py test
python scripts/phase_tracking.py test
```

> **The column period underpinning these counts is now vindicated** on the
> Grand Prize render (see [`docs/data_sources.md`](../data_sources.md),
> "Grid self-consistency"), so the 43 mm branch is the working one and the
> counts below are usable. The 72 mm branch stays in the sensitivity output
> because Herculaneum column widths genuinely vary between rolls — it is an
> alternative for *other* scrolls, not a rival reading of this one.

**Prior art, stated first.** Reconstructing a roll's original length and
column count from its geometry is standard papyrology, done on opened rolls
by measuring the width of successive volutions against column beginnings —
the reconstruction of PHerc. 1004 from 30 pieces is a worked example. Nothing
here invents the method. The only new input is CT geometry from a roll that
was never opened, and therefore never disturbed.

### Why columns and not characters

The chain `columns → sheet length → diameter` needs only the **column
period**. Going through characters — or through *stichoi* for prose — also
needs the **letter pitch**, because an ancient stichos is a notional
35-letter unit (the length of a Homeric hexameter), not a physical line. The
letter pitch is the least trustworthy number in the grid (see mode 8 and
`band_sensitivity.py`). So columns are
firm, characters are provisional, and the tool labels which is which. For
**verse** the stichos *is* the physical line, so that route stays clean —
which happens to favour the Latin material, most of which is verse.

### The base rate is the cheapest measurement available

An implied column count inherits three unknowns: the umbilicus, the winding
pitch, and the layout regime. Decomposing the band shows they are not
comparable:

| resolving… | band becomes |
|---|---|
| **the prose column period** (43 or 72 mm) | 80–98 or 47–58 |
| the regime (prose or verse) | 47–98 or 35–43 |
| the umbilicus | 38–95 |
| the winding pitch | 38–98 |

The column period has become the dominant term, and unlike the others it is
not a declared assumption but a **measurement that contradicts itself** — see
the self-consistency check in `docs/data_sources.md`.

And the regime is not a coin flip. Of ~1826 rolls from this library, **62 are
Latin** (Sider 2005), and every identified Latin text is **verse** — the
*Carmen de Bello Actiaco*, Lucretius, Ennius' *Annales*, Caecilius Statius'
*Obolostates*. The Greek remainder is overwhelmingly Epicurean prose. So
P(Greek prose) ≈ 0.966, and for PHerc1218 the prose band is **47–98
columns**, with 35–43 as a low-prior verse alternative. The prose band is wide
because the column period inside it is contested: 80–98 at 43 mm, 47–58 at
72 mm.

That reduction cost no scan. It is a base rate, and it removes more
uncertainty than the umbilicus and the pitch put together.

### A population check that is worth more than the band

The measured 42 × 21 mm section gives an equal-perimeter diameter of
**3.24 cm**. Intact Herculaneum rolls run **4–6 cm** in diameter and 19–24 cm
in height. PHerc1218 is therefore ~19 % below the population floor, which
admits two readings, and they are distinguishable:

- it was a small roll; or
- **what survives is not what was buried.** The precedent is exact: PHerc.
  1667 was reduced from 4.9 cm to 2 cm of diameter by 19th- and 20th-century
  opening attempts, losing more than half its content.

A stripped roll should show a truncated *outer* surface; an intrinsically
small one should not. If layers are missing, every size estimated from the
present section is a **lower bound**.

### The catalogue, and the rule that keeps it honest

`archives/results/roll_catalogue.csv` carries one row per roll or work, in columns where
possible, and **every sized row must name its source**. Exam C fails on any
number without one, so the catalogue cannot degrade quietly as it grows. An
empty cell is information; an invented one is damage.

Sizes come from Gigante's *Catalogo dei Papiri Ercolanesi* and Sider's
*Library of the Villa dei Papiri*, one sourced row at a time. Anchors in place: Philodemus' *On Piety* at ~367 columns and *On Poems* II at
**222 columns in a 16 m roll of 100 kollemata** — both far larger than
PHerc1218 and correctly excluded. PHerc. 1667 gives ~20 columns over ~1.5 m
of surviving roll, and PHerc. 172 (*On Vices* I) more than 70. PHerc. 118
carries no size but supplies the **17 characters per line** that the grid
self-consistency check turns on.

### Validation

| exam | criterion | result |
|---|---|---|
| A — round trip | forward(N) → section → inverse returns N, for N = 20…200 | **exact, PASS** |
| B — the band must stay wide | the raw implied band spans > 2× while the umbilicus is unmeasured | **2.8×, PASS** |
| C — no unsourced sizes | every row carrying a column or stichoi count names a source | **PASS** |

Exam B is written backwards on purpose: it **fails if the band narrows**
without anyone having measured the umbilicus. It is a guard against a future
version of this tool quoting a confident single figure, which is the failure
mode most likely to produce a wrong attribution.

---

