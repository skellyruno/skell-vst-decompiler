# VMR nonlinear local DSP evidence — 2026-11-24

Source identities are enforced by SHA-256 before any build-specific checks. All three local binaries passed the new verifier; repeated runs produced byte-identical JSON. This is a static mathematical research record, not source recovery, a complete commercial compressor implementation, an activation bypass, or a claim of audio equivalence.

## FG-116: clamped integrator and variable retention

The candidate call at `0x162175` enters `0x15e670`. In the scalar remainder loop at `0x15eabf`, the old state s is limited to c=clamp(s,-0.053088,0.046774). With d=a*(x-s), the scratch output is q=c+d and the persisted next state is s'=c+2*d. A separate boolean indicates whether s was limited and selects k0 or k1, whose fields are loaded at `0x15e732–0x15e758`. At `0x15ec5a`, the selected coefficient stream feeds the minimum-constrained update k_s=min(k,k+a_r*(k_s_prev-k)). Then `0x15ed88` uses that stream to compute a second state's residual e=x-v and v'=v+k_s*e. Verified state stores are relative to channel records at +0x60, +0x58, +0x68. These are linked local recurrences; the physical circuit interpretation, final gain law and active dispatch remain unverified.

## FG-2A: biased magnitude curve and even-power stage

The candidate call at `0x156f4f` reaches `0x14d590`. At `0x14d9d2–0x14da5e`, input is biased, magnitude extracted with a sign of +/-1, passed through identity/quadratic/plateau regions, sign-restored and offset-subtracted. The constants +1 and -1 are checked. The next argument chain at `0x14da5e–0x14db2d` computes a weighted sum of the fourth, sixth and eighth powers, conditional on the inspected vector helpers. The 7 explicit square-dispatch slots map through 6 pointer locations to 4 entry routines containing scalar/SSE/AVX self-multiplication. The first explicit slots for element-wise multiplication, in-place scalar scaling, out-of-place scalar scaling and in-place vector addition are also verified. Other slots and actual runtime selection remain open. The fourth-, sixth- and eighth-power weights come from object fields 0x560/0x568/0x578. The sum scratch is consumed by a double-precision DF2T biquad at `0x14db50`. This is evidence of nonlinear processing and filtering, not proof of a full gain-computer or a particular physical optical model. Do not infer harmonic levels or sound quality from this trace.

## FG-Stress: three-region curve

At `0x16327e`, finite inputs with ordered thresholds lo<=hi use identity for x>=hi, affine for x<lo, otherwise a quadratic polynomial. The coefficient fields occupy +0xd8..+0xf8. The downstream scratch path at `0x163300–0x1633f6` calls vector operations and passes buffers to `0x15d420`. This confirms additional nonlinear processing, not the final dynamic gain law. The setup, parameter units, continuity and final output contribution remain open.

## Reusable research workflow

- `python -m skell_vst_decompiler.vmr_nonlinear /private/FG-2A.epl` — exact-source evidence (FG-116, FG-2A, FG-Stress supported). No proprietary binaries or coefficient tables in this repository.
- `python -m skell_vst_decompiler.research_index reports 'even-power'` — existing cross-report search.
- `python -m skell_vst_decompiler.evidence_book reports` — generated equation atlas; `--format json` emits structured evidence and fingerprint-scoped call links. The generated Markdown is `docs/DSP_EQUATION_ATLAS.md`. A target may overlap multiple evidence regions; no match does not mean the function is unknown. 95 records are not 95 distinct algorithms or a completeness estimate.
- The new report contains 16 local regions, 165 opcode/operand checkpoints, six exact double constants and 17 explicit pointer slots. It includes direct call references from the bounded windows. The atlas consolidates 95 evidence records from four source fingerprints, with 95 static call references where the source reports expose them. These are not counts of runtime call edges.
- 59 local Python tests passed, including four new regression tests; compilation and repeat-report equality passed. The first new test incorrectly assumed the keyword 'even-power nonlinear' matched only one record; it was corrected to require both intended records. No test failure was suppressed.
- Ghidra 12.2 previously passed the owned-fixture CI gate. Local JDK remains 21 and no analyzeHeadless is installed; an actual official release URL probe failed DNS in this session. Actual vendor Ghidra output, full commercial processor gain laws and real plugin audio measurements remain unverified. No vendor files uploaded to CI. No Skelliere production or JUCE changes in this batch.
