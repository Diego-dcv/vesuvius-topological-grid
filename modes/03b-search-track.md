# 3b — Search & Track (`scripts/phase_tracking.py`)

*Moved unchanged from the README on 2026-09-06; the README now holds only the summary. Figures and scripts are referenced relative to the repository root.*


Mode 3 states its own limit in its docstring: line centres are found on a
*clean* image, and on real raw data the algorithm
must **search** for the period and phase by maximizing the contrast of the
folded profile — "that search is the natural next step". This is that step,
and it turned up something the prototype was throwing away.

```bash
python scripts/phase_tracking.py search IMAGE.png --width-mm 129 --axis lines
python scripts/phase_tracking.py track IMAGE.png --width-mm 129 --plot phase.png
python scripts/phase_tracking.py test
```

**The search.** Classic epoch folding: for each trial period, fold the
profile and score it with the chi-square of the folded bins against a flat
one. The true period maximizes it. No peak-finding on a clean image, no
assumed period, and it degrades gracefully instead of collapsing — it
recovers a 2.79 mm lattice to 0.1 % at SNR 0.3, where peak-finding on the raw
profile has nothing to work with.

**What the prototype discarded.** `fold_lines` already walks the image in
windows and computes line centres in each one — then averages every strip
together, throwing away *where each window sat*. That per-window phase is a
signal in its own right. In an intact surface it drifts slowly and smoothly;
a discontinuity in the underlying surface displaces the text and **steps**
it. A phase glitch, in the pulsar-timing sense.

### A glitch is not a drift

This distinction is the whole tool. Writing that sits slightly skew to the
roll axis produces a phase that drifts **linearly** across the render — three
whole periods in the test case, and entirely innocent. A surface
discontinuity produces a **step**. The drift is fitted and subtracted before
anything is called a glitch, and exam C enforces it: if a pure linear drift
raises even one glitch, the tool is reporting skew as damage and fails.

### Which axis says what

| `--axis` | period | what a jump to a neighbouring winding does |
|---|---|---|
| `columns` | ~43 mm, along the unrolled arc | **steps** — a skip displaces text by roughly one circumference, not a multiple of the column period |
| `lines` | ~2.79 mm, along the roll axis | **need not move at all** |

The asymmetry matters and is easy to get backwards. The scribe wrote on a
flat sheet, so lines sit at the same height on every winding; only skew moves
them. **A clean line phase is not evidence of an intact surface.**

One practical caveat, worth more than the code in some cases: a render
carrying only ~10 column periods gives the search very little along that
axis. Where the periods are few, locating the blank intercolumn bands
directly and checking the sequence of gap-to-gap distances is more robust and
needs none of this. This tool earns its place where the periods are many and
the signal is buried — the raw-intensity case mode 3 was always aimed at.

### Validation

| exam | criterion | result |
|---|---|---|
| A — period under noise | recover a known lattice to < 2 % at SNR 0.3, where peak-finding fails | **0.1 %, PASS** |
| B — glitch localized | exactly one glitch within one window of truth; a clean control raises none | **21.1 vs 21.0 mm, 0 control, PASS** |
| C — drift is not a glitch | a 3-period linear drift must raise **zero** glitches | **0, PASS** |
| D — harmonic rejection | recover the fundamental where 2P genuinely scores higher, **and** show the search picks 2P with rejection off | **2.786 vs 5.583 mm, PASS** |

Exam D was rewritten because its first version was vacuous: with a plain
second harmonic the search returned the right answer with rejection switched
off, so the exam could not fail. It now checks both halves — the fix, and
that the fix was needed.

Exam B failed on the first run for a reason worth keeping: the analysis
window was sized from the lattice period, which runs along the *perpendicular*
axis. For line spacing on a narrow render that came out wider than the whole
image, so exactly one window fitted and there was no track to glitch. Window
size belongs to the walking direction.

---

