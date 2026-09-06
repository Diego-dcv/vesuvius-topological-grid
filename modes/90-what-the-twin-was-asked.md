# What the twin was asked to do — and what came back

*Moved unchanged from the README on 2026-09-06; the README now holds only the summary. Figures and scripts are referenced relative to the repository root.*


The synthetic twin (Mode 7) is the only tool here that produces data rather than
consuming it, and that makes it good for exactly one class of problem: **breaking a
confound that real data cannot break.** Two such problems were put to it, both asked
for rather than invented — and both have now been run, by other hands.

**Separating faint from compressed** became Mode 12. Run end-to-end by aviad12g over
a frozen production checkpoint (five generation seeds, controlled-FPR readouts), it
returned the third outcome — the one invisible in real data: the response moves on
**both** axes, contrast and geometry, with a modest interaction (~0.05).

**Calibrating a fusion detector** became the three-handed fusion readout: this
repository's geometry supplied exact gaps, aviad12g's frozen runs supplied the
probabilities, and Jinhojeong's ray instrument counted — the first measurement of
fusion rate against exact gap size. The finding: at detected contacts the checkpoint
bridges neighbouring sheets at a flat 75–78 % across 10–150 µm of true air gap, so
fusion is **not** a tight-gap phenomenon there, and the PHerc1218 anisotropy question
moves from gaps to detection-versus-contrast — which the preregistered fixed-geometry
follow-up is built to answer. (The same welding trick had earlier calibrated the
winding-count invariant to a floor of ≳7 % of a slab's windings.)

What the twin cannot do, and should not be asked to: it is a prism, identical top to
bottom, with two analytic folds and no tearing. **That prism assumption now has a
price tag**: a single section profile fits a given CT slice to 1.1–2.8 mm, while
that slice's own measured profile fits to 0.66–0.83 mm (see Mode 11B). So
`--section-profile` taking one shape for the whole roll is itself an
approximation worth about 2 mm of section error, and the natural next step is to
let it take a profile per height, which the data already contains. It does not reproduce the complexity
of real deformation and comparing its slices with real CT by eye would be pointless.
Its value is that the answer is known, not that it looks convincing — and the modes
above use it as a unit test with ground truth, never as evidence about a real scroll.

---

